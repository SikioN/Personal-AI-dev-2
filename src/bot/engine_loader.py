"""Load QAEngine and KGNavigator — shared between bot and other entry points."""
import os
import logging

logger = logging.getLogger(__name__)

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_PATH = os.path.join(ROOT_DIR, 'models/wikidata_finetuned_remote/wikidata_finetuned')

_engine = None
_navigator = None
_kg_model = None


def load_engine():
    """Initialize QAEngine + KGNavigator (singleton). Returns (engine, navigator, kg_model)."""
    global _engine, _navigator, _kg_model
    if _engine is not None:
        return _engine, _navigator, _kg_model

    from src.db_drivers.vector_driver.embedders import EmbedderModelConfig
    from src.kg_model.embeddings_model import EmbeddingsModelConfig
    from src.db_drivers.vector_driver import VectorDriverConfig, VectorDBConnectionConfig
    from src.kg_model.graph_model import GraphModelConfig
    from src.db_drivers.graph_driver import GraphDriverConfig
    from src.kg_model.knowledge_graph_model import KnowledgeGraphModel, KnowledgeGraphModelConfig
    from src.pipelines.qa.qa_engine import QAEngine
    from src.utils.kg_navigator import KGNavigator
    from src.config.qa_config import QAConfig

    config = QAConfig.from_env()

    # ChromaDB paths
    nodes_path = os.path.join(ROOT_DIR, config.chroma_nodes_path)
    if not os.path.exists(nodes_path):
        nodes_path = os.path.join(ROOT_DIR, "data/graph_structures/vectorized_nodes/wikidata_test")

    quads_path = os.path.join(ROOT_DIR, config.chroma_quads_path)
    if not os.path.exists(quads_path):
        quads_path = os.path.join(ROOT_DIR, "data/graph_structures/vectorized_triplets/wikidata_test")

    nodes_cfg = VectorDriverConfig(
        db_vendor='chroma', db_config=VectorDBConnectionConfig(
            conn={'path': nodes_path},
            db_info={'db': 'default_db', 'table': "personalaitable"}))

    quads_cfg = VectorDriverConfig(
        db_vendor='chroma', db_config=VectorDBConnectionConfig(
            conn={'path': quads_path},
            db_info={'db': 'default_db', 'table': "personalaitable"}))

    # Graph backend: Neo4j if available, else in-memory fallback
    neo4j_available = False
    try:
        graph_driver_cfg = GraphDriverConfig(
            db_vendor='neo4j',
            db_config={
                'host': config.neo4j_host,
                'port': config.neo4j_port,
                'user': config.neo4j_user,
                'pwd': config.neo4j_password,
                'db': config.neo4j_db,
            }
        )
        neo4j_available = True
        logger.info("Connected to Neo4j")
    except Exception as e:
        logger.warning(f"Neo4j unavailable ({e}), falling back to in-memory graph.")
        graph_driver_cfg = GraphDriverConfig(db_vendor='inmemory_graph')

    graph_cfg = GraphModelConfig(driver_config=graph_driver_cfg)

    embedder_cfg = EmbedderModelConfig(model_name_or_path='intfloat/multilingual-e5-small')
    emb_cfg = EmbeddingsModelConfig(
        nodesdb_driver_config=nodes_cfg,
        tripletsdb_driver_config=quads_cfg,
        embedder_config=embedder_cfg,
    )

    kg_model_cfg = KnowledgeGraphModelConfig(
        embeddings_config=emb_cfg,
        graph_config=graph_cfg,
    )

    kg_model = KnowledgeGraphModel(kg_model_cfg)

    if not neo4j_available:
        logger.info("Hydrating in-memory graph from files...")
        try:
            from src.utils.wikidata_utils import WikidataMapper
            from src.utils.graph_loader import hydrate_in_memory_graph
            kg_data_path = os.path.join(ROOT_DIR, "wikidata_big/kg")
            mapper = WikidataMapper(kg_data_path)
            hydrate_in_memory_graph(kg_model, mapper, kg_data_path)
            logger.info("Graph hydrated (in-memory mode)")
        except Exception as e:
            logger.warning(f"Could not hydrate in-memory graph: {e}")

    # Create LLM client
    llm_backend = os.environ.get("LLM_BACKEND", "ollama").lower()
    llm_client = None
    try:
        if llm_backend == "yandexgpt":
            from src.llm.yandex_gpt_client import YandexGPTClient
            llm_client = YandexGPTClient(
                api_key=os.environ.get("YANDEX_API_KEY", ""),
                folder_id=os.environ.get("YANDEX_FOLDER_ID", ""),
                model_name=os.environ.get("YANDEX_MODEL", "yandexgpt"),
            )
        elif llm_backend == "deepseek":
            from src.llm.deepseek_client import DeepSeekClient
            llm_client = DeepSeekClient(api_key=os.environ.get("DEEPSEEK_API_KEY", ""))
        elif llm_backend == "gigachat":
            from src.llm.gigachat_client import GigaChatClient
            llm_client = GigaChatClient(
                credentials=os.environ.get("GIGACHAT_CREDENTIALS", ""),
                model=os.environ.get("GIGACHAT_MODEL", "GigaChat"),
            )
        elif llm_backend in ("openai", "chatgpt"):
            from src.llm.openai_client import OpenAIClient
            llm_client = OpenAIClient(
                api_key=os.environ.get("OPENAI_API_KEY", ""),
                model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
                base_url=os.environ.get("OPENAI_BASE_URL") or None,
            )
        elif llm_backend == "qwen":
            from src.llm.qwen_client import QwenClient
            llm_client = QwenClient(
                api_key=os.environ.get("QWEN_API_KEY", ""),
                model=os.environ.get("QWEN_MODEL", "qwen-plus"),
            )
        else:
            from src.llm.ollama_client import OllamaClient
            llm_client = OllamaClient(
                model=os.environ.get("OLLAMA_MODEL", "llama3.2"),
            )
    except Exception as e:
        logger.warning(f"LLM client init error: {e}")

    engine = QAEngine(kg_model, MODEL_PATH, config=config, llm_client=llm_client)
    navigator = KGNavigator(kg_model)

    _engine = engine
    _navigator = navigator
    _kg_model = kg_model

    return engine, navigator, kg_model
