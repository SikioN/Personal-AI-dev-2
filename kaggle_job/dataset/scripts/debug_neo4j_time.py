import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.db_drivers.graph_driver.connectors.Neo4jConnector import Neo4jConnector
import json

def debug_neo4j():
    conn = Neo4jConnector()
    conn.open_connection()
    
    print("--- Debugging Neo4j Time Nodes ---")
    
    # query for Vladimir Nabokov (Q36591)
    # We know his name is Vladimir Nabokov
    query = """
    MATCH (n)-[r]-(m)
    WHERE n.str_id = "Q36591" 
    RETURN n, r, m
    LIMIT 5
    """
    
    results = conn.execute_query(query)
    for res in results:
        r = res['r']
        r_props = dict(r)
        print(f"\nRelation: {r.type} ({r_props.get('name')})")
        print(f"Props: {r_props}")
        
        if 'time_node_id' in r_props:
            tid_json = r_props['time_node_id']
            print(f"Found time_node_id (raw): {tid_json}")
            
            # Try clean string
            try:
                tid_clean = json.loads(tid_json)
                print(f"Clean ID: {tid_clean}")
            except:
                tid_clean = tid_json
                
            # Check if Time node exists
            # We check raw string match first (as logic uses)
            t_query = f"MATCH (t:time) WHERE t.str_id = {tid_json} RETURN t"
            t_res = conn.execute_query(t_query)
            if t_res:
                print(" -> Time Node FOUND via raw match!")
                print(" -> Props:", dict(t_res[0]['t']))
            else:
                print(" -> Time Node NOT FOUND via raw match.")
                # Try clean match
                t_query_clean = f'MATCH (t:time) WHERE t.str_id = "{tid_clean}" RETURN t'
                t_res_clean = conn.execute_query(t_query_clean)
                if t_res_clean:
                     print(" -> Time Node FOUND via clean match!")
                     print(" -> Props:", dict(t_res_clean[0]['t']))
                else:
                    print(" -> Time Node REALLY NOT FOUND.")

    print("\n--- Listing Sample Time Nodes ---")
    t_sample = conn.execute_query("MATCH (t:time) RETURN t LIMIT 3")
    for row in t_sample:
        print(dict(row['t']))

    conn.close_connection()

if __name__ == "__main__":
    debug_neo4j()
