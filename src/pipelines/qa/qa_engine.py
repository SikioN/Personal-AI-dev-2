import numpy as np
import torch
import os
import re
from typing import List, Dict, Tuple, Optional

from src.kg_model.knowledge_graph_model import KnowledgeGraphModel
from src.utils.data_structs import Quadruplet, QuadrupletCreator
from src.db_drivers.vector_driver import VectorDBInstance
from src.pipelines.qa.kg_reasoning.medium_reasoner.entities_extractor import EntitiesExtractor, EntitiesExtractorConfig
from src.pipelines.qa.kg_reasoning.medium_reasoner.entities2nodes_matching import Entities2NodesMatcher, Entities2NodesMatcherConfig
from src.utils.kg_navigator import KGNavigator
from src.config.qa_config import QAConfig
from src.llm.base_client import BaseLLMClient
from src.pipelines.qa.stages.extraction import ExtractionStage
from src.pipelines.qa.stages.retrieval import HybridRetriever
from src.pipelines.qa.stages.scoring import ScoringStage
from src.pipelines.qa.stages.generation import GenerationStage


class QAEngine:
    """
    Thin orchestrator for the KG QA pipeline.
    Delegates work to ExtractionStage, HybridRetriever, ScoringStage, GenerationStage.
    """

    def __init__(
        self,
        kg_model: KnowledgeGraphModel,
        finetuned_model_path: str,
        config: Optional[QAConfig] = None,
        llm_client: Optional[BaseLLMClient] = None,
    ):
        self.kg_model = kg_model
        self.config = config or QAConfig.from_env()

        # Override embedder with finetuned weights
        from sentence_transformers import SentenceTransformer
        from src.utils.device_utils import get_device

        if os.path.exists(finetuned_model_path):
            finetuned_model_path = os.path.abspath(finetuned_model_path)
        else:
            print(f"Model path {finetuned_model_path} not found locally, assuming HuggingFace model name.")

        device = get_device()
        self.kg_model.embeddings_struct.embedder.config.model_name_or_path = finetuned_model_path
        self.kg_model.embeddings_struct.embedder.config.device = device
        self.kg_model.embeddings_struct.embedder.model = SentenceTransformer(
            finetuned_model_path,
            device=device
        )

        # LLM client — injected or created from env
        if llm_client is not None:
            self.ollama_client = llm_client
        else:
            self.ollama_client = self._create_llm_from_env()

        # WikidataMapper — Neo4j-backed if connector available, else file-based fallback
        from src.utils.wikidata_utils import WikidataMapper
        connector = self.kg_model.graph_struct.db_conn
        if hasattr(connector, 'execute_query'):
            print("[QAEngine] Using Neo4j-backed WikidataMapper.")
            self.mapper = WikidataMapper(connector)
        else:
            # Legacy: file-based
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.abspath(os.path.join(current_dir, "../../.."))
            kg_data_path = os.path.join(project_root, "wikidata_big/kg")
            if not os.path.exists(kg_data_path):
                kg_data_path = os.path.join(os.getcwd(), "wikidata_big/kg")
            # 2.6: warn loudly when neither path exists — mapper will return empty dicts
            if not os.path.exists(kg_data_path):
                raise FileNotFoundError(
                    f"[QAEngine] KG data path not found: {kg_data_path!r}. "
                    "Set KG_DATA_PATH env var or provide a Neo4j-backed connector."
                )
            print(f"[QAEngine] Using file-based WikidataMapper at: {kg_data_path}")
            self.mapper = WikidataMapper(kg_data_path)

        # Nodes matcher (used by get_ranked_results)
        self.entities_extractor = EntitiesExtractor()
        self.nodes_matcher = Entities2NodesMatcher(self.kg_model)

        # Temporal scorer
        self.temporal_scorer = None
        try:
            from src.kg_model.temporal.temporal_model import TemporalScorer
            self.temporal_scorer = TemporalScorer(device=get_device())
        except Exception as e:
            print(f"Warning: Could not initialize TemporalScorer: {e}")

        # Stage modules
        self._extraction_stage = ExtractionStage(self.ollama_client, self.config)
        self._retrieval_stage = HybridRetriever(
            self.kg_model, self.mapper, self.ollama_client, self.config
        )
        self._scoring_stage = ScoringStage(
            self.kg_model.embeddings_struct, self.temporal_scorer, self.config
        )
        self._generation_stage = GenerationStage(self.ollama_client, self.mapper, self.config)

    # ------------------------------------------------------------------
    # LLM factory (backward-compat)
    # ------------------------------------------------------------------

    def _create_llm_from_env(self) -> Optional[BaseLLMClient]:
        backend = os.environ.get("LLM_BACKEND", "ollama").lower()
        try:
            if backend == "yandexgpt":
                from src.llm.yandex_gpt_client import YandexGPTClient
                api_key = os.environ.get("YANDEX_API_KEY", "")
                folder_id = os.environ.get("YANDEX_FOLDER_ID", "")
                model_name = os.environ.get("YANDEX_MODEL", "yandexgpt")
                if not api_key or not folder_id:
                    print("Warning: YANDEX_API_KEY or YANDEX_FOLDER_ID not set.")
                    return None
                print(f"[LLM] Using YandexGPT backend: {model_name}")
                return YandexGPTClient(api_key=api_key, folder_id=folder_id, model_name=model_name)
            elif backend == "deepseek":
                from src.llm.deepseek_client import DeepSeekClient
                print("[LLM] Using DeepSeek backend.")
                return DeepSeekClient(
                    api_key=os.environ.get("DEEPSEEK_API_KEY", ""),
                    model=os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
                )
            elif backend == "gigachat":
                from src.llm.gigachat_client import GigaChatClient
                print("[LLM] Using GigaChat backend.")
                return GigaChatClient(
                    credentials=os.environ.get("GIGACHAT_CREDENTIALS", ""),
                    model=os.environ.get("GIGACHAT_MODEL", "GigaChat"),
                )
            elif backend in ("openai", "chatgpt"):
                from src.llm.openai_client import OpenAIClient
                print(f"[LLM] Using OpenAI backend: {os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')}")
                return OpenAIClient(
                    api_key=os.environ.get("OPENAI_API_KEY", ""),
                    model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
                    base_url=os.environ.get("OPENAI_BASE_URL") or None,
                )
            elif backend == "qwen":
                from src.llm.qwen_client import QwenClient
                print(f"[LLM] Using Qwen backend: {os.environ.get('QWEN_MODEL', 'qwen-plus')}")
                return QwenClient(
                    api_key=os.environ.get("QWEN_API_KEY", ""),
                    model=os.environ.get("QWEN_MODEL", "qwen-plus"),
                )
            else:  # ollama (default)
                from src.llm.ollama_client import OllamaClient
                ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
                ollama_model = os.environ.get("OLLAMA_MODEL", "llama3.2")
                print(f"[LLM] Using Ollama backend: {ollama_model} @ {ollama_url}")
                return OllamaClient(model=ollama_model)
        except Exception as e:
            print(f"Warning: Could not initialize LLM client for backend '{backend}': {e}")
            return None

    # ------------------------------------------------------------------
    # get_ranked_results — public, used by app.py (DO NOT change signature)
    # ------------------------------------------------------------------

    def get_ranked_results(self, query: str, top_k: int = 5) -> List[Dict]:
        """Process query and return ranked quadruplets with confidence scores."""
        query_time = None
        entities = []
        relation_hint = None

        if self.ollama_client:
            try:
                ollama_params = self.ollama_client.extract_search_parameters(query)
                extracted_entities = ollama_params.get("entities", [])
                if isinstance(extracted_entities, list):
                    entities.extend(extracted_entities)
                elif isinstance(extracted_entities, str):
                    entities.append(extracted_entities)
                if ollama_params.get("entity"):
                    entities.append(ollama_params.get("entity"))
                entities = list(set(entities))
                if ollama_params.get("time"):
                    query_time = ollama_params["time"]
                if ollama_params.get("relation"):
                    relation_hint = ollama_params["relation"]
                print(f"DEBUG: [Ollama] Entities: {entities}, Time: {query_time}, Relation: {relation_hint}")
            except Exception as e:
                print(f"DEBUG: [Ollama] Extraction failed: {e}")

        if not entities:
            print("DEBUG: [Fallback] triggering Regex/Legacy extraction...")
            try:
                extraction_result, info = self.entities_extractor.perform(query)
                if isinstance(extraction_result, dict):
                    entities = extraction_result.get('entities', [])
                    if not query_time:
                        query_time = extraction_result.get('time')
                else:
                    entities = extraction_result
            except Exception:
                words = re.findall(r'[A-Z][a-z]+', query)
                entities = list(set([query] + words))
            if not entities:
                entities = [query]

        # Map entities to Wikidata IDs
        mapped_ids = []
        for ent in entities:
            wd_id = self.mapper.get_id(ent)
            print(f"DEBUG: [Mapper] '{ent}' -> Wikidata ID: {wd_id}")
            if wd_id:
                mapped_ids.append(wd_id)

        search_candidates = list(set(entities + mapped_ids))
        all_matched_nodes = []

        connector = self.kg_model.graph_struct.db_conn
        valid_db_ids = []
        for mid in mapped_ids:
            try:
                if hasattr(connector, 'execute_query'):
                    raw_output = connector.execute_query(
                        'MATCH (n) WHERE n.str_id = $str_id RETURN n',
                        params={'str_id': mid}
                    )
                    if raw_output:
                        matched_nodes = connector.parse_query_nodes_output(raw_output)
                        for node in matched_nodes:
                            all_matched_nodes.append(node)
                        valid_db_ids.append(mid)
                elif hasattr(connector, 'strid_nodes_index'):
                    internal_ids = connector.strid_nodes_index.get(mid)
                    if internal_ids:
                        for iid in internal_ids:
                            if iid in connector.nodes:
                                all_matched_nodes.append(connector.nodes[iid])
            except Exception as e:
                print(f"DEBUG: [Graph Lookup Error] {e}")

        matched_nodes_dict, _ = self.nodes_matcher.perform(search_candidates)
        for nodes in matched_nodes_dict.values():
            for n in nodes:
                if hasattr(n, 'id') and hasattr(connector, 'nodes') and n.id in connector.nodes:
                    all_matched_nodes.append(connector.nodes[n.id])
                elif hasattr(n, 'name'):
                    all_matched_nodes.append(n)

        unique_nodes = {}
        for n in all_matched_nodes:
            unique_nodes[n.id] = n
        all_matched_nodes = list(unique_nodes.values())

        self.last_extraction = {
            'entities': entities,
            'mapped_ids': mapped_ids,
            'matched_node_ids': [n.id for n in all_matched_nodes],
            'matched_node_names': [n.name for n in all_matched_nodes],
        }

        if not all_matched_nodes:
            print(f"DEBUG: Triggering vector fallback for query: '{query}'")
            query_emb = self.kg_model.embeddings_struct.embedder.encode_queries([query])[0]
            raw_node_search = self.kg_model.embeddings_struct.vectordbs['nodes'].retrieve(
                query_instances=[VectorDBInstance(embedding=query_emb)],
                n_results=10, includes=['documents'])[0]
            all_matched_nodes = [res[1] for res in raw_node_search if res[0] < 0.75]
            if all_matched_nodes:
                self.last_extraction['fallback_triggered'] = True
                self.last_extraction['matched_node_ids'] = [n.id for n in all_matched_nodes]

        if not all_matched_nodes:
            return []

        node_ids = valid_db_ids if valid_db_ids else [n.id for n in all_matched_nodes]
        nav = KGNavigator(self.kg_model)
        candidate_quadruplets = nav.get_neighborhood(node_ids, depth=1)

        if not candidate_quadruplets:
            return []

        seen_q_ids = set()
        unique_candidates = []
        for q in candidate_quadruplets:
            if q.id not in seen_q_ids:
                unique_candidates.append(q)
                seen_q_ids.add(q.id)

        query_emb = self.kg_model.embeddings_struct.embedder.encode_queries([query])[0]
        quadruplet_texts = [QuadrupletCreator.stringify(q)[1] for q in unique_candidates]
        quadruplet_embs = self.kg_model.embeddings_struct.embedder.encode_passages(quadruplet_texts)

        def sigmoid(x):
            return 1 / (1 + np.exp(-x))

        results = []
        for q, text, emb in zip(unique_candidates, quadruplet_texts, quadruplet_embs):
            score = np.dot(query_emb, emb) / (np.linalg.norm(query_emb) * np.linalg.norm(emb) + 1e-9)
            e5_confidence = float(max(0, score))
            final_confidence = e5_confidence
            temporal_debug = None

            scoring_time = query_time
            if not scoring_time and q.time and q.time.name not in ["Always", "Unknown"]:
                raw_time = q.time.name
                scoring_time = raw_time.split(' - ')[0] if ' - ' in raw_time else raw_time

            if scoring_time and self.temporal_scorer:
                s_qid = q.start_node.prop.get('wd_id') or self.mapper.get_id(q.start_node.name)
                r_pid = q.relation.prop.get('wd_id') or self.mapper.get_id(q.relation.name)
                o_qid = q.end_node.prop.get('wd_id') or self.mapper.get_id(q.end_node.name)
                if s_qid and r_pid and o_qid:
                    try:
                        t_score_logit = self.temporal_scorer.score(s_qid, r_pid, o_qid, scoring_time)
                        if t_score_logit > -9.0:
                            t_prob = sigmoid(t_score_logit)
                            final_confidence = (e5_confidence * 0.7) + (t_prob * 0.3)
                            temporal_debug = f"{t_prob:.2f} (Logit: {t_score_logit:.2f})"
                        else:
                            temporal_debug = "None (Unknown to Scorer)"
                    except Exception:
                        temporal_debug = "Error"

            if relation_hint and relation_hint.lower() in q.relation.name.lower():
                final_confidence = min(1.0, final_confidence * 1.2)
                semantic_debug = f"{e5_confidence:.2f} (+RelBoost)"
            else:
                semantic_debug = f"{e5_confidence:.2f}"

            results.append({
                'quadruplet': q,
                'text': text,
                'confidence': final_confidence,
                'temporal_score': temporal_debug,
                'semantic_score': semantic_debug,
            })

        results.sort(key=lambda x: x['confidence'], reverse=True)
        return results[:top_k]

    # ------------------------------------------------------------------
    # ask() — main 7-stage pipeline (public, unchanged signature)
    # ------------------------------------------------------------------

    def ask(self, question: str, top_k: int = 10, debug: bool = False) -> str:
        """
        Full 7-stage QA pipeline via stage modules:
          1. ExtractionStage  — LLM parses question
          2. Config           — alpha / search_k / flags set inside ExtractionResult
          3-4. HybridRetriever — HOP 1 + entity resolution + graph + vector retrieval
          5. ScoringStage     — E5 (from RetrievalResult) + TComplEx + gap selection
          6. GenerationStage  — anonymized Q-ID answer → decode
        """
        SEP = '=' * 70
        print(f'\n{SEP}\n[ask] QUESTION: {question}\n{SEP}')

        if not self.ollama_client:
            return "LLM client not available. Set LLM_BACKEND=yandexgpt or ensure Ollama is running."

        # Stage 1 + 2
        print('[1/7] Extracting parameters...')
        extraction = self._extraction_stage.run(question)
        if debug:
            print(f'  ext={extraction}')
        print(f'[2/7] type={extraction.q_type}, alpha={extraction.alpha}')

        # Stage 3 + 4: HOP 1 + Retrieval
        print('[3-4/7] HOP 1 + Retrieval...')
        retrieval = self._retrieval_stage.run(question, extraction)
        print(f'  {len(retrieval.unique_candidates)} unique candidates, '
              f'time={retrieval.resolved_time}, search_k={retrieval.search_k}')

        if not retrieval.unique_candidates:
            print('[ask] No candidates found.')
            return 'Unknown'

        # Stage 5: Scoring + gap selection
        print(f'[5/7] Scoring {len(retrieval.unique_candidates)} candidates...')
        scoring = self._scoring_stage.run(question, retrieval, extraction)
        print(f'  Selected {len(scoring.selected_quads)} facts after gap selection.')

        if debug:
            for r in scoring.all_scored[:5]:
                print(f"  [{r.conf:.3f}] E5={r.e5:.3f} T={r.tp:.3f}")

        # Stage 6 (skipped — replaced by gap selection in ScoringStage)
        print('[6/7] Fact selection done via confidence gap (no extra LLM call).')

        # Stage 7: Generation
        print('[7/7] Generating answer...')
        generation = self._generation_stage.run(
            question, scoring.selected_quads, extraction, retrieval
        )

        answer = generation.answer
        print(f'\n{SEP}\n>>> ANSWER: {answer}\n{SEP}\n')
        return answer

    def hot_reload_scorer(self, checkpoint_path: str) -> None:
        """Atomically replace TComplEx scorer without stopping inference (GIL-safe)."""
        from src.kg_model.temporal.temporal_model import TemporalScorer
        from src.utils.device_utils import get_device
        import logging as _logging
        new_scorer = TemporalScorer(device=get_device())
        # CPython GIL guarantees object-reference assignment is atomic
        self.temporal_scorer = new_scorer
        self._scoring_stage.temporal_scorer = new_scorer
        _logging.getLogger(__name__).info(
            "TComplEx scorer hot-reloaded from %s", checkpoint_path
        )

    # 1.4: status() required by /status handler when in production mode
    def status(self) -> dict:
        llm_name = type(self.ollama_client).__name__ if self.ollama_client else "None"
        return {"mode": "production", "llm": llm_name}

    def ask_base(self, question: str, top_k: int = 10) -> str:
        """
        Baseline pipeline: exact-match entity resolution + raw E5 cosine (no TComplEx).
        Used for benchmark comparison.
        """
        if not self.ollama_client:
            return 'Unknown'

        ext = self._extraction_stage.run(question)
        candidates: List[Quadruplet] = []
        for ent in ext.entities:
            wd_id = self.mapper.get_id(ent)
            if wd_id:
                batch = self._retrieval_stage._get_graph_candidates([wd_id], [ent])
                candidates.extend(batch)

        if not candidates:
            return 'Unknown'

        embedder = self.kg_model.embeddings_struct.embedder
        q_emb = embedder.encode_queries([question])[0]
        texts = [QuadrupletCreator.stringify(q)[1] for q in candidates]
        embs = embedder.encode_passages(texts)

        scored = []
        for quad, text, emb in zip(candidates, texts, embs):
            norm = np.linalg.norm(q_emb) * np.linalg.norm(emb) + 1e-9
            e5 = float(max(0.0, np.dot(q_emb, emb) / norm))
            scored.append((e5, quad))

        scored.sort(key=lambda x: x[0], reverse=True)
        top_quads = [q for _, q in scored[:5]]

        from src.pipelines.qa.stages.retrieval import RetrievalResult
        fake_retrieval = RetrievalResult(
            unique_candidates=top_quads,
            candidate_e5_scores={},
            temporal_bucket=[],
            resolved_entities=[(e, e, self.mapper.get_id(e)) for e in ext.entities],
            resolved_time=ext.query_time,
            search_k=top_k,
        )
        generation = self._generation_stage.run(question, top_quads, ext, fake_retrieval)
        return generation.answer
