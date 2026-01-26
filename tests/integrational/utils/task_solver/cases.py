import copy
import sys
sys.path.insert(0, "../")
from src.utils import ReturnStatus, TripletCreator, NodeCreator, NodeType
from src.utils.data_structs import RelationCreator, RelationType, create_id

# data structures fro english language

# OBJECT NODES

EN_VALID_OBJECT_NODE1 = NodeCreator.create(
    n_type=NodeType.object,
    name='qwe', prop={'k1': 'v1'})

EN_VALID_OBJECT_NODE2 = NodeCreator.create(
    n_type=NodeType.object,
    name='asd', prop={'k1': 'v1'})

EN_VALID_OBJECT_NODE3 = NodeCreator.create(
    n_type=NodeType.object,
    name='uio', prop={'k1': 'v1'})

# HYPER NODES

EN_VALID_HYPER_NODE1 = NodeCreator.create(
    n_type=NodeType.hyper,
    name='rty', prop={'k1': 'v1'}
)

EN_VALID_HYPER_NODE2 = NodeCreator.create(
    n_type=NodeType.hyper,
    name='fgh', prop={'k5': 'v5'}
)

EN_VALID_HYPER_NODE3 = NodeCreator.create(
    n_type=NodeType.hyper,
    name='jkl', prop={'k6': 'v7'}
)

# HYPER RELATIONS

EN_VALID_HYPER_RELATION1 = RelationCreator.create(
    r_type=RelationType.hyper, prop={'k5': 'v5'})

EN_VALID_HYPER_RELATION2 = RelationCreator.create(
    r_type=RelationType.hyper)

# SIMPLE RELATIONS

EN_VALID_SIMPLE_RELATION1 = RelationCreator.create(
    r_type=RelationType.simple,
    name='zxc', prop={'k3': 'v3'})

EN_VALID_SIMPLE_RELATION2 = RelationCreator.create(
    r_type=RelationType.simple,
    name='rfvbgt')

# SIMPLE TRIPLETS

EN_VALID_SIMPLE_TRIPLET1 = TripletCreator.create(
    start_node=EN_VALID_OBJECT_NODE1,
    relation=copy.deepcopy(EN_VALID_SIMPLE_RELATION1),
    end_node=EN_VALID_OBJECT_NODE2
)

EN_VALID_SIMPLE_TRIPLET2 = TripletCreator.create(
    start_node=EN_VALID_OBJECT_NODE2,
    relation=copy.deepcopy(EN_VALID_SIMPLE_RELATION1),
    end_node=EN_VALID_OBJECT_NODE3
)

EN_VALID_SIMPLE_TRIPLET3 = TripletCreator.create(
    start_node=EN_VALID_OBJECT_NODE3,
    relation=copy.deepcopy(EN_VALID_SIMPLE_RELATION1),
    end_node=EN_VALID_OBJECT_NODE1
)

# HYPER TRIPLETS

EN_VALID_HYPER_TRIPLET1 = TripletCreator.create(
    start_node=EN_VALID_OBJECT_NODE1,
    relation=copy.deepcopy(EN_VALID_HYPER_RELATION1),
    end_node=EN_VALID_HYPER_NODE1
)

EN_VALID_HYPER_TRIPLET2 = TripletCreator.create(
    start_node=EN_VALID_OBJECT_NODE2,
    relation=copy.deepcopy(EN_VALID_HYPER_RELATION1),
    end_node=EN_VALID_HYPER_NODE2
)


EN_VALID_HYPER_TRIPLET3 = TripletCreator.create(
    start_node=EN_VALID_OBJECT_NODE3,
    relation=copy.deepcopy(EN_VALID_HYPER_RELATION1),
    end_node=EN_VALID_HYPER_NODE3
)

# data structures for russian language

# OBJECT NODES

RU_VALID_OBJECT_NODE1 = NodeCreator.create(
    n_type=NodeType.object,
    name='йцу', prop={'k1': 'v1'})

RU_VALID_OBJECT_NODE2 = NodeCreator.create(
    n_type=NodeType.object,
    name='фыв', prop={'k1': 'v1'})

RU_VALID_OBJECT_NODE3 = NodeCreator.create(
    n_type=NodeType.object,
    name='ячс', prop={'k1': 'v1'})

# HYPER NODES

RU_VALID_HYPER_NODE1 = NodeCreator.create(
    n_type=NodeType.hyper,
    name='кен', prop={'k1': 'v1'}
)

RU_VALID_HYPER_NODE2 = NodeCreator.create(
    n_type=NodeType.hyper,
    name='апр', prop={'k5': 'v5'}
)

RU_VALID_HYPER_NODE3 = NodeCreator.create(
    n_type=NodeType.hyper,
    name='мит', prop={'k6': 'v7'}
)

# HYPER RELATIONS

RU_VALID_HYPER_RELATION1 = RelationCreator.create(
    r_type=RelationType.hyper, prop={'k5': 'v5'})

RU_VALID_HYPER_RELATION2 = RelationCreator.create(
    r_type=RelationType.hyper)

# SIMPLE RELATIONS

RU_VALID_SIMPLE_RELATION1 = RelationCreator.create(
    r_type=RelationType.simple,
    name='епи', prop={'k3': 'v3'})

RU_VALID_SIMPLE_RELATION2 = RelationCreator.create(
    r_type=RelationType.simple,
    name='нрт')

# SIMPLE TRIPLETS

RU_VALID_SIMPLE_TRIPLET1 = TripletCreator.create(
    start_node=RU_VALID_OBJECT_NODE1,
    relation=copy.deepcopy(RU_VALID_SIMPLE_RELATION1),
    end_node=RU_VALID_OBJECT_NODE2
)

RU_VALID_SIMPLE_TRIPLET2 = TripletCreator.create(
    start_node=RU_VALID_OBJECT_NODE2,
    relation=copy.deepcopy(RU_VALID_SIMPLE_RELATION1),
    end_node=RU_VALID_OBJECT_NODE3
)

RU_VALID_SIMPLE_TRIPLET3 = TripletCreator.create(
    start_node=RU_VALID_OBJECT_NODE3,
    relation=copy.deepcopy(RU_VALID_SIMPLE_RELATION1),
    end_node=RU_VALID_OBJECT_NODE1
)

# HYPER TRIPLETS

RU_VALID_HYPER_TRIPLET1 = TripletCreator.create(
    start_node=RU_VALID_OBJECT_NODE1,
    relation=copy.deepcopy(RU_VALID_HYPER_RELATION1),
    end_node=RU_VALID_HYPER_NODE1
)

RU_VALID_HYPER_TRIPLET2 = TripletCreator.create(
    start_node=RU_VALID_OBJECT_NODE2,
    relation=copy.deepcopy(RU_VALID_HYPER_RELATION1),
    end_node=RU_VALID_HYPER_NODE2
)

RU_VALID_HYPER_TRIPLET3 = TripletCreator.create(
    start_node=RU_VALID_OBJECT_NODE3,
    relation=copy.deepcopy(RU_VALID_HYPER_RELATION1),
    end_node=RU_VALID_HYPER_NODE3
)
