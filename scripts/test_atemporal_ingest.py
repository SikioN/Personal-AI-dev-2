
import os
import sys
import json
import logging
from unittest.mock import MagicMock

# Setup paths
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

# Mock modules to avoid heavy imports and permission/db errors during logic check
sys.modules['src.db_drivers.vector_driver'] = MagicMock()
sys.modules['src.db_drivers.vector_driver.embedders'] = MagicMock()
sys.modules['src.kg_model.embeddings_model'] = MagicMock()
sys.modules['src.kg_model.graph_model'] = MagicMock()
sys.modules['src.kg_model.knowledge_graph_model'] = MagicMock()
sys.modules['chromadb'] = MagicMock()

from src.pipelines.ingestion.temporal_kg_ingester import TemporalKGIngester

# Enable logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("src.pipelines.ingestion.temporal_kg_ingester")
logger.setLevel(logging.INFO)

def test_atemporal_ingestion_logic():
    print("\n[TEST] Verifying atemporal ingestion logic...")
    
    # 1. Setup mock kg_model
    kg_model = MagicMock()
    # Mock add_knowledge to track what's being added
    added_quads = []
    def mock_add(quads, **kwargs):
        added_quads.extend(quads)
    kg_model.add_knowledge.side_effect = mock_add
    
    ingester = TemporalKGIngester(kg_model=kg_model)
    
    # 2. Test input with NO years
    records = [
        {
            "s": {"id": "Q1", "name": "Albert Einstein"},
            "r": {"id": "P27", "name": "citizenship", "type": "simple"},
            "o": {"id": "Q30", "name": "USA"},
            "t": {"prop": {}} # Empty temporal data
        }
    ]
    
    # 3. Target record for ingestion
    quads, errors = ingester._json_to_quadruplets(records)
    
    print(f"Parsed {len(quads)} quads, {errors} errors.")
    
    if len(quads) == 0:
        print("FAILED: No quads parsed for atemporal record.")
        sys.exit(1)
        
    q = quads[0]
    print(f"Time node name: {q.time.name}")
    
    if q.time.name != "Always":
        print(f"FAILED: Expected time name 'Always', got '{q.time.name}'")
        sys.exit(1)
        
    # 4. Ingest and check TComplEx skipping
    print("Simulating ingestion...")
    result = ingester.ingest_quadruplets(quads, update_tkbc=False)
    print(f"Ingestion result: {result}")
    
    if result.added != 1:
        print("FAILED: Fact not added to KG.")
        sys.exit(1)
        
    print("\n[SUCCESS] Atemporal ingestion logic verified.")

if __name__ == "__main__":
    test_atemporal_ingestion_logic()
