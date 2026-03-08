"""
engine_loader.py — unified loader for QA engine.

Mode is controlled by env variable:
  USE_INMEMORY=true   → SimpleInMemoryEngine (default for testing)
  USE_INMEMORY=false  → Full KnowledgeGraphModel with Neo4j + ChromaDB (production)
"""
import os
import logging
import re
import threading
from typing import List, Tuple, Dict, Optional

logger = logging.getLogger(__name__)

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_PATH = os.environ.get(
    'MODEL_PATH',
    os.path.join(ROOT_DIR, 'models/wikidata_finetuned_remote/wikidata_finetuned')
)

_engine = None
_navigator = None
_kg_model = None
_engine_lock = threading.Lock()  # 5.2: thread-safe singleton initialisation


# ===========================================================================
# SECTION 1: Simple In-Memory Engine
# Loads quadruplets from full.txt, embeds with E5, retrieves by cosine sim.
# No external services required — for testing/demo.
# ===========================================================================

def _load_id2label(path: str) -> Dict[str, str]:
    mapping = {}
    if not os.path.exists(path):
        logger.warning(f"Label file not found: {path}")
        return mapping
    try:
        with open(path, encoding='utf-8') as f:
            for line in f:
                parts = line.rstrip('\n').split('\t', 1)
                if len(parts) == 2:
                    mapping[parts[0]] = parts[1]
    except Exception as e:
        logger.warning(f"Could not load {path}: {e}")
    return mapping


def _load_quadruplets(full_txt_path: str) -> List[Tuple[str, str, str, str]]:
    quads = []
    if not os.path.exists(full_txt_path):
        logger.warning(f"full.txt not found: {full_txt_path}")
        return quads
    try:
        with open(full_txt_path, encoding='utf-8') as f:
            for line in f:
                parts = line.rstrip('\n').split('\t')
                if len(parts) < 3:
                    parts = line.rstrip('\n').split()
                if len(parts) >= 5:
                    s, r, o, ts, te = parts[0], parts[1], parts[2], parts[3], parts[4]
                    time_str = f"{ts}-{te}" if ts != te else ts
                elif len(parts) == 4:
                    s, r, o, time_str = parts
                elif len(parts) == 3:
                    s, r, o = parts
                    time_str = "Always"
                else:
                    continue
                quads.append((s, r, o, time_str))
    except Exception as e:
        logger.error(f"Could not load full.txt: {e}")
    return quads


class SimpleInMemoryEngine:
    """
    Minimal QA engine for testing/demo.
    Compatible interface: .ask(), .get_ranked_results(), .get_neighborhood(), .status()
    """

    def __init__(self, kg_data_path: str, llm_client, model_path: str):
        self.llm = llm_client
        self.quad_texts: List[str] = []
        self.raw_quads: List[Tuple] = []
        self.embeddings = None
        self._embedder = None
        self._load_data(kg_data_path)
        self._build_embeddings(model_path)

    def _load_data(self, kg_data_path: str):
        full_txt = os.path.join(kg_data_path, 'full.txt')
        ent_file = os.path.join(kg_data_path, 'wd_id2entity_text.txt')
        rel_file = os.path.join(kg_data_path, 'wd_id2relation_text.txt')
        self.id2label = _load_id2label(ent_file)
        self.id2label.update(_load_id2label(rel_file))

        logger.info(f"Loading quadruplets from {full_txt} ...")
        self.raw_quads = _load_quadruplets(full_txt)
        logger.info(f"Loaded {len(self.raw_quads)} quadruplets")
        if len(self.raw_quads) > 1_000_000:
            logger.warning(
                "SimpleInMemoryEngine loaded %d quadruplets — high OOM risk. "
                "Consider switching to production mode (USE_INMEMORY=false).",
                len(self.raw_quads),
            )

        def label(qid: str) -> str:
            return self.id2label.get(qid, qid)

        self.quad_texts = [
            f"{label(s)} -- {label(r)} --> {label(o)} (time: {t})"
            for s, r, o, t in self.raw_quads
        ]

    def _build_embeddings(self, model_path: str):
        try:
            from sentence_transformers import SentenceTransformer
            model_name = model_path if os.path.exists(model_path) else 'intfloat/multilingual-e5-small'
            logger.info(f"Loading embedder: {model_name} ...")
            self._embedder = SentenceTransformer(model_name)
            passages = ["passage: " + t for t in self.quad_texts]
            logger.info("Encoding quadruplets (this may take a while)...")
            self.embeddings = self._embedder.encode(
                passages, batch_size=256, show_progress_bar=True, normalize_embeddings=True,
            )
            logger.info(f"Embeddings ready: shape={self.embeddings.shape}")
        except Exception as e:
            logger.warning(f"Could not build embeddings: {e}. Falling back to keyword search.")

    def retrieve(self, question: str, top_k: int = 10) -> List[str]:
        if self.embeddings is not None:
            import numpy as np
            q_emb = self._embedder.encode(["query: " + question], normalize_embeddings=True)
            scores = (q_emb @ self.embeddings.T)[0]
            top_idx = scores.argsort()[::-1][:top_k]
            return [self.quad_texts[i] for i in top_idx]
        # Keyword fallback
        words = set(re.findall(r'\w+', question.lower()))
        scored = sorted(self.quad_texts, key=lambda t: sum(1 for w in words if w in t.lower()), reverse=True)
        return scored[:top_k]

    def ask(self, question: str) -> str:
        if not self.llm:
            return "LLM не инициализирован."
        facts = self.retrieve(question, top_k=8)
        if not facts:
            return "Релевантные факты не найдены в базе знаний."
        facts_str = "\n".join(f"- {f}" for f in facts)
        prompt = (
            f"You are a knowledge graph QA assistant. "
            f"Answer the question using ONLY the facts below.\n\n"
            f"FACTS:\n{facts_str}\n\nQUESTION: {question}\n\nANSWER:"
        )
        try:
            return self.llm.generate(prompt)
        except Exception as e:
            logger.error(f"LLM error: {e}")
            return f"Ошибка LLM: {e}"

    # 2.1: unified return type List[Dict] — compatible with QAEngine.get_ranked_results()
    def get_ranked_results(self, question: str, top_k: int = 10) -> List[Dict]:
        texts = self.retrieve(question, top_k)
        return [{"quadruplet": t, "confidence": 0.0, "text": t} for t in texts]

    def get_neighborhood(self, entity_name: str, limit: int = 20) -> List[str]:
        name_lower = entity_name.lower()
        return [t for t in self.quad_texts if name_lower in t.lower()][:limit]

    def status(self) -> Dict:
        return {
            "mode": "in-memory",
            "quadruplets": len(self.raw_quads),
            "embeddings_ready": self.embeddings is not None,
            "llm": type(self.llm).__name__ if self.llm else "None",
        }


