import sys
sys.path.append('.')
from src.db_drivers.graph_driver.connectors.KuzuConnector import KuzuConnector
from src.utils.data_structs import QuadrupletCreator, NodeCreator, RelationCreator, NodeType, RelationType

conn = KuzuConnector()
conn.open_connection()

n1 = NodeCreator.create(type=NodeType.object, name="Company A")
n2 = NodeCreator.create(type=NodeType.object, name="Company B")
t1 = NodeCreator.create(type=NodeType.time, name="2021")
r1 = RelationCreator.create("partnership")

q1 = QuadrupletCreator.create(n1, r1, n2, time=t1)
q2 = QuadrupletCreator.create(n1, r1, n2, time=t1)

try:
    conn.create([q1, q2])
    print("SUCCESS")
except Exception as e:
    import traceback
    traceback.print_exc()
    print("FAILED:", e)
