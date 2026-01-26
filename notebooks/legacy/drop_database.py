from neo4j_functions import Neo4jConnection

conn = Neo4jConnection(uri="bolt://31.207.47.254:7687", user="neo4j", pwd="password")

conn.execute_query("CREATE DATABASE testdb IF NOT EXISTS")
#conn.execute_query("DROP DATABASE testdb IF EXISTS")

#res = conn.extract_node(node_name="Xiaomi 11", db="testdb")
#print(res)
