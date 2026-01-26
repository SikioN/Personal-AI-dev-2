import copy
import sys
sys.path.insert(0, "../")
from src.utils import TripletCreator, NodeCreator, NodeType
from src.utils.data_structs import RelationCreator, RelationType, create_id

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

#

REPLACE_SIMPLE_2AND3 = f'"{VALID_SIMPLE_TRIPLET2.start_node.name}, {VALID_SIMPLE_TRIPLET2.relation.name}, {VALID_SIMPLE_TRIPLET2.end_node.name}"; "{VALID_SIMPLE_TRIPLET3.start_node.name}, {VALID_SIMPLE_TRIPLET3.relation.name}, {VALID_SIMPLE_TRIPLET3.end_node.name}"'
REPLACE_SIMPLE_1 = f'"{VALID_SIMPLE_TRIPLET1.start_node.name}, {VALID_SIMPLE_TRIPLET1.relation.name}, {VALID_SIMPLE_TRIPLET1.end_node.name}"'
REPLACE_SIMPLE_2 = f'"{VALID_SIMPLE_TRIPLET2.start_node.name}, {VALID_SIMPLE_TRIPLET2.relation.name}, {VALID_SIMPLE_TRIPLET2.end_node.name}"'

#

REPLACE_SIMPLE_RAW_RESPONSE1 = '[["qwe, rty, uio" -> "asd, fgh, jkl"]]'
REPLACE_SIMPLE_PARSE_OUTPUT1 = {create_id("asd, fgh, jkl"): {create_id("qwe, rty, uio")}}

REPLACE_SIMPLE_RAW_RESPONSE2 = '[["qwe, rty, uio" -> "asd, fgh, jkl"],["zxc, vbn, jkl" -> "asd, fgh, jkl"]]'
REPLACE_SIMPLE_PARSE_OUTPUT2 = {create_id("asd, fgh, jkl"): {create_id("qwe, rty, uio"), create_id("zxc, vbn, jkl")}}

REPLACE_SIMPLE_RAW_RESPONSE3 = '[["qwe, rty, uio" "asd, fgh, jkl"],["zxc, vbn, jkl" -> "asd, fgh, jkl"]]'

REPLACE_SIMPLE_RAW_RESPONSE4 = '["qwe, rty, uio" -> "asd, fgh, jkl", "zxc, vbn, jkl" -> "asd, fgh, jkl"]'

REPLACE_SIMPLE_RAW_RESPONSE5 = '[[qwe, rty, uio -> "asd, fgh, jkl"], ["zxc, vbn, jkl" -> asd, fgh, jkl]]'

REPLACE_SIMPLE_RAW_RESPONSE6 = '[["q -> we, rty, uio" -> "asd, fgh, jkl"],["zxc, vbn, jkl" -> "asd, fgh, jkl"]]'

REPLACE_SIMPLE_RAW_RESPONSE7 = '[["qwe, r[t]y, uio" -> "asd, fgh, jkl"],["zxc, vbn, jkl" -> "asd, fgh, jkl"]]'

REPLACE_SIMPLE_RAW_RESPONSE8 = '[["qwe, rty, u"i"o" -> "asd, fgh, jkl"],["zxc, v"b"n, jkl" -> "asd, fgh, jkl"]]'
