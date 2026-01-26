import copy
import sys
sys.path.insert(0, "../")
from src.utils import ReturnStatus, TripletCreator, NodeCreator, NodeType
from src.utils.data_structs import RelationCreator, RelationType, create_id

# OBJECT NODES

VALID_OBJECT_NODE1 = NodeCreator.create(
    n_type=NodeType.object,
    name='qwe', prop={'k1': 'v1'})

VALID_OBJECT_NODE2 = NodeCreator.create(
    n_type=NodeType.object,
    name='asd', prop={'k1': 'v1'})

VALID_OBJECT_NODE3 = NodeCreator.create(
    n_type=NodeType.object,
    name='uio', prop={'k1': 'v1'})

VALID_OBJECT_NODE4 = NodeCreator.create(
    n_type=NodeType.object,
    name='jkl', prop={'k4': 'v4'})

VALID_OBJECT_NODE5 = NodeCreator.create(
    n_type=NodeType.object,
    name='zxc', prop={'k5': 'v5'})


VALID_OBJECT_NODE6 = NodeCreator.create(
    n_type=NodeType.object,
    name='qazxsw')

VALID_OBJECT_NODE7 = NodeCreator.create(
    n_type=NodeType.object,
    name='tgbh')

# HYPER NODES

VALID_HYPER_NODE1 = NodeCreator.create(
    n_type=NodeType.hyper,
    name='rty', prop={'k1': 'v1'}
)

VALID_HYPER_NODE2 = NodeCreator.create(
    n_type=NodeType.hyper,
    name='fgh', prop={'k5': 'v5'}
)

VALID_HYPER_NODE3 = NodeCreator.create(
    n_type=NodeType.hyper,
    name='jkl', prop={'k6': 'v7'}
)

VALID_HYPER_NODE4 = NodeCreator.create(
    n_type=NodeType.hyper,
    name='qwe rty', prop={'k7': 'v7'}
)

VALID_HYPER_NODE5 = NodeCreator.create(
    n_type=NodeType.hyper,
    name='asd fgh', prop={'k8': 'v8'}
)

VALID_HYPER_NODE6 = NodeCreator.create(
    n_type=NodeType.hyper,
    name='zxc vbn', prop={'k9': 'v9'}
)

VALID_HYPER_NODE7 = NodeCreator.create(
    n_type=NodeType.hyper,
    name='qsdcb')

# HYPER RELATIONS

VALID_HYPER_RELATION = RelationCreator.create(
    r_type=RelationType.hyper, prop={'k5': 'v5'})

VALID_HYPER_RELATION2 = RelationCreator.create(
    r_type=RelationType.hyper)

# SIMPLE RELATIONS

VALID_SIMPLE_RELATION1 = RelationCreator.create(
    r_type=RelationType.simple,
    name='zxc', prop={'k3': 'v3'})

VALID_SIMPLE_RELATION2 = RelationCreator.create(
    r_type=RelationType.simple,
    name='rty', prop={'k3': 'v3'})

VALID_SIMPLE_RELATION3 = RelationCreator.create(
    r_type=RelationType.simple,
    name='vbn', prop={'k4': 'v4'})

VALID_SIMPLE_RELATION4 = RelationCreator.create(
    r_type=RelationType.simple,
    name='fgh', prop={'k5': 'v5'})

VALID_SIMPLE_RELATION5 = RelationCreator.create(
    r_type=RelationType.simple,
    name='rfvbgt')

# SIMPLE TRIPLETS

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

VALID_SIMPLE_TRIPLET3 = TripletCreator.create(
    start_node=VALID_OBJECT_NODE3,
    relation=copy.deepcopy(VALID_SIMPLE_RELATION1),
    end_node=VALID_OBJECT_NODE1
)

VALID_SIMPLE_TRIPLET4 = TripletCreator.create(
    start_node=VALID_OBJECT_NODE2,
    relation=copy.deepcopy(VALID_SIMPLE_RELATION4),
    end_node=VALID_OBJECT_NODE4
)

VALID_SIMPLE_TRIPLET5 = TripletCreator.create(
    start_node=VALID_OBJECT_NODE1,
    relation=copy.deepcopy(VALID_SIMPLE_RELATION2),
    end_node=VALID_OBJECT_NODE3
)

VALID_SIMPLE_TRIPLET6 = TripletCreator.create(
    start_node=VALID_OBJECT_NODE5,
    relation=copy.deepcopy(VALID_SIMPLE_RELATION3),
    end_node=VALID_OBJECT_NODE4
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

# HYPER TRIPLETS

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


VALID_HYPER_TRIPLET2 = TripletCreator.create(
    start_node=VALID_OBJECT_NODE2,
    relation=copy.deepcopy(VALID_HYPER_RELATION),
    end_node=VALID_HYPER_NODE2
)

VALID_HYPER_TRIPLET3 = TripletCreator.create(
    start_node=VALID_OBJECT_NODE3,
    relation=copy.deepcopy(VALID_HYPER_RELATION),
    end_node=VALID_HYPER_NODE3
)

VALID_HYPER_TRIPLET4 = TripletCreator.create(
    start_node=VALID_OBJECT_NODE2,
    relation=copy.deepcopy(VALID_HYPER_RELATION),
    end_node=VALID_HYPER_NODE4
)

VALID_HYPER_TRIPLET5 = TripletCreator.create(
    start_node=VALID_OBJECT_NODE2,
    relation=copy.deepcopy(VALID_HYPER_RELATION),
    end_node=VALID_HYPER_NODE5
)

VALID_HYPER_TRIPLET6 = TripletCreator.create(
    start_node=VALID_OBJECT_NODE2,
    relation=copy.deepcopy(VALID_HYPER_RELATION),
    end_node=VALID_HYPER_NODE6
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

#

REPLACE_THESISES_2AND3 = f'["{VALID_HYPER_TRIPLET2.end_node.name}", "{VALID_HYPER_TRIPLET3.end_node.name}"]'
REPLACE_THESISES_1 = f'["{VALID_HYPER_TRIPLET1.end_node.name}"]'
REPLACE_THESISES_2 = f'["{VALID_HYPER_TRIPLET2.end_node.name}"]'

#

REPLACE_SIMPLE_2AND3 = f'"{VALID_SIMPLE_TRIPLET2.start_node.name}, {VALID_SIMPLE_TRIPLET2.relation.name}, {VALID_SIMPLE_TRIPLET2.end_node.name}"; "{VALID_SIMPLE_TRIPLET3.start_node.name}, {VALID_SIMPLE_TRIPLET3.relation.name}, {VALID_SIMPLE_TRIPLET3.end_node.name}"'
REPLACE_SIMPLE_1 = f'"{VALID_SIMPLE_TRIPLET1.start_node.name}, {VALID_SIMPLE_TRIPLET1.relation.name}, {VALID_SIMPLE_TRIPLET1.end_node.name}"'
REPLACE_SIMPLE_2 = f'"{VALID_SIMPLE_TRIPLET2.start_node.name}, {VALID_SIMPLE_TRIPLET2.relation.name}, {VALID_SIMPLE_TRIPLET2.end_node.name}"'

#
