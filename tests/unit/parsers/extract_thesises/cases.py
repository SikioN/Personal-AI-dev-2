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

VALID_HYPER_RELATION = RelationCreator.create(
    r_type=RelationType.hyper, prop={'k5': 'v5'})

VALID_HYPER_NODE1 = NodeCreator.create(
    n_type=NodeType.hyper,
    name='rty', prop={'k1': 'v1'}
)

VALID_OBJECT_NODE2 = NodeCreator.create(
    n_type=NodeType.object,
    name='asd', prop={'k1': 'v1'})

VALID_HYPER_RELATION2 = RelationCreator.create(
    r_type=RelationType.hyper)

VALID_OBJECT_NODE6 = NodeCreator.create(
    n_type=NodeType.object,
    name='qazxsw')

VALID_HYPER_NODE7 = NodeCreator.create(
    n_type=NodeType.hyper,
    name='qsdcb')

VALID_HYPER_TRIPLET1 = TripletCreator.create(
    start_node=VALID_OBJECT_NODE1,
    relation=copy.deepcopy(VALID_HYPER_RELATION),
    end_node=VALID_HYPER_NODE1
)

VALID_HYPER_TRIPLET1_2 = TripletCreator.create(
    start_node=VALID_OBJECT_NODE2,
    relation=copy.deepcopy(VALID_HYPER_RELATION),
    end_node=VALID_HYPER_NODE1
)

VALID_HYPER_TRIPLET7 = TripletCreator.create(
    start_node=VALID_OBJECT_NODE1,
    relation=copy.deepcopy(VALID_HYPER_RELATION2),
    end_node=VALID_HYPER_NODE1
)

VALID_HYPER_TRIPLET8 = TripletCreator.create(
    start_node=VALID_OBJECT_NODE6,
    relation=copy.deepcopy(VALID_HYPER_RELATION),
    end_node=VALID_HYPER_NODE7
)
