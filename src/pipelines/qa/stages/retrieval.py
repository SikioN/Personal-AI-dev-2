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
                    f"В вопросе упоминается сущность '{name}'. "
                    f"Какое из этих названий в базе знаний лучше всего соответствует?\n"
                    f"Варианты: {cand_str}\n"
                    f"Выведи ТОЛЬКО точное название из списка, ничего больше.\n"
                    f"(If the question is in English: Which of these KG names best matches "
                    f"'{name}'? Output ONLY the exact name from the list.)"
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
                    f"Как официально называется сущность '{name}' в Wikidata/Wikipedia? "
                    f"Выведи ТОЛЬКО название, ничего больше. "
                    f"(English fallback: What is the full official name of '{name}'? "
                    f"Output ONLY the name.)"
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

    def _get_graph_candidates(self, wd_ids: List[str], names: List[str], rel_query: str = "") -> List[Quadruplet]:
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
            
            # Sanitization for rel_query
            rel_query_sanitized = rel_query.strip() if rel_query else ""
            
            for mid in wd_ids:
                # If we have a relation query, we try to be specific first
                cyphers = []
                if rel_query_sanitized:
                    cyphers.append(
                        "MATCH (n1)-[rel]->(n2) WHERE n1.str_id = $wid "
                        "AND lower(rel.name) CONTAINS lower($rel) "
                        "RETURN n1, rel, n2 LIMIT 1000;"
                    )
                    cyphers.append(
                        "MATCH (n1)-[rel]->(n2) WHERE n2.str_id = $wid "
                        "AND lower(rel.name) CONTAINS lower($rel) "
                        "RETURN n1, rel, n2 LIMIT 1000;"
                    )
                
                # Always add a broader fallback or primary query
                cyphers.extend([
                    "MATCH (n1)-[rel]->(n2) WHERE n1.str_id = $wid "
                    "RETURN n1, rel, n2 LIMIT 5000;",
                    "MATCH (n1)-[rel]->(n2) WHERE n2.str_id = $wid "
                    "RETURN n1, rel, n2 LIMIT 5000;",
                ])

                for cypher in cyphers:
                    try:
                        params = {"wid": mid}
                        if "$rel" in cypher:
                            params["rel"] = rel_query_sanitized
                            
                        result = connector.conn.execute(cypher, params)
                        for q in connector.parse_query_quadruplets_output(result):
                            if q.id not in seen:
                                quads.append(q)
                                seen.add(q.id)
                                if hasattr(self.config, 'debug') and self.config.debug:
                                    if len(quads) <= 5:
                                        print(f"      [RET] Graph quad: {q}")
                    except Exception as e:
                        logger.warning(
                            "[_get_graph_candidates] KuzuDB query failed for %s (rel=%s): %s", mid, rel_query_sanitized, e
                        )
            
            # Name fallback
            if not quads:
                for name in names:
                    if not name:
                        continue
                    name = name.strip()
                    cyphers = []
                    # For KuzuDB name queries, use CONTAINS instead of direct equality 
                    # to handle partial matches and formatting discrepancies (spaces/dots/etc)
                    if rel_query_sanitized:
                        # Forward & Reverse
                        cyphers.append(
                            "MATCH (n1)-[rel]->(n2) "
                            "WHERE lower(n1.name) CONTAINS lower($name) "
                            "AND lower(rel.name) CONTAINS lower($rel) "
                            "RETURN n1, rel, n2 LIMIT 1000;"
                        )
                        cyphers.append(
                            "MATCH (n1)-[rel]->(n2) "
                            "WHERE lower(n2.name) CONTAINS lower($name) "
                            "AND lower(rel.name) CONTAINS lower($rel) "
                            "RETURN n1, rel, n2 LIMIT 1000;"
                        )
                    cyphers.append(
                        "MATCH (n1)-[rel]->(n2) "
                        "WHERE lower(n1.name) CONTAINS lower($name) "
                        "OR lower(n2.name) CONTAINS lower($name) "
                        "RETURN n1, rel, n2 LIMIT 5000;"
                    )
                    
                    for cypher in cyphers:
                        try:
                            params = {"name": name}
                            if "$rel" in cypher:
                                params["rel"] = rel_query_sanitized
                            
                            # Log the query for debugging
                            logger.info("[KuzuDB] Executing name query: %s with params: %s", cypher, params)
                            
                            result = connector.conn.execute(cypher, params)
                            found_in_this_query = 0
                            for q in connector.parse_query_quadruplets_output(result):
                                found_in_this_query += 1
                                if q.id not in seen:
                                    quads.append(q)
                                    seen.add(q.id)
                            
                            if found_in_this_query > 0:
                                logger.info("[KuzuDB] Found %d quads for name '%s'", found_in_this_query, name)
                        except Exception as e:
                            logger.warning(
                                "[_get_graph_candidates] KuzuDB name query failed for %s (rel=%s): %s", name, rel_query_sanitized, e
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

    # Temporal question prefixes to strip for a secondary focused search
    _TEMPORAL_PREFIXES = (
        'в каком году в ', 'в каком году ',  # longer pattern first
        'в каком году?', 'когда ', 'с какого года ', 'до какого года ',
        'с какого ', 'до какого ', 'в каком ', 'с какого момента ', 'начиная с какого ',
        'when ', 'in what year ', 'since when ', 'what year ',
    )

    @staticmethod
    def _strip_temporal_prefix(question: str) -> str:
        """Remove leading temporal question words to produce a factual phrase."""
        q = question.strip().lower()
        for prefix in HybridRetriever._TEMPORAL_PREFIXES:
            if q.startswith(prefix):
                return question.strip()[len(prefix):].strip(' ?')
        return question

    def _get_vector_candidates(
        self, question: str, top_n: int = 50
    ) -> Tuple[List[Quadruplet], Dict[str, float]]:
        """
        ChromaDB ANN search on quadruplet embeddings.
        For temporal questions also runs a second search with the question prefix
        stripped (e.g. "Когда X составил Y" → also search "X составил Y") to
        improve recall when the question word shifts the embedding.
        Returns (quadruplets, {quad_id -> e5_score}).
        ChromaDB 'ip' space: sim = 1.0 - distance (for normalised E5 vectors).
        """
        try:
            from ....db_drivers.vector_driver import VectorDBInstance
            embedder = self.kg_model.embeddings_struct.embedder

            quad_db = self.kg_model.embeddings_struct.vectordbs.get('quadruplets')
            if quad_db is None:
                return [], {}

            # Build list of queries: primary + optional stripped version
            queries = [question]
            stripped = self._strip_temporal_prefix(question)
            if stripped != question:
                queries.append(stripped)
            # Fix C: second query without numbers for numeric questions
            # Two-stage retrieval reduces false positives caused by numeric token overlap
            # (e.g. "$50bn" in "GenAI pharma $50bn" matching SSD/storage facts)
            import re as _re_fixc
            q_no_nums = _re_fixc.sub(
                r'\b\d+(?:[,\.]\d+)?\s*(?:%|млрд|трлн|млн|billion|trillion|million)?\b',
                '', question
            ).strip()
            if q_no_nums != question and len(q_no_nums) > 10:
                queries.append(q_no_nums)

            t_id_scores: Dict[str, float] = {}
            for q_text in queries:
                q_emb = embedder.encode_queries([q_text])[0]
                raw_results = quad_db.retrieve(
                    query_instances=[VectorDBInstance(embedding=q_emb)],
                    n_results=top_n,
                    includes=['documents', 'metadatas']
                )
                if not raw_results:
                    continue
                for dist, vdb_inst in raw_results[0]:
                    sim = max(0.0, min(1.0, 1.0 - float(dist)))
                    t_id = (vdb_inst.metadata or {}).get('t_id')
                    if t_id:
                        # Keep highest score across queries
                        if t_id not in t_id_scores or sim > t_id_scores[t_id]:
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

        # Always use encode_passages for correct similarity — the relation-ID-based
        # ChromaDB lookup used wrong IDs and could short-circuit with corrupt scores.
        scores = {}
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
        """Resolves the year of an anchor event via KG neighbors and semantic ranking."""
        try:
            # 1. Fetch larger neighborhood (100 quads) to find specific events
            hop_quads = self._get_graph_candidates([anchor_ent_id], [])[:100]
            if not hop_quads:
                return None

            # 2. Semantic ranking
            top_quads = []
            embedder = self.kg_model.embeddings_struct.embedder
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
                    if inst.embedding is None: continue
                    emb = np.array(inst.embedding)
                    sim = float(np.dot(query_vec, emb) / (qv_norm * np.linalg.norm(emb) + 1e-9))
                    for q in rel_to_quads.get(inst.id, []):
                        ranked.append((sim, q))
                
                ranked.sort(key=lambda x: x[0], reverse=True)
                top_quads = [q for _, q in ranked[:20]]
            else:
                top_quads = hop_quads[:20]

            # 3. LLM Extract Year with improved prompt
            from src.utils.data_structs import QuadrupletCreator
            ctx = '\n'.join(f"- {QuadrupletCreator.stringify(q)[1]}" for q in top_quads)
            
            prompt = (
                f"ФАКТЫ о сущности:\n{ctx}\n\n"
                f"На основе ТОЛЬКО этих фактов: в каком году произошло '{anchor_event}'?\n"
                f"Контекст вопроса: {question}\n"
                f"Выведи ТОЛЬКО год (например, 1961) или NULL если не найдено.\n"
                f"(English: Based ONLY on these facts, what year was '{anchor_event}'? "
                f"Output ONLY the year or NULL.)"
            )
            
            raw = self.llm.generate(prompt).strip()
            # 5.1: debug logging to trace HOP 1 hallucinations
            if hasattr(self.config, 'debug') and self.config.debug:
                print(f"  [HOP 1] raw_llm_output={raw!r}")
                
            m = re.search(r'(\d{4})', raw)
            if m:
                return m.group(1)
            
            # 4. Semantic fallback: if LLM failed, take year from the most similar fact (if sim > 0.8)
            if 'ranked' in locals() and ranked:
                best_sim, best_q = ranked[0]
                if best_sim > 0.8:
                    sy, _ = self._parse_years(best_q)
                    if sy:
                        if hasattr(self.config, 'debug') and self.config.debug:
                            print(f"  [HOP 1] LLM failed, using semantic fallback (sim={best_sim:.2f}): {sy}")
                        return str(sy)

        except Exception as e:
            # 5.1: capture HOP 1 failures specifically
            logger.warning("[HybridRetriever] HOP 1 failed for %s: %s", anchor_ent_id, e)
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
            
            # DBG: Detailed resolution info
            src = "DB"
            if wd_id:
                if hasattr(self.mapper, 'manual_overrides') and self.mapper.manual_overrides.get(ent.lower()) == wd_id:
                    src = "MANUAL"
                elif hasattr(self.mapper, 'fallback_name2id') and self.mapper.fallback_name2id.get(ent.lower()) == wd_id:
                    src = "RAM"
            print(f"  - Resolved: '{ent}' -> '{res_name}' ({wd_id}) [via {src}]")

            # [v7 Fix]: Prioritize subject over anchor to reduce noise.
            # Anchor entities (used for year extraction) don't need 5000 quads.
            limit = 5000
            if ext.anchor_entity and ent.lower() == ext.anchor_entity.lower():
                limit = 1000
                
            batch = self._get_graph_candidates(
                [wd_id] if wd_id else [],
                [res_name],
                rel_query=ext.raw.get('relation', '')
            )[:limit]
            graph_quads.extend(batch)
            print(f"    Found {len(batch)} quads in graph for '{res_name}' (limit={limit})")

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

        # E5 scores for graph-only candidates (use original question — preserves natural
        # query form which E5 handles well; temporal stripping caused regression).
        graph_scores = self._get_e5_for_graph_candidates(question, graph_only)
        candidate_e5_scores = {**vector_scores, **graph_scores}

        # Final dedup
        seen2: set = set()
        unique_candidates: List[Quadruplet] = []
        for q in all_candidates:
            if q.id not in seen2:
                unique_candidates.append(q)
                seen2.add(q.id)

        # Keyword boost: guarantee that facts matching key terms from the question
        # always surface into top-12, even when E5 embedding similarity is low.
        _stripped_q = self._strip_temporal_prefix(question)

        # 1) Numerical boost: percentages or financial values (NOT bare years —
        #    "2024" is too common and would spuriously boost unrelated facts).
        _key_nums = set(re.findall(r'\d+(?:[,\.]\d+)?\s*%', _stripped_q))
        if not _key_nums:
            # Also match numbers explicitly followed by financial units
            _key_nums = set(re.findall(
                r'\d+(?:[,\.]\d+)?\s*(?:млрд|трлн|млн|тыс|руб\.?)', _stripped_q
            ))

        # 1b) English financial units (for English-language source documents)
        if not _key_nums:
            _key_nums = set(re.findall(
                r'\d+(?:[,\.]\d+)?\s*(?:billion|trillion|million|thousand|percent)',
                _stripped_q, re.IGNORECASE
            ))

        # 2) Text keyword boost: significant content words (5+ chars), Russian and English.
        #    Excludes stop-words and overly common terms.
        _common_ru = {
            'сколько', 'когда', 'каком', 'какой', 'какая', 'будет', 'этого',
            'которые', 'благодаря', 'составляет', 'является', 'также',
            'сбере', 'сбера', 'сберу', 'имеет', 'каких', 'году', 'годом',
            'количество', 'среднее', 'значение', 'данные',
        }
        _common_en = {
            'which', 'about', 'their', 'there', 'where', 'would', 'could',
            'should', 'first', 'these', 'total', 'other', 'percent', 'billion',
            'million', 'between', 'company', 'what', 'when', 'that', 'with',
        }
        _stop_words = _common_ru | _common_en
        _key_words = set(
            w.lower() for w in re.findall(r'[а-яёА-ЯЁa-zA-Z]{5,}', _stripped_q)
            if w.lower() not in _stop_words
        )

        if _key_nums or len(_key_words) >= 2:
            for cand in unique_candidates:
                _, cand_text = QuadrupletCreator.stringify(cand)
                cand_lower = cand_text.lower()
                # Numerical match: ALL key numbers present in fact text
                nums_match = bool(_key_nums) and all(n in cand_text for n in _key_nums)
                # Text match: at least 2 specific words from question found in fact
                words_hit = sum(1 for w in _key_words if w in cand_lower)
                words_match = len(_key_words) >= 2 and words_hit >= 2
                if (nums_match and words_hit >= 1) or words_match:
                    old = candidate_e5_scores.get(cand.id, 0.0)
                    # Boost only if E5 already considers the fact somewhat relevant (>0.60).
                    # Avoids inflating unrelated facts that merely contain a matching number.
                    # Capped at 0.88 (not 0.97) so semantically strong facts (>0.88) can win.
                    if old > 0.60:
                        candidate_e5_scores[cand.id] = max(old, 0.88)

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
                # 2.8: Force-fetch all neighbors for time_join bucket (notebook alignment)
                # This ensures we don't miss "LBJ was president" just because it's not semantically
                # close to "Nabokov Nobel Prize".
                bucket_candidates = unique_candidates
                if len(ext.entities) > 0:
                    # Fetch extra neighbors specifically for the bucket
                    # 2.8: use local resolved_entities instead of uninstantiated retrieval object
                    extra_ids = [e[2] for e in resolved_entities if e[2]]
                    if extra_ids:
                        # Limit to 2000 to avoid OOM or slow DB response
                        # [v7 Fix]: Pass rel_query to prioritize important facts (e.g. head of government)
                        extra_graph = self._get_graph_candidates(
                            extra_ids, [], 
                            rel_query=ext.raw.get('relation', '')
                        )[:2000]
                        bucket_candidates = list({q.id: q for q in (unique_candidates + extra_graph)}.values())
                
                temporal_bucket = self._build_temporal_bucket(bucket_candidates, t_int)
                search_k = max(search_k, 20)
                print(f'  time_join bucket entries: {len(temporal_bucket)} quads @ {resolved_time}')
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
