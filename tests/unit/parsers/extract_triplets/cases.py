import copy
import sys

# TO CHANGE
PROJECT_BASE_DIR = '../'
sys.path.insert(0, PROJECT_BASE_DIR)
from src.utils import TripletCreator, \
    NodeCreator, NodeType, RelationCreator, RelationType

VALID_OBJECT_NODE1 = NodeCreator.create(
    n_type=NodeType.object,
    name='qwe', prop={'k1': 'v1'})

VALID_OBJECT_NODE2 = NodeCreator.create(
    n_type=NodeType.object,
    name='asd', prop={'k1': 'v1'})

VALID_OBJECT_NODE3 = NodeCreator.create(
    n_type=NodeType.object,
    name='uio', prop={'k1': 'v1'})

VALID_SIMPLE_RELATION5 = RelationCreator.create(
    r_type=RelationType.simple,
    name='rfvbgt')

VALID_OBJECT_NODE6 = NodeCreator.create(
    n_type=NodeType.object,
    name='qazxsw')

VALID_SIMPLE_RELATION1 = RelationCreator.create(
    r_type=RelationType.simple,
    name='zxc', prop={'k3': 'v3'})

VALID_SIMPLE_TRIPLET1 = TripletCreator.create(
    start_node=VALID_OBJECT_NODE1,
    relation=copy.deepcopy(VALID_SIMPLE_RELATION1),
    end_node=VALID_OBJECT_NODE2
)

VALID_SIMPLE_TRIPLET2 = TripletCreator.create(
    start_node=VALID_OBJECT_NODE2,
    relation=copy.deepcopy(VALID_SIMPLE_RELATION1),
    end_node=VALID_OBJECT_NODE3
)

VALID_SIMPLE_TRIPLET7 = TripletCreator.create(
    start_node=VALID_OBJECT_NODE6,
    relation=copy.deepcopy(VALID_SIMPLE_RELATION1),
    end_node=VALID_OBJECT_NODE6
)

VALID_SIMPLE_TRIPLET8 = TripletCreator.create(
    start_node=VALID_OBJECT_NODE1,
    relation=copy.deepcopy(VALID_SIMPLE_RELATION5),
    end_node=VALID_OBJECT_NODE2
)
