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
MODEL_PATH = (
    os.environ.get('FINETUNED_MODEL_PATH')
    or os.environ.get('MODEL_PATH')
    or os.path.join(ROOT_DIR, 'models/wikidata_finetuned_remote/wikidata_finetuned')
)

_engine = None
_navigator = None
_kg_model = None
_engine_lock = threading.Lock()  # 5.2: thread-safe singleton initialisation


def _resolve_kg_data_path() -> str:
    return os.environ.get('KG_DATA_PATH', os.path.join(ROOT_DIR, 'wikidata_big/kg'))


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
        from src.config.qa_config import QAConfig
        self.config = QAConfig.from_env()
        self.llm = llm_client
        self.quad_texts: List[str] = []
        self.raw_quads: List[Tuple] = []
        self.embeddings = None
        self._embedder = None
        self.temporal_scorer = None
        
        # Load temporal scorer if possible
        try:
            from src.kg_model.temporal.temporal_model import TemporalScorer
            from src.utils.device_utils import get_device
            self.temporal_scorer = TemporalScorer(
                checkpoint_path=self.config.tcomplex_checkpoint,
                data_path=self.config.tcomplex_data_path,
                device=get_device(),
            )
            logger.info("TComplEx loaded for SimpleInMemoryEngine.")
        except Exception as e:
            logger.warning(f"Could not initialize TemporalScorer for SimpleInMemoryEngine: {e}")

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

    def retrieve_with_scores(self, question: str, top_k: int = 10) -> List[Dict]:
        """Return list of dicts with keys: 'idx', 'text', 'conf', 'e5', 'tp', 'tl'."""
        entity_tokens = re.findall(r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+', question)
        candidate_indices = list(range(len(self.quad_texts)))
        if entity_tokens:
            matched = [
                i for i, t in enumerate(self.quad_texts)
                if any(ent.lower() in t.lower() for ent in entity_tokens)
            ]
            if matched:
                candidate_indices = matched

        scored_candidates = []

        if self.embeddings is not None:
            import numpy as np
            q_emb = self._embedder.encode(["query: " + question], normalize_embeddings=True)
            subset = self.embeddings[candidate_indices]
            semantic_scores = (q_emb @ subset.T)[0]
            
            # Simple temporal extraction for TComplEx
            resolved_time = None
            date_matches = re.findall(r'(\d{4})', question)
            if date_matches:
                resolved_time = int(date_matches[0])

            alpha = getattr(self.config, 'tcomplex_alpha', 0.5)
            
            for i, local_idx in enumerate(candidate_indices):
                e5 = float(semantic_scores[i])
                tp = 0.0
                tl = float('-inf')
                
                # Apply TComplEx if available
                if self.temporal_scorer and resolved_time:
                    s, r, o, _ = self.raw_quads[local_idx]
                    if s.startswith('Q') and r.startswith('P') and o.startswith('Q'):
                        try:
                            tl = float(self.temporal_scorer.score(s, r, o, str(resolved_time)))
                            tp = 1.0 / (1.0 + np.exp(-tl))
                            conf = (1.0 - alpha) * e5 + alpha * tp
                        except Exception:
                            conf = e5
                    else:
                        conf = e5
                else:
                    conf = e5
                
                scored_candidates.append({
                    'idx': local_idx,
                    'text': self.quad_texts[local_idx],
                    'conf': conf,
                    'e5': e5,
                    'tp': tp,
                    'tl': tl
                })
            
            scored_candidates.sort(key=lambda x: x['conf'], reverse=True)
            return scored_candidates[:top_k]

        # Keyword fallback
        words = set(re.findall(r'\w+', question.lower()))
        scored = sorted(
            candidate_indices,
            key=lambda i: sum(1 for w in words if w in self.quad_texts[i].lower()),
            reverse=True,
        )
        return [{
            'idx': i,
            'text': self.quad_texts[i],
            'conf': 0.0,
            'e5': 0.0,
            'tp': 0.0,
            'tl': float('-inf')
        } for i in scored[:top_k]]

    def retrieve(self, question: str, top_k: int = 10) -> List[str]:
        return [res['text'] for res in self.retrieve_with_scores(question, top_k)]

    def ask(self, question: str, top_k: int = 8, debug: bool = False) -> str:
        if not self.llm:
            return "LLM не инициализирован."
        SEP = '=' * 60
        if debug:
            print(f'\n{SEP}\n[SimpleInMemoryEngine] QUESTION: {question}\n{SEP}')
        
        results = self.retrieve_with_scores(question, top_k=top_k)
        if debug:
            print(f'[1/2] Top-{len(results)} facts by hybrid scoring (E5 + TComplEx):')
            for res in results:
                print(f"  [{res['conf']:.3f}] (e5={res['e5']:.3f}, tp={res['tp']:.3f}) {res['text']}")

        if not results:
            return "Релевантные факты не найдены в базе знаний."
        facts_str = "\n".join(f"- {res['text']}" for res in results)
        prompt = (
            "You are a knowledge graph QA assistant. "
            "Answer the question using ONLY the facts below.\n\n"
            f"FACTS:\n{facts_str}\n\nQUESTION: {question}\n\nANSWER:"
        )
        if debug:
            print(f'[2/2] Calling LLM ({type(self.llm).__name__})...')
        try:
            answer = self.llm.generate(prompt)
            if debug:
                print(f'\n{SEP}\n>>> ANSWER: {answer}\n{SEP}\n')
            return answer
        except Exception as e:
            logger.error(f"LLM error: {e}")
            return f"Ошибка LLM: {e}"

    def get_ranked_results(self, question: str, top_k: int = 10) -> List[Dict]:
        from src.utils.data_structs import NodeCreator, RelationCreator, QuadrupletCreator
        results = self.retrieve_with_scores(question, top_k)
        output = []
        for res in results:
            s, r, o, t = self.raw_quads[res['idx']]
            s_node = NodeCreator.create('object', self.id2label.get(s, s))
            s_node.id = s
            o_node = NodeCreator.create('object', self.id2label.get(o, o))
            o_node.id = o
            r_rel = RelationCreator.create('simple', self.id2label.get(r, r))
            t_node = NodeCreator.create('time', t if t else 'Always')
            quad = QuadrupletCreator.create(s_node, r_rel, o_node, t_node)
            output.append({
                'quadruplet': quad,
                'text': res['text'],
                'confidence': res['conf'],
                'e5': res['e5'],
                'tp': res['tp'],
                'tl': res['tl']
            })
        return output

    def ask_full(self, question: str, top_k: int = 10, debug: bool = False):
        """Single-pass: returns (answer, ranked_results) to avoid double pipeline execution."""
        ranked = self.get_ranked_results(question, top_k)
        answer = self.ask(question, top_k, debug)
        return answer, ranked

    def get_neighborhood(self, entity_name: str, limit: int = 20) -> List[str]:
        name_lower = entity_name.lower()
        return [t for t in self.quad_texts if name_lower in t.lower()][:limit]

    def status(self) -> Dict:
        from src.pipelines.ingestion.doc_ingestion_service import get_ingest_stats
        unique_nodes = len(
            set(s for s, _, _, _ in self.raw_quads) |
            set(o for _, _, o, _ in self.raw_quads)
        )
        stats_file = get_ingest_stats()
        return {
            "mode": "in-memory",
            "nodes": unique_nodes,
            "quadruplets": len(self.raw_quads),
            "embeddings_ready": self.embeddings is not None,
            "tcomplex_loaded": self.temporal_scorer is not None,
            "llm": type(self.llm).__name__ if self.llm else "None",
            "facts_since_last_retrain": stats_file.get("facts_since_last_retrain", 0),
        }


class SimpleNavigator:
    """Drop-in replacement for KGNavigator when using SimpleInMemoryEngine."""

    def __init__(self, engine: SimpleInMemoryEngine):
        self._engine = engine

    def get_neighborhood(self, node_ids: List[str], depth: int = 1) -> List:
        """Return Quadruplet objects for all quads touching any of the given node IDs."""
        from src.utils.data_structs import NodeCreator, RelationCreator, QuadrupletCreator
        id_set = set(node_ids)
        output = []
        seen: set = set()
        for s, r, o, t in self._engine.raw_quads:
            if s in id_set or o in id_set:
                key = (s, r, o, t)
                if key in seen:
                    continue
                seen.add(key)
                lbl = self._engine.id2label
                s_node = NodeCreator.create('object', lbl.get(s, s))
                s_node.id = s
                o_node = NodeCreator.create('object', lbl.get(o, o))
                o_node.id = o
                r_rel = RelationCreator.create('simple', lbl.get(r, r))
                t_node = NodeCreator.create('time', t if t else 'Always')
                output.append(QuadrupletCreator.create(s_node, r_rel, o_node, t_node))
        return output


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

    # ChromaDB — use config fields (which already read CHROMA_NODES_PATH / CHROMA_QUADS_PATH env vars)
    nodes_path = (
        config.chroma_nodes_path
        if os.path.isabs(config.chroma_nodes_path)
        else os.path.join(ROOT_DIR, config.chroma_nodes_path)
    )
    quads_path = (
        config.chroma_quads_path
        if os.path.isabs(config.chroma_quads_path)
        else os.path.join(ROOT_DIR, config.chroma_quads_path)
    )
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

    # Graph backend — controlled by GRAPH_BACKEND env var
    graph_backend = os.environ.get('GRAPH_BACKEND', 'kuzu').lower()
    if graph_backend == 'kuzu':
        from src.db_drivers.graph_driver.connectors.KuzuConnector import DEFAULT_KUZU_CONFIG
        from src.db_drivers.graph_driver.utils import GraphDBConnectionConfig
        kuzu_path = (
            config.kuzu_path
            if os.path.isabs(config.kuzu_path)
            else os.path.join(ROOT_DIR, config.kuzu_path)
        )
        # NOTE: KuzuDB >=0.6 expects a FILE path — do NOT makedirs the kuzu path itself
        os.makedirs(os.path.dirname(kuzu_path), exist_ok=True)
        kuzu_cfg = GraphDBConnectionConfig(
            params=dict(DEFAULT_KUZU_CONFIG.params, path=kuzu_path)
        )
        graph_driver_cfg = GraphDriverConfig(db_vendor='kuzu', db_config=kuzu_cfg)
        logger.info("Using KuzuDB at %s", kuzu_path)
    elif graph_backend == 'inmemory_graph':
        graph_driver_cfg = GraphDriverConfig(db_vendor='inmemory_graph')
        logger.info("Using in-memory graph backend.")
    else:  # neo4j (default)
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

    embedder_cfg = EmbedderModelConfig(
        model_name_or_path=MODEL_PATH if os.path.exists(MODEL_PATH) else 'intfloat/multilingual-e5-small'
    )
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

def _load_inmemory_stash(engine: "SimpleInMemoryEngine") -> None:
    """Load previously ingested facts from stash file into in-memory engine."""
    import json
    try:
        from src.pipelines.ingestion.doc_ingestion_service import STASH_PATH
    except ImportError:
        return
    if not os.path.exists(STASH_PATH):
        return
    try:
        with open(STASH_PATH, encoding="utf-8") as f:
            stash = json.load(f)
    except Exception as e:
        logger.warning("Could not load inmemory stash: %s", e)
        return
    if not stash:
        return
    new_tuples = [
        (q["s"]["name"], q["r"]["name"], q["o"]["name"],
         q["t"]["prop"].get("start", "unknown"))
        for q in stash
    ]
    new_texts = [f"{s} -- {r} --> {o} (time: {t})" for s, r, o, t in new_tuples]
    engine.raw_quads.extend(new_tuples)
    engine.quad_texts.extend(new_texts)
    if engine.embeddings is not None and engine._embedder is not None:
        import numpy as np
        new_embs = engine._embedder.encode(
            ["passage: " + t for t in new_texts],
            batch_size=64, normalize_embeddings=True,
        )
        if getattr(engine.embeddings, "size", 0) == 0 or getattr(engine.embeddings, "ndim", 1) == 1:
            engine.embeddings = new_embs
        else:
            engine.embeddings = np.vstack([engine.embeddings, new_embs])
    logger.info("Loaded %d facts from inmemory stash.", len(stash))


def _make_llm_client():
    """Instantiate LLM client based on LLM_BACKEND env var."""
    backend = os.environ.get("LLM_BACKEND", "deepseek").lower()
    try:
        if backend == "deepseek":
            from src.llm.deepseek_client import DeepSeekClient
            return DeepSeekClient(
                api_key=os.environ.get("DEEPSEEK_API_KEY", ""),
                model=os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
            )
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


def _index_quads_to_inmemory_graph(engine, kg_data_path: str) -> None:
    """
    Populate InMemoryGraphConnector from full.txt (no embedding computation).
    ~10s for 328k quads. Idempotent: skips if already populated.
    Node IDs are set to Wikidata QIDs so that strid_nodes_index lookups work.
    """
    import json as _json
    db_conn = engine.kg_model.graph_struct.db_conn
    if db_conn.count_items().get('quadruplets', 0) > 0:
        logger.info("InMemoryGraph already populated, skipping.")
        return

    full_txt = os.path.join(kg_data_path, 'full.txt')
    ent_file = os.path.join(kg_data_path, 'wd_id2entity_text.txt')
    rel_file = os.path.join(kg_data_path, 'wd_id2relation_text.txt')

    raw_quads = _load_quadruplets(full_txt)
    if not raw_quads:
        logger.warning("full.txt empty or missing — InMemoryGraph will be empty.")
        return
    id2label = _load_id2label(ent_file)
    id2label.update(_load_id2label(rel_file))

    from src.utils.data_structs import NodeCreator, RelationCreator, QuadrupletCreator, NodeType

    BATCH = 500
    logger.info(f"Loading {len(raw_quads)} quadruplets into InMemoryGraph...")

    for start in range(0, len(raw_quads), BATCH):
        batch = raw_quads[start:start + BATCH]
        quad_objs = []
        seen_ids: set = set()

        for s, r, o, t in batch:
            s_node = NodeCreator.create('object', id2label.get(s, s))
            s_node.id = s
            o_node = NodeCreator.create('object', id2label.get(o, o))
            o_node.id = o
            r_rel = RelationCreator.create('simple', id2label.get(r, r))
            t_node = NodeCreator.create('time', t if t else 'Always')

            q = QuadrupletCreator.create(s_node, r_rel, o_node, t_node)

            # Store Wikidata IDs for TComplEx scoring
            q.start_node.prop['wd_id'] = s
            q.relation.prop['wd_id'] = r
            q.end_node.prop['wd_id'] = o

            if q.id not in seen_ids:
                seen_ids.add(q.id)
                quad_objs.append(q)

        if quad_objs:
            db_conn.create(quad_objs)
        if start % (BATCH * 20) == 0 and start > 0:
            logger.info(f"  {start}/{len(raw_quads)} loaded")

    logger.info(f"InMemoryGraph ready: {db_conn.count_items()}")


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
        use_inmemory = os.environ.get("USE_INMEMORY", "false").lower() in ("1", "true", "yes")
        if use_inmemory:
            # --- IN-MEMORY MODE: full QAEngine with InMemoryGraphConnector ---
            # Force in-memory graph; point ChromaDB to empty /tmp (no global ANN indexing)
            os.environ.setdefault('GRAPH_BACKEND', 'inmemory_graph')
            os.environ.setdefault('CHROMA_NODES_PATH', '/tmp/personalai_chroma/nodes')
            os.environ.setdefault('CHROMA_QUADS_PATH', '/tmp/personalai_chroma/quads')
            from src.config.qa_config import QAConfig
            config = QAConfig.from_env()
            kg_data_path = _resolve_kg_data_path()
            try:
                _engine, _navigator, _kg_model = _load_production_engine(config)
                _index_quads_to_inmemory_graph(_engine, kg_data_path)
                logger.info("In-memory mode: full QAEngine with InMemoryGraphConnector.")
            except Exception as e:
                logger.exception(
                    f"Full engine failed ({type(e).__name__}: {str(e)[:200]}), "
                    "falling back to SimpleInMemoryEngine."
                )
                llm_client = _make_llm_client()
                _engine = SimpleInMemoryEngine(kg_data_path, llm_client, MODEL_PATH)
                _navigator = SimpleNavigator(_engine)
                _kg_model = None
                _load_inmemory_stash(_engine)
        else:
            # --- PRODUCTION MODE (Neo4j + ChromaDB) ---
            from src.config.qa_config import QAConfig
            config = QAConfig.from_env()
            try:
                _engine, _navigator, _kg_model = _load_production_engine(config)
                logger.info("Production engine initialized successfully.")
            except Exception as e:
                # 3.5: graceful fallback to in-memory on production engine failure
                logger.exception(
                    f"Production engine failed ({type(e).__name__}: {str(e)[:200]}), "
                    "falling back to in-memory mode."
                )
                kg_data_path = _resolve_kg_data_path()
                llm_client = _make_llm_client()
                _engine = SimpleInMemoryEngine(kg_data_path, llm_client, MODEL_PATH)
                _navigator = SimpleNavigator(_engine)
                _kg_model = None
                _load_inmemory_stash(_engine)

    return _engine, _navigator, _kg_model