# ===========================================================================
# SECTION 2: Full Production Engine (Neo4j + ChromaDB)
# Uses KnowledgeGraphModel infrastructure.
# Set USE_INMEMORY=false to activate.
# ===========================================================================

def _load_production_engine(config):
    """Full production engine: Neo4j + ChromaDB via KnowledgeGraphModel."""
    from src.db_drivers.vector_driver.embedders import EmbedderModelConfig
    from src.kg_model.embeddings_model import EmbeddingsModelConfig
    from src.db_drivers.vector_driver import VectorDriverConfig, VectorDBConnectionConfig
    from src.kg_model.graph_model import GraphModelConfig
    from src.db_drivers.graph_driver import GraphDriverConfig
    from src.kg_model.knowledge_graph_model import KnowledgeGraphModel, KnowledgeGraphModelConfig
    from src.pipelines.qa.qa_engine import QAEngine
    from src.utils.kg_navigator import KGNavigator

    # ChromaDB
    nodes_path = os.environ.get('CHROMA_NODES_PATH',
        os.path.join(ROOT_DIR, 'data/graph_structures/vectorized_nodes/wikidata_test'))
    quads_path = os.environ.get('CHROMA_QUADS_PATH',
        os.path.join(ROOT_DIR, 'data/graph_structures/vectorized_triplets/wikidata_test'))
    os.makedirs(nodes_path, exist_ok=True)
    os.makedirs(quads_path, exist_ok=True)

    nodes_cfg = VectorDriverConfig(
        db_vendor='chroma', db_config=VectorDBConnectionConfig(
            conn={'path': nodes_path},
            db_info={'db': 'default_db', 'table': 'personalaitable'}))
    quads_cfg = VectorDriverConfig(
        db_vendor='chroma', db_config=VectorDBConnectionConfig(
            conn={'path': quads_path},
            db_info={'db': 'default_db', 'table': 'personalaitable'}))

    # Graph backend
    try:
        graph_driver_cfg = GraphDriverConfig(
            db_vendor='neo4j',
            db_config={
                'host': config.neo4j_host, 'port': config.neo4j_port,
                'user': config.neo4j_user, 'pwd': config.neo4j_password,
                'db': config.neo4j_db,
            }
        )
        logger.info("Connected to Neo4j")
    except Exception as e:
        logger.warning(f"Neo4j unavailable ({type(e).__name__}), falling back to in-memory graph.")
        graph_driver_cfg = GraphDriverConfig(db_vendor='inmemory_graph')

    embedder_cfg = EmbedderModelConfig(model_name_or_path='intfloat/multilingual-e5-small')
    emb_cfg = EmbeddingsModelConfig(
        nodesdb_driver_config=nodes_cfg,
        quadrupletsdb_driver_config=quads_cfg,
        embedder_config=embedder_cfg,
    )
    kg_model_cfg = KnowledgeGraphModelConfig(
        embeddings_config=emb_cfg,
        graph_config=GraphModelConfig(driver_config=graph_driver_cfg),
    )
    kg_model = KnowledgeGraphModel(kg_model_cfg)
    engine = QAEngine(kg_model, MODEL_PATH, config=config)
    navigator = KGNavigator(kg_model)
    return engine, navigator, kg_model


