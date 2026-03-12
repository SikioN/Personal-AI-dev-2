import os
from dataclasses import dataclass, field
from typing import Dict, Tuple

# System prompt for anonymized Q-ID answer generation
_ANON_SYS_DEFAULT = (
    "You are a pure logical reasoning engine. "
    "FACT STRUCTURE: 'Subject_ID --[Relation_ID]--> Object_ID (Time: Range)'. "
    "Identify the ID that represents the specific value asked for by the question. "
    "Output ONLY the single ID (e.g. Q123 or P123). If the answer is not in the facts: output NULL."
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
    min_tl_count: int = 1  # 2.5: enable TComplEx even when only 1 quad has valid wikidata IDs
    confidence_gap: float = 0.20       # P3 gap-based selection threshold
    min_facts: int = 2
    max_facts: int = 7
    search_k_floor: int = 15
    search_k_exp: float = 0.55

    before_words: Tuple[str, ...] = (
        'before', 'prior to', 'earlier than', 'preceding', 'until', 'up to', 'by'
    )
    after_words: Tuple[str, ...] = (
        'after', 'since', 'following', 'post-', 'from', 'starting from', 'beyond'
    )

    # Neo4j connection (external DB — no in-memory graph)
    neo4j_host: str = 'localhost'
    neo4j_port: int = 7687
    neo4j_user: str = 'neo4j'
    neo4j_password: str = 'password'
    neo4j_db: str = 'neo4j'

    # ChromaDB (external vector store)
    chroma_nodes_path: str = 'data/graph_structures/vectorized_nodes/default_densedb'
    chroma_quads_path: str = 'data/graph_structures/vectorized_quadruplets/default_densedb'

    # Model paths
    finetuned_model_path: str = 'models/wikidata_finetuned_remote/wikidata_finetuned'
    tcomplex_checkpoint: str = 'models/cronkgqa/tcomplex.ckpt'
    tcomplex_data_path: str = 'wikidata_big/kg/tkbc_processed_data/wikidata_big/'

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
        return cfg
