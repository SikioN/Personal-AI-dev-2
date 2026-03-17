from __future__ import annotations

import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

logger = logging.getLogger(__name__)

import numpy as np

from src.utils.data_structs import Quadruplet, QuadrupletCreator
from src.utils.kg_navigator import KGNavigator

if TYPE_CHECKING:
    from ....llm.base_client import BaseLLMClient
    from ....config.qa_config import QAConfig
    from ....utils.wikidata_utils import WikidataMapper


@dataclass
class RetrievalResult:
    unique_candidates: List[Quadruplet]
    candidate_e5_scores: Dict[str, float]            # quad.id -> e5 score
    temporal_bucket: List[Quadruplet]                # for time_join
    resolved_entities: List[Tuple[str, str, Optional[str]]]  # (orig, resolved_name, wd_id)
    resolved_time: Optional[str]
    search_k: int


class HybridRetriever:
    """
    Retrieval from Neo4j (graph BFS via KGNavigator) +
    ChromaDB (ANN search on quadruplet embeddings).
    No in-memory KG.
    """

    def __init__(
        self,
        kg_model,
        mapper: "WikidataMapper",
        llm_client: "BaseLLMClient",
        config: "QAConfig",
        use_vector_search: bool = True,
    ) -> None:
        self.kg_model = kg_model
        self.mapper = mapper
        self.llm = llm_client
        self.config = config
        self.use_vector_search = use_vector_search

    # ------------------------------------------------------------------
    # Entity resolution
    # ------------------------------------------------------------------

    def resolve_entity(self, name: str) -> Tuple[str, Optional[str]]:
        """
        3-level entity resolution:
        1. mapper.get_id(name)          — exact Neo4j/file lookup
        2. mapper.search_names(name)    — fuzzy search
        3. LLM normalize -> mapper.get_id()
        """
        if not name:
            return name, None

        # Level 1: exact match
        wd_id = self.mapper.get_id(name)
        if wd_id:
            return name, wd_id

        # Level 2: fuzzy search
        cands = self.mapper.search_names(name, limit=10)
        if not cands and ' ' in name:
            tokens = name.split()
            cands = self.mapper.search_names(tokens[-1], limit=10)
            if not cands:
                cands = self.mapper.search_names(tokens[0], limit=10)
        if cands:
            if len(cands) == 1:
                return cands[0], self.mapper.get_id(cands[0])
            if self.llm:
                cand_str = ', '.join(repr(c) for c in cands)
                prompt = (
                    f"A question mentions entity '{name}'. "
                    f"Which of these KG names best matches?\nOptions: {cand_str}\n"
                    f"Output ONLY the exact name from the list, nothing else."
                )
                try:
                    choice = self.llm.generate(prompt).strip().strip("\"'")
                    if choice in cands:
                        return choice, self.mapper.get_id(choice)
                except Exception as e:
                    # 2.2: log LLM disambiguation failures for observability
                    logger.warning("[resolve_entity] LLM disambiguation failed for '%s': %s", name, e)
            return cands[0], self.mapper.get_id(cands[0])

        # Level 3: LLM normalisation
        if self.llm:
            try:
                norm = self.llm.generate(
                    f"What is the full official Wikidata/Wikipedia name of '{name}'? "
                    f"Output ONLY the name, nothing else."
                ).strip().strip("\"'")
                wd_id = self.mapper.get_id(norm)
                if wd_id:
                    return norm, wd_id
                cands2 = self.mapper.search_names(norm, limit=5)
                if cands2:
                    return cands2[0], self.mapper.get_id(cands2[0])
            except Exception as e:
                # 2.2: log LLM normalisation failures for observability
                logger.warning("[resolve_entity] LLM normalisation failed for '%s': %s", name, e)

        return name, None

    # ------------------------------------------------------------------
    # Graph candidates (Neo4j via KGNavigator)
    # ------------------------------------------------------------------

    def _get_graph_candidates(self, wd_ids: List[str], names: List[str]) -> List[Quadruplet]:
        """Graph candidate retrieval — supports KuzuDB, Neo4j, and InMemory connectors.

        KuzuDB: str_id = md5(name+props), NOT the wd_id. Query by prop['wd_id'] MAP key.
                Name fallback covers: (a) wd_id=None (resolution failure) and
                                      (b) user-ingested entities without wd_id in prop.
        Neo4j: execute_query resolves str_id → internal node.id via BFS.
        InMemory: strid_nodes_index maps str_id → internal integer ids.
        """
        connector = self.kg_model.graph_struct.db_conn

        # ── Branch A: KuzuDB ──────────────────────────────────────────────────
        # build_kg.py sets node.id = QID → KuzuDB stores it as n.str_id.
        # Two separate queries instead of OR to avoid LIMIT-splitting per branch.
        # Explicit [rel:simple] mirrors get_quadruplets() — avoids implicit-rel-type bug.
        # LIMIT 5000: covers ~150 unique quads even with 36x DB pollution from CREATE duplicates.
        if hasattr(connector, 'conn'):
            seen: set = set()
            quads: List[Quadruplet] = []
            for mid in wd_ids:
                for cypher in (
                    "MATCH (n1)-[rel:simple]->(n2) WHERE n1.str_id = $wid "
                    "RETURN n1, rel, n2 LIMIT 1000;",
                    "MATCH (n1)-[rel:simple]->(n2) WHERE n2.str_id = $wid "
                    "RETURN n1, rel, n2 LIMIT 1000;",
                ):
                    try:
                        result = connector.conn.execute(cypher, {"wid": mid})
                        for q in connector.parse_query_quadruplets_output(result):
                            if q.id not in seen:
                                quads.append(q)
                                seen.add(q.id)
                    except Exception as e:
                        logger.warning(
                            "[_get_graph_candidates] KuzuDB str_id query failed for %s: %s", mid, e
                        )
            # Name fallback: triggers when wd_ids=[] (resolution failed) OR str_id returned 0 quads
            if not quads:
                for name in names:
                    if not name:
                        continue
                    for cypher in (
                        "MATCH (n1)-[rel:simple]->(n2) WHERE n1.name = $name "
                        "RETURN n1, rel, n2 LIMIT 1000;",
                        "MATCH (n1)-[rel:simple]->(n2) WHERE n2.name = $name "
                        "RETURN n1, rel, n2 LIMIT 1000;",
                    ):
                        try:
                            result = connector.conn.execute(cypher, {"name": name})
                            for q in connector.parse_query_quadruplets_output(result):
                                if q.id not in seen:
                                    quads.append(q)
                                    seen.add(q.id)
                        except Exception as e:
                            logger.warning(
                                "[_get_graph_candidates] KuzuDB name query failed for %s: %s", name, e
                            )
            return quads

        # ── Branch B: Neo4j / InMemory — BFS via KGNavigator (unchanged) ─────
        node_ids = []
        for mid in wd_ids:
            try:
                if hasattr(connector, 'execute_query'):
                    raw = connector.execute_query(
                        'MATCH (n) WHERE n.str_id = $str_id RETURN n',
                        params={'str_id': mid}
                    )
                    if raw:
                        for node in connector.parse_query_nodes_output(raw):
                            node_ids.append(node.id)
                elif hasattr(connector, 'strid_nodes_index'):
                    internal = connector.strid_nodes_index.get(mid, [])
                    node_ids.extend(internal)
            except Exception:
                pass

        if not node_ids:
            return []

        nav = KGNavigator(self.kg_model)
        quads = nav.get_neighborhood(node_ids, depth=1)

        seen, unique = set(), []
        for q in quads:
            if q.id not in seen:
                unique.append(q)
                seen.add(q.id)
        return unique

    # ------------------------------------------------------------------
    # Vector candidates (ChromaDB ANN)
    # ------------------------------------------------------------------

    def _get_vector_candidates(
        self, question: str, top_n: int = 50
    ) -> Tuple[List[Quadruplet], Dict[str, float]]:
        """
        ChromaDB ANN search on quadruplet embeddings.
        Returns (quadruplets, {quad_id -> e5_score}).
        ChromaDB 'ip' space: sim = 1.0 - distance (for normalised E5 vectors).
        """
        try:
            from ....db_drivers.vector_driver import VectorDBInstance
            embedder = self.kg_model.embeddings_struct.embedder
            q_emb = embedder.encode_queries([question])[0]

            quad_db = self.kg_model.embeddings_struct.vectordbs.get('quadruplets')
            if quad_db is None:
                return [], {}

            raw_results = quad_db.retrieve(
                query_instances=[VectorDBInstance(embedding=q_emb)],
                n_results=top_n,
                includes=['documents', 'metadatas']
            )
            if not raw_results:
                return [], {}

            # Build t_id → score from ChromaDB results (vdb_inst is NOT a Quadruplet)
            t_id_scores = {}
            for dist, vdb_inst in raw_results[0]:
                sim = max(0.0, min(1.0, 1.0 - float(dist)))
                t_id = (vdb_inst.metadata or {}).get('t_id')
                if t_id:
                    t_id_scores[t_id] = sim

            if not t_id_scores:
                return [], {}

            # Fetch full Quadruplet objects from KuzuDB by t_id
            db_conn = self.kg_model.graph_struct.db_conn
            quads = db_conn.read(list(t_id_scores.keys()))
            scores = {q.id: t_id_scores[q.id] for q in quads if q.id in t_id_scores}
            return quads, scores
        except Exception as e:
            print(f"WARNING: [HybridRetriever] Vector search failed: {e}")
            return [], {}

    # ------------------------------------------------------------------
    # E5 scores for graph-only candidates
    # ------------------------------------------------------------------

    def _get_e5_for_graph_candidates(
        self, question: str, quads: List[Quadruplet]
    ) -> Dict[str, float]:
        """
        Compute E5 cosine scores for candidates not returned by ChromaDB.
        Uses read_embbeddings() from the embeddings model — no SentenceTransformer.encode() call.
        Falls back to encode_passages() if read_embbeddings is unavailable.
        """
        if not quads:
            return {}

        embedder = self.kg_model.embeddings_struct.embedder
        q_emb = embedder.encode_queries([question])[0]

        scores = {}
        try:
            emb_struct = self.kg_model.embeddings_struct
            if hasattr(emb_struct, 'vectordbs') and 'quadruplets' in emb_struct.vectordbs:
                q_emb_norm = np.linalg.norm(q_emb)
                rel_to_quads: dict = defaultdict(list)
                for q in quads:
                    rel_to_quads[q.relation.id].append(q)
                instances = emb_struct.vectordbs['quadruplets'].read(
                    list(rel_to_quads.keys()), includes=['embeddings'])
                for inst in instances:
                    if inst.embedding is None:
                        continue
                    emb = np.array(inst.embedding)
                    score_val = float(max(0.0, np.dot(q_emb, emb) / (q_emb_norm * np.linalg.norm(emb) + 1e-9)))
                    for q in rel_to_quads.get(inst.id, []):
                        scores[q.id] = score_val
                if scores:
                    return scores
        except Exception:
            pass

        # Fallback: encode_passages
        texts = [QuadrupletCreator.stringify(q)[1] for q in quads]
        embs = embedder.encode_passages(texts)
        for q, emb in zip(quads, embs):
            norm = np.linalg.norm(q_emb) * np.linalg.norm(emb) + 1e-9
            scores[q.id] = float(max(0.0, np.dot(q_emb, emb) / norm))
        return scores

    # ------------------------------------------------------------------
    # HOP 1: resolve anchor event year
    # ------------------------------------------------------------------

    def _resolve_hop1_time(
        self, anchor_ent_id: str, anchor_event: str, question: str
    ) -> Optional[str]:
        """
        Resolve the year of an anchor event via KGNavigator + embedding similarity.
        Encodes anchor_event text once; ranks stored quad embeddings from ChromaDB.
        """
        try:
            hop_quads = self._get_graph_candidates([anchor_ent_id], [])[:15]
            if not hop_quads:
                return None

            embedder = self.kg_model.embeddings_struct.embedder
            # Single SentenceTransformer call in the retrieval path
            query_vec = embedder.encode_queries(['query: ' + anchor_event])[0]

            emb_struct = self.kg_model.embeddings_struct
            if hasattr(emb_struct, 'vectordbs') and 'quadruplets' in emb_struct.vectordbs:
                qv_norm = np.linalg.norm(query_vec)
                rel_to_quads: dict = defaultdict(list)
                for q in hop_quads:
                    rel_to_quads[q.relation.id].append(q)
                instances = emb_struct.vectordbs['quadruplets'].read(
                    list(rel_to_quads.keys()), includes=['embeddings'])
                ranked = []
                for inst in instances:
                    if inst.embedding is None:
                        continue
                    emb = np.array(inst.embedding)
                    sim = float(np.dot(query_vec, emb) / (qv_norm * np.linalg.norm(emb) + 1e-9))
                    for q in rel_to_quads.get(inst.id, []):
                        ranked.append((sim, q))
                ranked.sort(key=lambda x: x[0], reverse=True)
                top_quads = [q for _, q in ranked[:15]]
            else:
                top_quads = hop_quads[:15]

            ctx = '\n'.join(QuadrupletCreator.stringify(q)[1] for q in top_quads)
            raw = self.llm.generate(
                f"FACTS:\n{ctx}\n\nExtract ONLY the 4-digit YEAR for "
                f"'{anchor_event}' of the anchor entity:"
            ).strip()
            m = re.search(r'(\d{4})', raw)
            if m:
                return m.group(1)
        except Exception as e:
            print(f"WARNING: [HybridRetriever] HOP 1 failed: {e}")
        return None

    # ------------------------------------------------------------------
    # Temporal filters
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_years(quad: Quadruplet) -> Tuple[Optional[int], Optional[int]]:
        if not quad.time or quad.time.name in ('Always', 'Unknown'):
            return None, None
        years = sorted(int(y) for y in re.findall(r'(\d{4})', quad.time.name))
        if not years:
            return None, None
        return years[0], years[-1]

    def _apply_before_after_filter(
        self, candidates: List[Quadruplet], ref_year: int, is_before: bool
    ) -> List[Quadruplet]:
        filtered = []
        for q in candidates:
            sy, ey = self._parse_years(q)
            if sy is None:
                continue
            if is_before and sy < ref_year:
                filtered.append(q)
            elif not is_before and (ey or 0) > ref_year:
                filtered.append(q)
        return filtered

    def _build_temporal_bucket(
        self, all_candidates: List[Quadruplet], t_int: int
    ) -> List[Quadruplet]:
        bucket = []
        seen = set()
        for q in all_candidates:
            sy, ey = self._parse_years(q)
            if sy is not None and ey is not None and sy <= t_int <= ey and q.id not in seen:
                bucket.append(q)
                seen.add(q.id)
        return bucket

    # ------------------------------------------------------------------
    # Main run
    # ------------------------------------------------------------------

    def run(self, question: str, extraction) -> RetrievalResult:
        from src.pipelines.qa.stages.extraction import ExtractionResult
        ext: ExtractionResult = extraction

        # --- compute search_k ---
        filter_temporal = ext.q_type in ('before_after', 'time_join')
        search_k = (
            50
            if (filter_temporal or ext.q_type in ('simple_time', 'first_last'))
            else self.config.search_k_floor
        )

        # --- Stage 3: HOP 1 ---
        resolved_time = ext.query_time
        if ext.anchor_entity and ext.anchor_event and not ext.query_time and ext.q_type != 'simple_time':
            print(f'[HOP 1] Resolving "{ext.anchor_event}" year for "{ext.anchor_entity}"...')
            _, a_wd = self.resolve_entity(ext.anchor_entity)
            if a_wd:
                year = self._resolve_hop1_time(a_wd, ext.anchor_event, question)
                if year:
                    resolved_time = year
                    print(f'  -> HOP 1 resolved year: {resolved_time}')
        else:
            print('[HOP 1] Skipped.')

        # --- Stage 4: Retrieval ---
        resolved_entities = []
        graph_quads: List[Quadruplet] = []

        for ent in ext.entities:
            res_name, wd_id = self.resolve_entity(ent)
            resolved_entities.append((ent, res_name, wd_id))
            batch = self._get_graph_candidates(
                [wd_id] if wd_id else [],
                [res_name]
            )
            graph_quads.extend(batch)
            print(f'  {len(batch)} graph quads for "{res_name}" (wd_id={wd_id})')

        # Deduplicate graph quads
        seen_ids: set = set()
        unique_graph: List[Quadruplet] = []
        for q in graph_quads:
            if q.id not in seen_ids:
                unique_graph.append(q)
                seen_ids.add(q.id)

        # Vector search
        vector_quads: List[Quadruplet] = []
        vector_scores: Dict[str, float] = {}
        if self.use_vector_search:
            vector_quads, vector_scores = self._get_vector_candidates(question, top_n=search_k)

        # Merge: vector quads first, then graph-only quads
        merged_ids: set = {q.id for q in vector_quads}
        graph_only = [q for q in unique_graph if q.id not in merged_ids]
        all_candidates = vector_quads + graph_only

        # E5 scores for graph-only candidates
        graph_scores = self._get_e5_for_graph_candidates(question, graph_only)
        candidate_e5_scores = {**vector_scores, **graph_scores}

        # Final dedup
        seen2: set = set()
        unique_candidates: List[Quadruplet] = []
        for q in all_candidates:
            if q.id not in seen2:
                unique_candidates.append(q)
                seen2.add(q.id)

        # Adaptive search_k: sub-linear growth capped at n_unique (notebook-aligned)
        # time_join gets max(search_k, 20) below — unchanged
        n_unique = len(unique_candidates)
        if not (filter_temporal or ext.q_type in ('simple_time', 'first_last')):
            search_k = min(n_unique, max(self.config.search_k_floor, int(n_unique ** 0.55)))

        # Temporal filters
        if ext.q_type == 'before_after' and resolved_time:
            try:
                ref = int(resolved_time)
                q_lower = question.lower()
                is_before = any(w in q_lower for w in self.config.before_words)
                filtered = self._apply_before_after_filter(unique_candidates, ref, is_before)
                if filtered:
                    unique_candidates = filtered
                    print(f'  before_after pre-filter: {len(filtered)} quads kept')
            except (ValueError, TypeError):
                pass

        temporal_bucket: List[Quadruplet] = []
        if ext.q_type == 'time_join' and resolved_time:
            try:
                t_int = int(resolved_time)
                temporal_bucket = self._build_temporal_bucket(unique_candidates, t_int)
                search_k = max(search_k, 20)
                print(f'  time_join bucket: {len(temporal_bucket)} quads @ {resolved_time}')
            except (ValueError, TypeError):
                pass

        return RetrievalResult(
            unique_candidates=unique_candidates,
            candidate_e5_scores=candidate_e5_scores,
            temporal_bucket=temporal_bucket,
            resolved_entities=resolved_entities,
            resolved_time=resolved_time,
            search_k=search_k,
        )
