import os
from dataclasses import dataclass, field
from typing import Dict, Tuple

# System prompt for answer generation from readable Russian facts
_ANON_SYS_DEFAULT = (
    "You are a knowledge base QA system. "
    "Answer ONLY based on the provided FACTS. "
    "Questions may be in Russian or English — answer in the same language as the question. "
    "FACT FORMAT: '- Subject → Relation → Object (Year: YYYY)'\n"
    "Rules:\n"
    "- Answer with a specific value, number, or short phrase from the chosen fact.\n"
    "- For year/date questions: output ONLY the year or range (e.g. '2024' or '2020 - 2024').\n"
    "- If multiple facts have different numbers — pick the one whose SUBJECT and RELATION best match the question topic.\n"
    "- Do NOT use external knowledge.\n"
    "- If the provided facts do not contain the answer: output NULL."
)


@dataclass
class QAConfig:
    # Scoring weights
    alpha_by_type: Dict[str, float] = field(default_factory=lambda: {
        'simple_time': 0.6,
        'before_after': 0.45,
        'time_join': 0.5,
        'first_last': 0.5,
    })
    alpha_default: float = 0.3
    tcomplex_threshold: float = -3.0   # P1 adaptive alpha gate
    min_tl_count: int = 2
    confidence_gap: float = 0.20       # P3 gap-based selection threshold
    min_facts: int = 2
    max_facts: int = 20
    search_k_floor: int = 15
    search_k_exp: float = 0.55
    tcomplex_alpha: float = 0.5

    before_words: Tuple[str, ...] = (
        'before', 'prior to', 'earlier than', 'preceding', 'until', 'up to', 'by',
        'до', 'раньше', 'ранее', 'перед', 'предшествующий', 'не позднее',
    )
    after_words: Tuple[str, ...] = (
        'after', 'since', 'following', 'post-', 'from', 'starting from', 'beyond',
        'после', 'с', 'начиная с', 'позже', 'позднее', 'следующий', 'с момента',
    )

    # Neo4j connection (external DB — no in-memory graph)
    neo4j_host: str = 'localhost'
    neo4j_port: int = 7687
    neo4j_user: str = 'neo4j'
    neo4j_password: str = ''
    neo4j_db: str = 'neo4j'

    # ChromaDB (external vector store)
    chroma_nodes_path: str = field(default_factory=lambda: os.environ.get(
        "CHROMA_NODES_PATH", "data/graph_structures/vectorized_nodes/default"))
    chroma_quads_path: str = field(default_factory=lambda: os.environ.get(
        "CHROMA_QUADS_PATH", "data/graph_structures/vectorized_quadruplets/default"))

    # KuzuDB (embedded graph store)
    kuzu_path: str = field(default_factory=lambda: os.environ.get("KUZU_PATH", "data/kuzu_db"))

    # Model paths
    finetuned_model_path: str = field(default_factory=lambda: os.environ.get(
        "FINETUNED_MODEL_PATH", "models/e5"))
    tcomplex_checkpoint: str = field(default_factory=lambda: os.environ.get(
        "TCOMPLEX_CHECKPOINT", "models/cronkgqa/tcomplex.ckpt"))
    tcomplex_data_path: str = field(default_factory=lambda: os.environ.get(
        "TCOMPLEX_DATA_PATH", "wikidata_big/kg/tkbc_processed_data/wikidata_big/"))

    # LLM generation system prompt
    anon_system_prompt: str = _ANON_SYS_DEFAULT

    @classmethod
    def from_env(cls) -> "QAConfig":
        """Override any field from environment variables."""
        cfg = cls()
        if os.environ.get('NEO4J_HOST'):
            cfg.neo4j_host = os.environ['NEO4J_HOST']
        if os.environ.get('NEO4J_PORT'):
            cfg.neo4j_port = int(os.environ['NEO4J_PORT'])
        if os.environ.get('NEO4J_USER'):
            cfg.neo4j_user = os.environ['NEO4J_USER']
        if os.environ.get('NEO4J_PASSWORD'):
            cfg.neo4j_password = os.environ['NEO4J_PASSWORD']
        if os.environ.get('NEO4J_DB'):
            cfg.neo4j_db = os.environ['NEO4J_DB']
        if os.environ.get('CHROMA_NODES_PATH'):
            cfg.chroma_nodes_path = os.environ['CHROMA_NODES_PATH']
        if os.environ.get('CHROMA_QUADS_PATH'):
            cfg.chroma_quads_path = os.environ['CHROMA_QUADS_PATH']
        if os.environ.get('QA_CONFIDENCE_GAP'):
            cfg.confidence_gap = float(os.environ['QA_CONFIDENCE_GAP'])
        if os.environ.get('QA_TCOMPLEX_THRESHOLD'):
            cfg.tcomplex_threshold = float(os.environ['QA_TCOMPLEX_THRESHOLD'])
        if os.environ.get('FINETUNED_MODEL_PATH'):
            cfg.finetuned_model_path = os.environ['FINETUNED_MODEL_PATH']
        if os.environ.get('KUZU_PATH'):
            cfg.kuzu_path = os.environ['KUZU_PATH']
        if os.environ.get('TCOMPLEX_CHECKPOINT'):
            cfg.tcomplex_checkpoint = os.environ['TCOMPLEX_CHECKPOINT']
        if os.environ.get('TCOMPLEX_DATA_PATH'):
            cfg.tcomplex_data_path = os.environ['TCOMPLEX_DATA_PATH']
        if os.environ.get('TCOMPLEX_ALPHA'):
            cfg.tcomplex_alpha = float(os.environ['TCOMPLEX_ALPHA'])
        if os.environ.get('QA_MAX_FACTS'):
            cfg.max_facts = int(os.environ['QA_MAX_FACTS'])
        if not cfg.neo4j_password:
            import warnings
            warnings.warn("NEO4J_PASSWORD is not set. Set it via environment variable.", stacklevel=2)
        return cfg
