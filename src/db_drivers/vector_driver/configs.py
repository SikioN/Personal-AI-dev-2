from .connectors import ChromaConnection, DEFAULT_CHROMA_CONFIG
from .connectors import MilvusConnector, DEFAULT_MILVUS_CONFIG


DEFAULT_VECTORDB_CONFIGS = {
    'chroma': DEFAULT_CHROMA_CONFIG,
    'milvus': DEFAULT_MILVUS_CONFIG
}

AVAILABLE_VECTORDB_CONNECTORS = {
    'chroma': ChromaConnection,
    'milvus': MilvusConnector
}
