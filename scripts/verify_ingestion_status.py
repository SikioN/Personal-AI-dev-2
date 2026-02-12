import sys
import os
import chromadb
from neo4j import GraphDatabase

# Add project root to path
sys.path.append(os.getcwd())

def verify_status():
    print("--- 1. Checking Neo4j Status ---")
    try:
        # Connect to Neo4j
        uri = "bolt://localhost:7687"
        auth = ("neo4j", "password")
        with GraphDatabase.driver(uri, auth=auth) as driver:
            driver.verify_connectivity()
            records, _, _ = driver.execute_query(
                "MATCH (n) RETURN count(n) as count"
            )
            neo4j_count = records[0]["count"]
            print(f"✅ Neo4j Connection: OK")
            print(f"Nodes in Neo4j: {neo4j_count}")
    except Exception as e:
        print(f"❌ Neo4j Connection Failed: {e}")

    print("\n--- 2. Checking ChromaDB Status ---")
    try:
        # Paths from src/kg_model/embeddings_model.py
        nodes_path = "../data/graph_structures/vectorized_nodes/default_densedb"
        
        # Check if path exists
        if not os.path.exists(nodes_path):
             print(f"⚠️ ChromaDB path not found: {nodes_path}")
             # Start from current dir to be safe
             nodes_path = "data/graph_structures/vectorized_nodes/default_densedb"
             
        if os.path.exists(nodes_path):
             client = chromadb.PersistentClient(path=nodes_path)
             try:
                 coll = client.get_collection("vectorized_nodes")
                 count = coll.count()
                 print(f"✅ ChromaDB Connection: OK (Path: {nodes_path})")
                 print(f"Vectors in ChromaDB (Nodes): {count}")
             except Exception as e:
                 print(f"Collection 'vectorized_nodes' not found or empty yet: {e}")
        else:
             print(f"❌ ChromaDB path still not found: {nodes_path}")

    except Exception as e:
        print(f"❌ ChromaDB Check Failed: {e}")

if __name__ == "__main__":
    verify_status()
