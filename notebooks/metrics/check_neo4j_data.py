
import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), '../..')))

from src.personalai_main import PersonalAI, PersonalAIConfig

def check_neo4j():
    config = PersonalAIConfig()
    config.verbose = True
    pai = PersonalAI(config)
    graph_driver = pai.kg_model.graph_struct.db_conn
    
    print("Checking relationship properties in Neo4j...")
    query = """
    MATCH ()-[r]->()
    RETURN keys(r) as keys, type(r) as type
    LIMIT 10
    """
    
    try:
        results = graph_driver.execute_query(query)
        if not results:
            print("No relationships found in Neo4j!")
            return
            
        for i, record in enumerate(results, 1):
            print(f"{i}. Type: {record['type']}, Keys: {record['keys']}")
            
        print("\nChecking nodes with str_id and names...")
        query_nodes = """
        MATCH (n)
        WHERE n.str_id IS NOT NULL
        RETURN n.name as name, n.str_id as str_id, labels(n) as labels
        LIMIT 5
        """
        node_results = graph_driver.execute_query(query_nodes)
        for i, record in enumerate(node_results, 1):
            print(f"{i}. Name: {record['name']}, ID: {record['str_id']}, Labels: {record['labels']}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_neo4j()
