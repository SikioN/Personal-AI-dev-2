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

VALID_HYPER_RELATION = RelationCreator.create(
    r_type=RelationType.hyper, prop={'k5': 'v5'})

VALID_HYPER_TRIPLET1 = TripletCreator.create(
    start_node=VALID_OBJECT_NODE1,
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

REPLACE_THESISES_2AND3 = f'["{VALID_HYPER_TRIPLET2.end_node.name}", "{VALID_HYPER_TRIPLET3.end_node.name}"]'
REPLACE_THESISES_1 = f'["{VALID_HYPER_TRIPLET1.end_node.name}"]'
REPLACE_THESISES_2 = f'["{VALID_HYPER_TRIPLET2.end_node.name}"]'

# валидный (один сопоставленный тезис)
REPLACE_THESISES_RAW_RESPONSE1 = '["qwe rty <- asd fgh"]'
REPLACE_THESISES_PARSE_OUTPUT1 = {create_id("qwe rty"): {create_id("asd fgh")}}

# валидный (несколько сопоставленных тезисов)
REPLACE_THESISES_RAW_RESPONSE2 = '["qwe rty <- asd fgh", "qwe rty <- zxc vbn"]'
REPLACE_THESISES_PARSE_OUTPUT2 = {create_id("qwe rty"): {create_id("asd fgh"), create_id("zxc vbn")}}

# невалидный (отсутствует стрелка)
REPLACE_THESISES_RAW_RESPONSE3 =  '["qwe rty  asd fgh", "qwe rty <- zxc vbn"]'

# невалидный (отсутствует скобка)
REPLACE_THESISES_RAW_RESPONSE4 = '"qwe rty <- asd fgh", "qwe rty <- zxc vbn"]'

# невалидный (отсутствует кавычка)
REPLACE_THESISES_RAW_RESPONSE5 = '[qwe rty <- asd fgh, "qwe rty <- zxc vbn"]'

# специальный символ (стрелка)
REPLACE_THESISES_RAW_RESPONSE6 = '["qwe <- rty <- asd fgh", "qwe rty <- zxc vbn"]'

# специальный символ (скобки)
REPLACE_THESISES_RAW_RESPONSE7 = '["qwe [rty] <- asd fgh", "qwe rty <- zxc vbn"]'

# специальный символ (кавычки)
REPLACE_THESISES_RAW_RESPONSE8 = '["qwe "rty <- asd fgh", "qwe rty <- zxc vbn"]'
