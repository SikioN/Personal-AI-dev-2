
import os
import sys
from src.db_drivers.vector_driver import VectorDriverConfig, VectorDBConnectionConfig, VectorDBInstance
from src.db_drivers.vector_driver.chroma_db_driver import ChromaDBDriver

def inspect_id():
    ROOT_DIR = os.getcwd()
    # Use the path from app.py/test_pipeline_integration.py
    nodes_path = os.path.join(ROOT_DIR, "data/graph_structures/vectorized_nodes/wikidata_test")
    
    config = VectorDriverConfig(
        db_vendor='chroma', db_config=VectorDBConnectionConfig(
            conn={'path': nodes_path},
            db_info={'db': 'default_db', 'table': "personalaitable"}))

    print(f"Connecting to Vector DB at {nodes_path}...")
    driver = ChromaDBDriver(config)
    
    target_id = "e0dbcf3abfbb2f07e30a19cd676ab2f9"
    print(f"Looking for ID: {target_id}")
    
    # ChromaDBDriver.retrieve usually takes embeddings. 
    # Does it support get by ID?
    # Checking implementation of ChromaDBDriver might be needed, but assuming standard get method or using raw client.
    
    try:
        # Access raw collection to get by ID
        collection = driver.collection
        result = collection.get(ids=[target_id])
        print("Result:", result)
        
        if result and result['documents']:
            print("\nFOUND DOCUMENT:")
            print(result['documents'][0])
            print("\nMETADATA:")
            print(result['metadatas'][0])
        else:
            print("ID not found in Vector DB.")
            
    except Exception as e:
        print(f"Error: {e}")
        # Fallback dump first 5 items to see format
        print("Dumping first 5 items...")
        res = collection.get(limit=5)
        for i, doc in enumerate(res['documents']):
            print(f"[{res['ids'][i]}]: {doc}")

if __name__ == "__main__":
    inspect_id()
