import sys
sys.path.append('.')
import kuzu
db = kuzu.Database('../../kuzu_volume', buffer_pool_size=1024**3)
conn = kuzu.Connection(db)

conn.execute("CREATE NODE TABLE IF NOT EXISTS test_node (str_id STRING, name STRING, prop MAP(STRING, STRING), PRIMARY KEY(str_id));")

# Insert first time
conn.execute("MERGE (n:test_node {str_id: '123'}) SET n.name = 'Test', n.prop = map(['k'], ['v']);")

try:
    # Begin tx, insert second time
    conn.execute("BEGIN TRANSACTION;")
    conn.execute("MERGE (n:test_node {str_id: '123'}) SET n.name = 'Test2', n.prop = map(['k2'], ['v2']);")
    conn.execute("COMMIT;")
    print("SECOND SUCCESS")
except Exception as e:
    print("SECOND FAILED:", e)

# What if we MERGE multiple times where the first is in the same TX but the node doesn't exist?
try:
    conn.execute("BEGIN TRANSACTION;")
    conn.execute("MERGE (n:test_node {str_id: '456'}) SET n.name = 'A', n.prop = map(['a'], ['b']);")
    conn.execute("MERGE (n:test_node {str_id: '456'}) SET n.name = 'B', n.prop = map(['c'], ['d']);")
    conn.execute("COMMIT;")
    print("THIRD SUCCESS")
except Exception as e:
    print("THIRD FAILED:", e)
