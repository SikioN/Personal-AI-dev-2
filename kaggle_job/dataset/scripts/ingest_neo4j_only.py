import logging
import sys
import os
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.getcwd())

from src.pipelines.ingestion.core_loader import CoreLoader
from src.kg_model.knowledge_graph_model import KnowledgeGraphModel, KnowledgeGraphModelConfig
from src.kg_model.graph_model import GraphModelConfig
from src.db_drivers.graph_driver.GraphDriver import GraphDriverConfig
from src.db_drivers.graph_driver.utils import GraphDBConnectionConfig
from src.utils import Logger
from src.kg_model.knowledge_graph_model import KnowledgeGraphModel

# Monkey-patch KnowledgeGraphModel to completely skip EmbeddingsModel initialization
original_init = KnowledgeGraphModel.__init__

def patched_init(self, config=None, cache_kvdriver_config=None):
    from src.kg_model.knowledge_graph_model import KnowledgeGraphModelConfig
    from src.kg_model.graph_model import GraphModel
    
    if config is None:
        config = KnowledgeGraphModelConfig()
    
    self.config = config
    self.config.graph_config.log = self.config.log
    self.config.graph_config.verbose = self.config.verbose
    
    # Only initialize GraphModel, skip EmbeddingsModel entirely
    self.graph_struct = GraphModel(self.config.graph_config)
    
    # Create mock EmbeddingsModel to avoid NoneType errors
    class MockEmbeddingsModel:
        def create_quadruplets(self, quadruplets, status_bar=False):
            return {'nodes': {'created': [], 'failed': []}, 'quadruplets': {'created': [], 'failed': []}}
        
        def delete_quadruplets(self, quadruplets, delete_info=None):
            return {'nodes': {'deleted': [], 'failed': []}, 'quadruplets': {'deleted': [], 'failed': []}}
        
        def count_items(self):
            return {'nodes': 0, 'quadruplets': 0}
        
        def clear(self):
            pass
    
    self.embeddings_struct = MockEmbeddingsModel()
    self.nodestree_struct = None
    
    self.log = self.config.log
    self.verbose = self.config.verbose
    
    print("ℹ️  EmbeddingsModel (ChromaDB) SKIPPED - Neo4j only mode")

KnowledgeGraphModel.__init__ = patched_init

def run_neo4j_ingestion():
    # Configuration for Neo4j
    driver_conf = GraphDriverConfig(
        db_vendor='neo4j', 
        db_config=GraphDBConnectionConfig(
            host='localhost', 
            port=7687, 
            params={'user': 'neo4j', 'pwd': 'password'},
            db_info={'db': 'neo4j'}
        )
    )

    graph_conf = GraphModelConfig(
        driver_config=driver_conf
    )

    # Use KnowledgeGraphModelConfig
    config = KnowledgeGraphModelConfig(
        graph_config=graph_conf,
        log=Logger('ingestion_neo4j_log') 
    )

    kg_model = KnowledgeGraphModel(config=config)
    loader = CoreLoader(kg_model, config.log)

    print('Starting NEO4J-ONLY ingestion...')
    print('Vector DB ingestion is disabled by monkey-patching.')
    
    input_file = 'processed_data/standardized_quadruplets.jsonl'
    
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found.")
        return

    try:
        # Start from the beginning to ensure full consistency if Neo4j is empty/broken
        # If user wants to resume, they can edit this. 
        # But "fix" implies ensuring correctness, so full reload is safer if fast enough.
        # batch_size=5000
        loader.load_from_jsonl(input_file, batch_size=5000, skip_lines=0)
        print('Ingestion complete.')
    except Exception as e:
        print(f"Ingestion failed: {e}")

if __name__ == "__main__":
    run_neo4j_ingestion()
