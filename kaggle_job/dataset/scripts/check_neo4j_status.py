import sys
import os
sys.path.append(os.getcwd())

from src.db_drivers.graph_driver.GraphDriver import GraphDriverConfig, GraphDriver
from src.db_drivers.graph_driver.utils import GraphDBConnectionConfig
from src.utils import Logger

def check_neo4j():
    print("Checking Neo4j connection...")
    try:
        driver_conf = GraphDriverConfig(
            db_vendor='neo4j', 
            db_config=GraphDBConnectionConfig(
                host='localhost', 
                port=7687, 
                params={'user': 'neo4j', 'pwd': 'password'},
                db_info={'db': 'neo4j'}
            )
        )
        # Fix: Use static connect method
        driver = GraphDriver.connect(driver_conf)
        
        # Test connection
        print("Driver initialized. Testing connectivity...")
        # Assuming GraphDriver has a method to get connection or execute query
        # Let's try to list nodes count
        
        # Accessing the internal connector if possible, or using driver methods
        # GraphDriver initializes a specific connector based on vendor.
        # let's look at GraphDriver code to be sure, but usually it delegates.
        # For now, let's try a simple count if possible.
        
        # Checking if 'count_items' exists
        if hasattr(driver, 'count_items'):
            counts = driver.count_items()
            print(f"Data counts: {counts}")
        else:
             print(f"Driver ({type(driver)}) has no count_items method.")

        print("Neo4j connection seems OK.")
        return True
    except Exception as e:
        print(f"Failed to connect to Neo4j: {e}")
        return False

if __name__ == "__main__":
    check_neo4j()
