import numpy as np
import torch
import os
import re
import time
import logging
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)

from src.kg_model.knowledge_graph_model import KnowledgeGraphModel
from src.utils.data_structs import Quadruplet, QuadrupletCreator
from src.db_drivers.vector_driver import VectorDBInstance
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
            self.llm_client = llm_client
        else:
            self.llm_client = self._create_llm_from_env()

        # WikidataMapper — Neo4j-backed if connector available, else file-based fallback
        from src.utils.wikidata_utils import WikidataMapper
        connector = self.kg_model.graph_struct.db_conn
        if hasattr(connector, 'execute_query'):
            print("[QAEngine] Using Neo4j-backed WikidataMapper.")
            self.mapper = WikidataMapper(connector)
        else:
            # Legacy: file-based
            kg_data_path = os.environ.get('KG_DATA_PATH', None)
            if not kg_data_path:
                current_dir = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.abspath(os.path.join(current_dir, "../../.."))
                kg_data_path = os.path.join(project_root, "wikidata_big/kg")
                if not os.path.exists(kg_data_path):
                    kg_data_path = os.path.join(os.getcwd(), "wikidata_big/kg")
            # 2.6: warn loudly when neither path exists — mapper will return empty dicts
            if not os.path.exists(kg_data_path):
                print(
                    f"[QAEngine] WARNING: KG data path not found: {kg_data_path!r}. "
                    "Entity resolution will be empty. Set KG_DATA_PATH env var."
                )
            print(f"[QAEngine] Using file-based WikidataMapper at: {kg_data_path}")
            self.mapper = WikidataMapper(kg_data_path)


        # Temporal scorer
        self.temporal_scorer = None
        try:
            from src.kg_model.temporal.temporal_model import TemporalScorer
            self.temporal_scorer = TemporalScorer(
                checkpoint_path=self.config.tcomplex_checkpoint,
                data_path=self.config.tcomplex_data_path,
                device=get_device(),
            )
        except Exception as e:
            print(f"Warning: Could not initialize TemporalScorer: {e}")

        # Stage modules
        self._extraction_stage = ExtractionStage(self.llm_client, self.config)
        self._retrieval_stage = HybridRetriever(
            self.kg_model, self.mapper, self.llm_client, self.config
        )
        self._scoring_stage = ScoringStage(
            self.kg_model.embeddings_struct, self.temporal_scorer, self.config
        )
        self._generation_stage = GenerationStage(self.llm_client, self.mapper, self.config)

    # ------------------------------------------------------------------
    # LLM factory (backward-compat)
    # ------------------------------------------------------------------

    def _create_llm_from_env(self) -> Optional[BaseLLMClient]:
        backend = os.environ.get("LLM_BACKEND", "deepseek").lower()
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
        """Process query and return ranked quadruplets with confidence scores using modern stages."""
        if not self.llm_client:
            return []

        # 1. Extract
        extraction = self._extraction_stage.run(query)

        # 2. Retrieve
        retrieval = self._retrieval_stage.run(query, extraction)
        if not retrieval.unique_candidates:
            return []

        # 3. Score
        scoring = self._scoring_stage.run(query, retrieval, extraction)

        # 4. Format for bot (/facts, /graph)
        results = []
        for r in scoring.all_scored[:top_k]:
            results.append({
                'quadruplet': r.quad,
                'text': QuadrupletCreator.stringify(r.quad)[1],
                'confidence': r.conf,
                'temporal_score': f"{r.tp:.2f} (Logit: {r.tl:.2f})" if r.tl != float('-inf') else "None",
                'semantic_score': f"{r.e5:.2f}"
            })

        return results

    # ------------------------------------------------------------------
    # ask() — main 6-stage pipeline (public, unchanged signature)
    # ------------------------------------------------------------------

    def ask(self, question: str, top_k: int = 10, debug: bool = False) -> str:
        """
        Full QA pipeline via stage modules (notebook-aligned):
          [1/4] ExtractionStage  — LLM parses question → q_type, entities, alpha
          [2/4] HybridRetriever  — HOP 1 + entity resolution + graph + vector retrieval
          [3/4] ScoringStage     — E5 + TComplEx + gap-based fact selection
          [4/4] GenerationStage  — anonymized Q-ID answer → decode
        """
        import time as _time

        SEP = '=' * 70
        print(f'\n{SEP}\n[ask] QUESTION: {question}\n{SEP}')

        if not self.llm_client:
            return "LLM client not available. Set LLM_BACKEND=yandexgpt or ensure Ollama is running."

        timings: dict = {}
        t0 = _time.time()
        t_s = t0

        # Stage 1: Extraction
        print('\n[1/4] Extracting...')
        extraction = self._extraction_stage.run(question)
        timings['extract'] = round(_time.time() - t_s, 2); t_s = _time.time()
        if debug:
            print(f'  ext={extraction}')
        print(f'  type={extraction.q_type}, alpha={extraction.alpha:.2f}')

        # Stage 2: HOP 1 + Retrieval
        print('\n[2/4] Retrieving...')
        retrieval = self._retrieval_stage.run(question, extraction)
        timings['retrieve'] = round(_time.time() - t_s, 2); t_s = _time.time()
        print(f'  {len(retrieval.unique_candidates)} unique candidates, '
              f'time={retrieval.resolved_time}, search_k={retrieval.search_k}')

        if not retrieval.unique_candidates:
            print('[ask] No candidates found.')
            return 'Unknown'

        # Stage 3: Scoring + gap selection
        print(f'\n[3/4] Scoring {len(retrieval.unique_candidates)} candidates...')
        scoring = self._scoring_stage.run(question, retrieval, extraction)
        timings['score'] = round(_time.time() - t_s, 2); t_s = _time.time()
        print(f'  Selected {len(scoring.selected_quads)} facts after gap selection.')

        if debug:
            for r in scoring.all_scored[:5]:
                print(f"  [{r.conf:.3f}] E5={r.e5:.3f} T={r.tp:.3f} tl={r.tl:.1f}")

        # Stage 4: Generation
        print('\n[4/4] Generating answer...')
        generation = self._generation_stage.run(
            question, scoring.selected_quads, extraction, retrieval
        )
        timings['generate'] = round(_time.time() - t_s, 2)

        answer = generation.answer
        timing_str = ' | '.join(f'{k}={v}s' for k, v in timings.items())
        total = round(_time.time() - t0, 2)
        print(f'\n{SEP}\n>>> ANSWER: {answer}  ({total}s)\n[TIMING] {timing_str}\n{SEP}\n')
        return answer

    def ask_full(self, question: str, top_k: int = 10, debug: bool = False) -> tuple:
        """
        Single-pass pipeline: returns (answer, ranked_results) to avoid double execution.
        answer is None when LLM call failed.
        ranked_results: facts used by LLM come first (_used_by_llm=True), rest fill up to top_k.
        """
        if not self.llm_client:
            return "LLM client not available.", []

        t0 = time.perf_counter()
        extraction = self._extraction_stage.run(question)
        t1 = time.perf_counter()

        retrieval = self._retrieval_stage.run(question, extraction)
        t2 = time.perf_counter()
        if not retrieval.unique_candidates:
            logger.debug("[ask_full] extraction=%.3fs retrieval=%.3fs → no candidates", t1 - t0, t2 - t1)
            return 'Unknown', []

        scoring = self._scoring_stage.run(question, retrieval, extraction)
        t3 = time.perf_counter()

        generation = self._generation_stage.run(
            question, scoring.selected_quads, extraction, retrieval
        )
        t4 = time.perf_counter()

        logger.info(
            "[ask_full] extraction=%.3fs retrieval=%.3fs scoring=%.3fs generation=%.3fs total=%.3fs",
            t1 - t0, t2 - t1, t3 - t2, t4 - t3, t4 - t0,
        )

        # Build ranked_results: selected (seen by LLM) first, then rest up to top_k
        selected_ids = {q.id for q in scoring.selected_quads}
        ranked = []
        for r in scoring.all_scored:
            if r.quad.id in selected_ids:
                ranked.append({
                    'quadruplet': r.quad,
                    'text': QuadrupletCreator.stringify(r.quad)[1],
                    'confidence': r.conf,
                    'temporal_score': f"{r.tp:.2f} (Logit: {r.tl:.2f})" if r.tl != float('-inf') else "None",
                    'semantic_score': f"{r.e5:.2f}",
                    '_used_by_llm': True,
                })
        for r in scoring.all_scored:
            if r.quad.id not in selected_ids and len(ranked) < top_k:
                ranked.append({
                    'quadruplet': r.quad,
                    'text': QuadrupletCreator.stringify(r.quad)[1],
                    'confidence': r.conf,
                    'temporal_score': f"{r.tp:.2f} (Logit: {r.tl:.2f})" if r.tl != float('-inf') else "None",
                    'semantic_score': f"{r.e5:.2f}",
                    '_used_by_llm': False,
                })

        return generation.answer, ranked

    def hot_reload_scorer(self, checkpoint_path: str) -> None:
        """Atomically replace TComplEx scorer without stopping inference (GIL-safe)."""
        from src.kg_model.temporal.temporal_model import TemporalScorer
        from src.utils.device_utils import get_device
        import logging as _logging
        new_scorer = TemporalScorer(
            checkpoint_path=checkpoint_path,
            data_path=self.config.tcomplex_data_path,
            device=get_device(),
        )
        # CPython GIL guarantees object-reference assignment is atomic
        self.temporal_scorer = new_scorer
        self._scoring_stage.temporal_scorer = new_scorer
        _logging.getLogger(__name__).info(
            "TComplEx scorer hot-reloaded from %s", checkpoint_path
        )

    # 1.4: status() required by /status handler when in production mode
    def status(self) -> dict:
        from src.pipelines.ingestion.doc_ingestion_service import get_ingest_stats
        llm_name = type(self.llm_client).__name__ if self.llm_client else "None"
        nodes, quads = 0, 0
        try:
            counts = self.kg_model.count_items()
            graph_info = counts.get('graph_info', {})
            nodes = graph_info.get('nodes', 0)
            quads = graph_info.get('quadruplets', 0)
        except Exception:
            pass
        stats_file = get_ingest_stats()
        return {
            "mode": "production",
            "llm": llm_name,
            "ingested_facts": stats_file.get("total_facts", 0),
            "nodes": nodes,
            "quadruplets": quads,
            "tcomplex_loaded": self.temporal_scorer is not None,
            "facts_since_last_retrain": stats_file.get("facts_since_last_retrain", 0),
        }

