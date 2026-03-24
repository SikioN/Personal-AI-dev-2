import os
import sys
import logging
from dotenv import load_dotenv

# Add project root to path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)

from src.config.qa_config import QAConfig
from src.kg_model.knowledge_graph_model import KnowledgeGraphModel, KnowledgeGraphModelConfig
from src.kg_model.graph_model import GraphModelConfig
from src.kg_model.embeddings_model import EmbeddingsModelConfig
from src.db_drivers.graph_driver import GraphDriverConfig
from src.db_drivers.graph_driver.connectors.KuzuConnector import DEFAULT_KUZU_CONFIG
from src.db_drivers.graph_driver.utils import GraphDBConnectionConfig
from src.db_drivers.vector_driver import VectorDriverConfig, VectorDBConnectionConfig

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

def main():
    # Load .env for database paths
    load_dotenv()
    
    logger.info("Initializing KG for clearing...")
    
    config = QAConfig.from_env()
    
    # KuzuDB config
    kuzu_path = os.path.abspath(config.kuzu_path)
    kuzu_cfg = GraphDBConnectionConfig(
        params=dict(DEFAULT_KUZU_CONFIG.params, path=kuzu_path)
    )
    graph_driver_cfg = GraphDriverConfig(db_vendor="kuzu", db_config=kuzu_cfg)
    
    # ChromaDB config
    nodes_path = os.path.abspath(config.chroma_nodes_path)
    quads_path = os.path.abspath(config.chroma_quads_path)
    
    nodes_cfg = VectorDriverConfig(
        db_vendor="chroma",
        db_config=VectorDBConnectionConfig(
            conn={"path": nodes_path},
            db_info={"db": "default_db", "table": "personalaitable"},
        ),
    )
    quads_cfg = VectorDriverConfig(
        db_vendor="chroma",
        db_config=VectorDBConnectionConfig(
            conn={"path": quads_path},
            db_info={"db": "default_db", "table": "personalaitable"},
        ),
    )
    
    # Assemble KnowledgeGraphModelConfig
    kg_model_cfg = KnowledgeGraphModelConfig(
        graph_config=GraphModelConfig(driver_config=graph_driver_cfg),
        embeddings_config=EmbeddingsModelConfig(
            nodesdb_driver_config=nodes_cfg,
            quadrupletsdb_driver_config=quads_cfg
        )
    )
    
    try:
        # Initialize model (opens connections)
        kg_model = KnowledgeGraphModel(kg_model_cfg)
        
        logger.info(f"Clearing KuzuDB at {kuzu_path}...")
        kg_model.graph_struct.db_conn.clear()
        
        logger.info(f"Clearing ChromaDB nodes at {nodes_path}...")
        kg_model.embeddings_struct.vectordbs['nodes'].clear()
        
        logger.info(f"Clearing ChromaDB quadruplets at {quads_path}...")
        kg_model.embeddings_struct.vectordbs['quadruplets'].clear()
        
        logger.info("✓ Databases cleared successfully. Schema preserved.")
        
    except Exception as e:
        logger.error(f"Error during KG clearing: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
