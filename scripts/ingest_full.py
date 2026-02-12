import logging
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from src.pipelines.ingestion.core_loader import CoreLoader
from src.kg_model.knowledge_graph_model import KnowledgeGraphModel, KnowledgeGraphModelConfig
from src.kg_model.graph_model import GraphModelConfig
from src.db_drivers.graph_driver.GraphDriver import GraphDriverConfig
from src.db_drivers.graph_driver.utils import GraphDBConnectionConfig
from src.utils import Logger

def run_full_ingestion():
    # Configuration for Neo4j
    # Ensure these credentials match your Docker container
    driver_conf = GraphDriverConfig(
        db_vendor='neo4j', 
        db_config=GraphDBConnectionConfig(
            host='localhost', 
            port=7687, 
            params={'user': 'neo4j', 'pwd': 'password'},
            db_info={'db': 'neo4j'} # Default DB
        )
    )

    graph_conf = GraphModelConfig(
        driver_config=driver_conf
    )

    # Use KnowledgeGraphModelConfig
    config = KnowledgeGraphModelConfig(
        graph_config=graph_conf,
        log=Logger('ingestion_full_log') 
    )

    kg_model = KnowledgeGraphModel(config=config)
    loader = CoreLoader(kg_model, config.log)

    print('Starting FULL ingestion into Neo4j...')
    
    input_file = 'processed_data/standardized_quadruplets.jsonl'
    
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found.")
        print("Please run 'python3 scripts/adapters/process_wikidata.py wikidata_big/kg/full.txt processed_data/standardized_quadruplets.jsonl' first.")
        return

    # batch_size=5000 is optimal for stability
    try:
        # Resume from 284,758 lines (86.5% completed previously)
        loader.load_from_jsonl(input_file, batch_size=5000, skip_lines=284758)
        print('Ingestion complete.')
    except Exception as e:
        print(f"Ingestion failed: {e}")

if __name__ == "__main__":
    run_full_ingestion()
