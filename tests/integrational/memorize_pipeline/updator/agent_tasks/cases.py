import sys

# TO CHANGE
PROJECT_BASE_DIR = '../'
sys.path.insert(0, PROJECT_BASE_DIR)

from src.utils import RelationType, NodeType, NodeCreator, RelationCreator, TripletCreator

OBJECT_NODE1 = NodeCreator.create(n_type=NodeType.object, name='qwe')
OBJECT_NODE2 = NodeCreator.create(n_type=NodeType.object, name='asd')
OBJECT_NODE3 = NodeCreator.create(n_type=NodeType.object, name='zxc')
OBJECT_NODE4 = NodeCreator.create(n_type=NodeType.object, name='rty')
OBJECT_NODE5 = NodeCreator.create(n_type=NodeType.object, name='fgh')
OBJECT_NODE6 = NodeCreator.create(n_type=NodeType.object, name='cvb')

SIMPLE_REL1 = RelationCreator.create(r_type=RelationType.simple, name='uio')
SIMPLE_REL2 = RelationCreator.create(r_type=RelationType.simple, name='jkl')
SIMPLE_REL3 = RelationCreator.create(r_type=RelationType.simple, name='bnm')

SIMPLE_TRIPLET1 = TripletCreator.create(
    start_node=OBJECT_NODE1,relation=SIMPLE_REL1,end_node=OBJECT_NODE2)
SIMPLE_TRIPLET2 = TripletCreator.create(
    start_node=OBJECT_NODE3,relation=SIMPLE_REL2,end_node=OBJECT_NODE4)
SIMPLE_TRIPLET3 = TripletCreator.create(
    start_node=OBJECT_NODE5,relation=SIMPLE_REL3,end_node=OBJECT_NODE6)

SIMPLE_TRIPLET4 = TripletCreator.create(
    start_node=OBJECT_NODE3, relation=SIMPLE_REL3, end_node=OBJECT_NODE4)
SIMPLE_TRIPLET5 = TripletCreator.create(
    start_node=OBJECT_NODE5, relation=SIMPLE_REL1, end_node=OBJECT_NODE6)
SIMPLE_TRIPLET6 = TripletCreator.create(
    start_node=OBJECT_NODE5,relation=SIMPLE_REL2,end_node=OBJECT_NODE6)

NO_TRIPLET_REPL_AGENT_ANSWER = '[]'
ONE_TRIPLET_REPL_AGENT_ANSWER = f'[["{SIMPLE_TRIPLET4.start_node.name}, {SIMPLE_TRIPLET4.relation.name}, {SIMPLE_TRIPLET4.end_node.name}" -> "{SIMPLE_TRIPLET2.start_node.name}, {SIMPLE_TRIPLET2.relation.name}, {SIMPLE_TRIPLET2.end_node.name}"]'
SEVERAL_TRIPLET_REPL_AGENT_ANSWER = f'[["{SIMPLE_TRIPLET5.start_node.name}, {SIMPLE_TRIPLET5.relation.name}, {SIMPLE_TRIPLET5.end_node.name}" -> "{SIMPLE_TRIPLET3.start_node.name}, {SIMPLE_TRIPLET3.relation.name}, {SIMPLE_TRIPLET3.end_node.name}"], ["{SIMPLE_TRIPLET6.start_node.name}, {SIMPLE_TRIPLET6.relation.name}, {SIMPLE_TRIPLET6.end_node.name}" -> "{SIMPLE_TRIPLET3.start_node.name}, {SIMPLE_TRIPLET3.relation.name}, {SIMPLE_TRIPLET3.end_node.name}"]]'
BAD_TRIPLET_AGENT_ANSWER = f'[[{SIMPLE_TRIPLET4.start_node.name} {SIMPLE_TRIPLET4.relation.name} {SIMPLE_TRIPLET4.end_node.name} -> {SIMPLE_TRIPLET1.start_node.name} {SIMPLE_TRIPLET1.relation.name} {SIMPLE_TRIPLET1.end_node.name}]]'

HYPER_NODE1 = NodeCreator.create(n_type=NodeType.hyper, name='qwerty')
HYPER_NODE2 = NodeCreator.create(n_type=NodeType.hyper, name='asdfg')
HYPER_NODE3 = NodeCreator.create(n_type=NodeType.hyper, name='zxcvb')
HYPER_NODE4 = NodeCreator.create(n_type=NodeType.hyper, name='poiuy')
HYPER_NODE5 = NodeCreator.create(n_type=NodeType.hyper, name='tgbnhy')

HYPER_REL = RelationCreator.create(r_type=RelationType.hyper)

HYPER_TRIPLET1 = TripletCreator.create(
    start_node=OBJECT_NODE1,relation=HYPER_REL,
    end_node=HYPER_NODE1)
HYPER_TRIPLET2 = TripletCreator.create(
    start_node=OBJECT_NODE2, relation=HYPER_REL, end_node=HYPER_NODE2)
HYPER_TRIPLET3 = TripletCreator.create(
    start_node=OBJECT_NODE3, relation=HYPER_REL, end_node=HYPER_NODE3)
HYPER_TRIPLET4 = TripletCreator.create(
    start_node=OBJECT_NODE4, relation=HYPER_REL, end_node=HYPER_NODE4)
HYPER_TRIPLET5 = TripletCreator.create(
    start_node=OBJECT_NODE5, relation=HYPER_REL, end_node=HYPER_NODE5)

NO_THESIS_REPL_AGENT_ANSWER = '[]'
ONE_THESIS_REPL_AGENT_ANSWER = f'["{HYPER_TRIPLET2.end_node.name} <- {HYPER_TRIPLET4.end_node.name}"]'
SEVERAL_THESIS_REPL_AGENT_ANSWER = f'["{HYPER_TRIPLET3.end_node.name} <- {HYPER_TRIPLET4.end_node.name}", "{HYPER_TRIPLET3.end_node.name} <- {HYPER_TRIPLET5.end_node.name}"]'
BAD_THESIS_AGENT_ANSWER = f'[{HYPER_TRIPLET1.end_node.name} {HYPER_TRIPLET4.end_node.name}]'