# ===========================================================================
# SECTION 3: Unified entry point
# ===========================================================================

def _make_llm_client():
    """Instantiate LLM client based on LLM_BACKEND env var."""
    backend = os.environ.get("LLM_BACKEND", "deepseek").lower()
    try:
        if backend == "deepseek":
            from src.llm.deepseek_client import DeepSeekClient
            return DeepSeekClient(api_key=os.environ.get("DEEPSEEK_API_KEY", ""))
        elif backend == "yandexgpt":
            from src.llm.yandex_gpt_client import YandexGPTClient
            return YandexGPTClient(
                api_key=os.environ.get("YANDEX_API_KEY", ""),
                folder_id=os.environ.get("YANDEX_FOLDER_ID", ""),
                model_name=os.environ.get("YANDEX_MODEL", "yandexgpt"),
            )
        elif backend == "gigachat":
            from src.llm.gigachat_client import GigaChatClient
            return GigaChatClient(credentials=os.environ.get("GIGACHAT_CREDENTIALS", ""))
        elif backend in ("openai", "chatgpt"):
            from src.llm.openai_client import OpenAIClient
            return OpenAIClient(
                api_key=os.environ.get("OPENAI_API_KEY", ""),
                model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
                base_url=os.environ.get("OPENAI_BASE_URL") or None,
            )
        elif backend == "qwen":
            from src.llm.qwen_client import QwenClient
            return QwenClient(
                api_key=os.environ.get("QWEN_API_KEY", ""),
                model=os.environ.get("QWEN_MODEL", "qwen-plus"),
            )
        else:
            from src.llm.ollama_client import OllamaClient
            return OllamaClient(model=os.environ.get("OLLAMA_MODEL", "llama3.2"))
    except Exception as e:
        # 5.3: mask sensitive data — only log exception type and first 100 chars
        logger.warning(f"LLM client init error: {type(e).__name__}: {str(e)[:100]}")
        return None


def load_engine():
    """
    Initialize engine (singleton). Returns (engine, navigator, kg_model).
    Thread-safe via double-checked locking (5.2).
    - navigator and kg_model are None in in-memory mode.
    - Controlled by USE_INMEMORY env var (default: 'true').
    - Falls back to in-memory if production engine fails (3.5).
    """
    global _engine, _navigator, _kg_model

    # Fast path — already initialised
    if _engine is not None:
        return _engine, _navigator, _kg_model

    with _engine_lock:
        # Double-checked locking
        if _engine is not None:
            return _engine, _navigator, _kg_model

        use_inmemory = os.environ.get("USE_INMEMORY", "true").lower() in ("1", "true", "yes")

        if use_inmemory:
            # --- IN-MEMORY MODE ---
            kg_data_path = os.environ.get('KG_DATA_PATH', os.path.join(ROOT_DIR, 'wikidata_big/kg'))
            llm_client = _make_llm_client()
            logger.info(f"Starting SimpleInMemoryEngine (KG data: {kg_data_path})")
            _engine = SimpleInMemoryEngine(kg_data_path, llm_client, MODEL_PATH)
            _navigator = None
            _kg_model = None
        else:
            # --- PRODUCTION MODE (Neo4j + ChromaDB) ---
            from src.config.qa_config import QAConfig
            config = QAConfig.from_env()
            try:
                _engine, _navigator, _kg_model = _load_production_engine(config)
                logger.info("Production engine initialized successfully.")
            except Exception as e:
                # 3.5: graceful fallback to in-memory on production engine failure
                logger.error(
                    f"Production engine failed ({type(e).__name__}: {str(e)[:200]}), "
                    "falling back to in-memory mode."
                )
                kg_data_path = os.environ.get('KG_DATA_PATH', os.path.join(ROOT_DIR, 'wikidata_big/kg'))
                llm_client = _make_llm_client()
                _engine = SimpleInMemoryEngine(kg_data_path, llm_client, MODEL_PATH)
                _navigator = None
                _kg_model = None

    return _engine, _navigator, _kg_model
