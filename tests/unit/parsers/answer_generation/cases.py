import copy
import sys
sys.path.insert(0, "../")
from src.utils import TripletCreator, NodeCreator, NodeType,\
      RelationCreator, RelationType

VALID_OBJECT_NODE1 = NodeCreator.create(
    n_type=NodeType.object,
    name='qwe', prop={'k1': 'v1'})

VALID_OBJECT_NODE2 = NodeCreator.create(
    n_type=NodeType.object,
    name='asd', prop={'k1': 'v1'})

VALID_SIMPLE_RELATION1 = RelationCreator.create(
    r_type=RelationType.simple,
    name='zxc', prop={'k3': 'v3'})

VALID_SIMPLE_TRIPLET1 = TripletCreator.create(
    start_node=VALID_OBJECT_NODE1,
    relation=copy.deepcopy(VALID_SIMPLE_RELATION1),
    end_node=VALID_OBJECT_NODE2
)

VALID_HYPER_NODE1 = NodeCreator.create(
    n_type=NodeType.hyper,
    name='rty', prop={'k1': 'v1'}
)

VALID_HYPER_RELATION = RelationCreator.create(
    r_type=RelationType.hyper, prop={'k5': 'v5'})

VALID_HYPER_TRIPLET1 = TripletCreator.create(
    start_node=VALID_OBJECT_NODE1,
    relation=copy.deepcopy(VALID_HYPER_RELATION),
    end_node=VALID_HYPER_NODE1
)
