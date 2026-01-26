import pytest
import hashlib
from typing import Dict

import sys
sys.path.insert(0, "../")
from src.utils.data_structs import TripletCreator, NodeCreator, RelationCreator, \
    Node, Relation, Triplet, NodeType, RelationType, create_id

STRING_PROP_VALUE = 'string_value'
INT_PROP_VALUE = 1001
TEST_TIME = '12.12.2012'
TEST_NODE_NAME = 'abc'
TEST_REL_NAME = 'def'
TEST_ID = 'id123'

TEST_PROPS_WITH_TIME = {'time': TEST_TIME}
TEST_PROPS_WO_TIME = {'p1': STRING_PROP_VALUE, 'p2': INT_PROP_VALUE}
TEST_PROPS_WITH_SPECIAL = {
    'name': STRING_PROP_VALUE, 'type': STRING_PROP_VALUE, 'raw_time': STRING_PROP_VALUE,
    'time': TEST_TIME, 'str_id': STRING_PROP_VALUE}

###################

TEST_OBJECT_NODE = NodeCreator.create(name=TEST_NODE_NAME, n_type=NodeType.object)

TEST_EXPECTED_SIMPLE_TRIPLET_STR1 = f'{TEST_NODE_NAME} {TEST_REL_NAME} {TEST_NODE_NAME}'
TEST_EXPECTED_SIMPLE_TRIPLET_WITH_TIME_STR2 = f'{TEST_TIME}: {TEST_EXPECTED_SIMPLE_TRIPLET_STR1}'
TEST_EXPECTED_SIMPLE_TRIPLET_STR3 = f'{TEST_NODE_NAME} {TEST_REL_NAME} (p1: {STRING_PROP_VALUE}; p2: {INT_PROP_VALUE}) {TEST_NODE_NAME}'
TEST_EXPECTED_SIMPLE_TRIPLET_STR4 = f'{TEST_NODE_NAME}  {TEST_NODE_NAME}'

@pytest.mark.parametrize("params, expected", [
    # сохранить строковое представление в триплете
    ({'sn': TEST_OBJECT_NODE, 'en': TEST_OBJECT_NODE, 'r_name': TEST_REL_NAME, 'r_prop': dict(), 'id': None, 's_str': True}, {'str': TEST_EXPECTED_SIMPLE_TRIPLET_STR1}),
    # не сохранять строковое представление в триплете
    ({'sn': TEST_OBJECT_NODE, 'en': TEST_OBJECT_NODE, 'r_name': TEST_REL_NAME, 'r_prop': dict(), 'id': None, 's_str': False}, {'str': None}),
    # назначить собственный идентификатор триплету
    ({'sn': TEST_OBJECT_NODE, 'en': TEST_OBJECT_NODE, 'r_name': TEST_REL_NAME, 'r_prop': dict(), 'id': TEST_ID, 's_str': False}, {'str': None}),
    # строковое представление с отметкой времени
    ({'sn': TEST_OBJECT_NODE, 'en': TEST_OBJECT_NODE, 'r_name': TEST_REL_NAME, 'r_prop': TEST_PROPS_WITH_TIME, 'id': None, 's_str': True}, {'str': TEST_EXPECTED_SIMPLE_TRIPLET_WITH_TIME_STR2}),
    # строкое представление со свойствами
    ({'sn': TEST_OBJECT_NODE, 'en': TEST_OBJECT_NODE, 'r_name': TEST_REL_NAME, 'r_prop': TEST_PROPS_WO_TIME, 'id': None, 's_str': True}, {'str': TEST_EXPECTED_SIMPLE_TRIPLET_STR3}),
    # строкоове представление без свойств/имён
    ({'sn': TEST_OBJECT_NODE, 'en': TEST_OBJECT_NODE, 'r_name': '', 'r_prop': dict(), 'id': None, 's_str': True}, {'str': TEST_EXPECTED_SIMPLE_TRIPLET_STR4}),
    # строковое представление со специальными свойствами
    ({'sn': TEST_OBJECT_NODE, 'en': TEST_OBJECT_NODE, 'r_name': TEST_REL_NAME, 'r_prop': TEST_PROPS_WITH_SPECIAL, 'id': None, 's_str': True}, {'str': TEST_EXPECTED_SIMPLE_TRIPLET_WITH_TIME_STR2}),
])
def test_create_simple_triplet(params, expected):
    rel = Relation(name=params['r_name'], prop=params['r_prop'], type=RelationType.simple)
    triplet = TripletCreator.create(
        start_node=params['sn'], relation=rel,
        end_node=params['en'], add_stringified_triplet=params['s_str'],
        t_id=params['id'])

    if params['id'] is not None:
        assert triplet.id == params['id']
    else:
        assert triplet.id == create_id(''.join([triplet.start_node.id, triplet.relation.id, triplet.end_node.id]))

    assert triplet.relation.id == create_id(TripletCreator.stringify(triplet)[1])

    if params['s_str']:
        assert expected['str'] == triplet.stringified
    else:
        assert triplet.stringified is None

###################

TEST_THESIS_NODE1 = NodeCreator.create(name=TEST_NODE_NAME, n_type=NodeType.hyper)
TEST_THESIS_NODE2 = NodeCreator.create(name=TEST_NODE_NAME, n_type=NodeType.hyper, prop=TEST_PROPS_WITH_TIME)
TEST_THESIS_NODE3 = NodeCreator.create(name=TEST_NODE_NAME, n_type=NodeType.hyper, prop=TEST_PROPS_WO_TIME)
TEST_THESIS_NODE4 = NodeCreator.create(name=TEST_NODE_NAME, n_type=NodeType.hyper, prop=TEST_PROPS_WITH_SPECIAL)

TEST_EXPECTED_HYPER_TRIPLET_STR1 = f"{TEST_NODE_NAME}"
TEST_EXPECTED_HYPER_TRIPLET_STR2 = f"{TEST_TIME}: {TEST_NODE_NAME}"
TEST_EXPECTED_HYPER_TRIPLET_STR3 = f"{TEST_EXPECTED_HYPER_TRIPLET_STR1} (p1: {STRING_PROP_VALUE}; p2: {INT_PROP_VALUE})"

@pytest.mark.parametrize("params, expected", [
    # сохранить строковое представление в триплете
    ({'sn': TEST_OBJECT_NODE, 'en': TEST_THESIS_NODE1, 'r_name': TEST_REL_NAME, 'r_prop': dict(), 'id': None, 's_str': True}, {'str': TEST_EXPECTED_HYPER_TRIPLET_STR1}),
    # не сохранять строковое представление в триплете
    ({'sn': TEST_OBJECT_NODE, 'en': TEST_THESIS_NODE1, 'r_name': TEST_REL_NAME, 'r_prop': dict(), 'id': None, 's_str': False}, {'str': None}),
    # назначить собственный идентификатор триплету
    ({'sn': TEST_OBJECT_NODE, 'en': TEST_THESIS_NODE1, 'r_name': TEST_REL_NAME, 'r_prop': dict(), 'id': TEST_ID, 's_str': False}, {'str': None}),
    # строковое представление с отметкой времени
    ({'sn': TEST_OBJECT_NODE, 'en': TEST_THESIS_NODE2, 'r_name': TEST_REL_NAME, 'r_prop': TEST_PROPS_WO_TIME, 'id': None, 's_str': True}, {'str': TEST_EXPECTED_HYPER_TRIPLET_STR2}),
    # строкое представление со свойствами
    ({'sn': TEST_OBJECT_NODE, 'en': TEST_THESIS_NODE3, 'r_name': TEST_REL_NAME, 'r_prop': TEST_PROPS_WO_TIME, 'id': None, 's_str': True}, {'str': TEST_EXPECTED_HYPER_TRIPLET_STR3}),
    # строкоове представление без свойств/имён
    ({'sn': TEST_OBJECT_NODE, 'en': TEST_THESIS_NODE1, 'r_name': '', 'r_prop': dict(), 'id': None, 's_str': True}, {'str': TEST_EXPECTED_HYPER_TRIPLET_STR1}),
    # строковое представление со специальными свойствами
    ({'sn': TEST_OBJECT_NODE, 'en': TEST_THESIS_NODE4, 'r_name': TEST_REL_NAME, 'r_prop': TEST_PROPS_WITH_SPECIAL, 'id': None, 's_str': True}, {'str': TEST_EXPECTED_HYPER_TRIPLET_STR2}),
])
def test_create_hyper_triplet(params, expected):
    rel = Relation(name=params['r_name'], prop=params['r_prop'], type=RelationType.hyper)
    triplet = TripletCreator.create(
        start_node=params['sn'], relation=rel,
        end_node=params['en'], add_stringified_triplet=params['s_str'],
        t_id=params['id'])

    if params['id'] is not None:
        assert triplet.id == params['id']
    else:
        assert triplet.id == create_id(''.join([triplet.start_node.id, triplet.relation.id, triplet.end_node.id]))

    assert triplet.relation.id == create_id(TripletCreator.stringify(triplet)[1])

    if params['s_str']:
        assert expected['str'] == triplet.stringified
    else:
        assert triplet.stringified is None

###################

TEST_EPISODIC_NODE1 = NodeCreator.create(name=TEST_NODE_NAME, n_type=NodeType.episodic)
TEST_EPISODIC_NODE2 = NodeCreator.create(name=TEST_NODE_NAME, n_type=NodeType.episodic, prop=TEST_PROPS_WITH_TIME)
TEST_EPISODIC_NODE3 = NodeCreator.create(name=TEST_NODE_NAME, n_type=NodeType.episodic, prop=TEST_PROPS_WO_TIME)
TEST_EPISODIC_NODE4 = NodeCreator.create(name=TEST_NODE_NAME, n_type=NodeType.episodic, prop=TEST_PROPS_WITH_SPECIAL)

TEST_EXPECTED_EPISODIC_TRIPLET_STR1 = f"{TEST_NODE_NAME}"
TEST_EXPECTED_EPISODIC_TRIPLET_STR2 = f"{TEST_TIME}: {TEST_NODE_NAME}"
TEST_EXPECTED_EPISODIC_TRIPLET_STR3 = f"{TEST_EXPECTED_EPISODIC_TRIPLET_STR1} (p1: {STRING_PROP_VALUE}; p2: {INT_PROP_VALUE})"

@pytest.mark.parametrize("params, expected", [
    # сохранить строковое представление в триплете
    ({'sn': TEST_OBJECT_NODE, 'en': TEST_EPISODIC_NODE1, 'r_name': TEST_REL_NAME, 'r_prop': dict(), 'id': None, 's_str': True}, {'str': TEST_EXPECTED_EPISODIC_TRIPLET_STR1}),
    # не сохранять строковое представление в триплете
    ({'sn': TEST_OBJECT_NODE, 'en': TEST_EPISODIC_NODE1, 'r_name': TEST_REL_NAME, 'r_prop': dict(), 'id': None, 's_str': False}, {'str': None}),
    # назначить собственный идентификатор триплету
    ({'sn': TEST_OBJECT_NODE, 'en': TEST_EPISODIC_NODE1, 'r_name': TEST_REL_NAME, 'r_prop': dict(), 'id': TEST_ID, 's_str': False}, {'str': None}),
    # строковое представление с отметкой времени
    ({'sn': TEST_OBJECT_NODE, 'en': TEST_EPISODIC_NODE2, 'r_name': TEST_REL_NAME, 'r_prop': TEST_PROPS_WO_TIME, 'id': None, 's_str': True}, {'str': TEST_EXPECTED_EPISODIC_TRIPLET_STR2}),
    # строкое представление со свойствами
    ({'sn': TEST_OBJECT_NODE, 'en': TEST_EPISODIC_NODE3, 'r_name': TEST_REL_NAME, 'r_prop': TEST_PROPS_WO_TIME, 'id': None, 's_str': True}, {'str': TEST_EXPECTED_EPISODIC_TRIPLET_STR3}),
    # строкоове представление без свойств/имён
    ({'sn': TEST_OBJECT_NODE, 'en': TEST_EPISODIC_NODE1, 'r_name': '', 'r_prop': dict(), 'id': None, 's_str': True}, {'str': TEST_EXPECTED_EPISODIC_TRIPLET_STR1}),
    # строковое представление со специальными свойствами
    ({'sn': TEST_OBJECT_NODE, 'en': TEST_EPISODIC_NODE4, 'r_name': TEST_REL_NAME, 'r_prop': TEST_PROPS_WITH_SPECIAL, 'id': None, 's_str': True}, {'str': TEST_EXPECTED_EPISODIC_TRIPLET_STR2}),
])
def test_create_episodic_triplet(params, expected):
    rel = Relation(name=params['r_name'], prop=params['r_prop'], type=RelationType.episodic)
    triplet = TripletCreator.create(
        start_node=params['sn'], relation=rel,
        end_node=params['en'], add_stringified_triplet=params['s_str'],
        t_id=params['id'])

    if params['id'] is not None:
        assert triplet.id == params['id']
    else:
        assert triplet.id == create_id(''.join([triplet.start_node.id, triplet.relation.id, triplet.end_node.id]))

    assert triplet.relation.id == create_id(TripletCreator.stringify(triplet)[1])

    if params['s_str']:
        assert expected['str'] == triplet.stringified
    else:
        assert triplet.stringified is None


NODE_OBJECT_EMPTY_PROP = NodeCreator.create(n_type=NodeType.object, name='qwe')
NODE_OBJECT_FULL_PROP = NodeCreator.create(n_type=NodeType.object, name='rty', prop={'k1': 'v1'})

RELATION_SIMPLE_EMPTY_PROP = RelationCreator.create(r_type=RelationType.simple, name='uio')

TRIPLET_EMPTY_PROP = TripletCreator.create(
    start_node=NODE_OBJECT_EMPTY_PROP,
    relation=RELATION_SIMPLE_EMPTY_PROP,
    end_node=NODE_OBJECT_EMPTY_PROP)

NODE_OBJECT_OMITED_PROP = {'name': 'qwe', 'type': 'object'}
NODE_HYPER_OMITED_PROP = {'name': 'qwe', 'type': 'hyper'}
NODE_EPISODIC_OMITED_PROP = {'name': 'qwe', 'type': 'episodic'}

NODE_OBJECT_OMITED_NAME = {'type': 'object'}
NODE_HYPER_OMITED_NAME = {'type': 'hyper'}
NODE_EPISODIC_OMITED_NAME = {'type': 'episodic'}
NODE_OBJECT_OMITED_TYPE = {'name': 'qwe'}
NODE_OBJECT_BAD_TYPE = {'name': 'qwe', 'type': 'unknown_type'}

RELATION_SIMPLE_OMITED_PROP = {'name': 'uio', 'type': 'simple'}
RELATION_SIMPLE_OMITED_NAME = {'type': 'simple'}
RELATION_HYPER_OMITED_NAME = {'type': 'hyper'}
RELATION_EPISODIC_OMITED_NAME = {'type': 'episodic'}
RELATION_SIMPLE_OMITED_TYPE = {'name':'qwe'}
RELATION_SIMPLE_BAD_TYPE = {'name': 'qwe', 'type': 'unknown_type'}

TRIPLET_HYPER_WITH_OMITED_NAME = TripletCreator.create(
    start_node=NodeCreator.create(name=NODE_OBJECT_OMITED_PROP['name'],n_type=NODE_OBJECT_OMITED_PROP['type'],),
    relation=RelationCreator.create(r_type=RELATION_HYPER_OMITED_NAME['type']),
    end_node=NodeCreator.create(name=NODE_HYPER_OMITED_PROP['name'],n_type=NODE_HYPER_OMITED_PROP['type']))

TRIPLET_EPISODIC_WITH_OMITED_NAME = TripletCreator.create(
    start_node=NodeCreator.create(name=NODE_OBJECT_OMITED_PROP['name'],n_type=NODE_OBJECT_OMITED_PROP['type'],),
    relation=RelationCreator.create(r_type=RELATION_EPISODIC_OMITED_NAME['type']),
    end_node=NodeCreator.create(name=NODE_EPISODIC_OMITED_PROP['name'],n_type=NODE_EPISODIC_OMITED_PROP['type']))

@pytest.mark.parametrize("json_triplet, expected_triplet, exception", [
    # 1. в subject
    # 1.1. не заполнено prop-поле
    ({'subject': NODE_OBJECT_OMITED_PROP, 'relation': RELATION_SIMPLE_OMITED_PROP, 'object': NODE_OBJECT_OMITED_PROP}, TRIPLET_EMPTY_PROP, False),
    # 1.2. не заполнено name-поле
    # 1.2.1 type = 'object'
    ({'subject': NODE_OBJECT_OMITED_NAME, 'relation': RELATION_SIMPLE_OMITED_PROP, 'object': NODE_OBJECT_OMITED_PROP}, None, True),
    # 1.2.2 type = 'hyper'
    ({'subject': NODE_HYPER_OMITED_NAME, 'relation': RELATION_SIMPLE_OMITED_PROP, 'object': NODE_OBJECT_OMITED_PROP}, None, True),
    # 1.2.3 type = 'episodic'
    ({'subject': NODE_EPISODIC_OMITED_NAME, 'relation': RELATION_SIMPLE_OMITED_PROP, 'object': NODE_OBJECT_OMITED_PROP}, None, True),
    # 1.3. не заполнено type-поле
    ({'subject': NODE_OBJECT_OMITED_TYPE, 'relation': RELATION_SIMPLE_OMITED_PROP, 'object': NODE_OBJECT_OMITED_PROP}, None, True),
    # 1.4. указано невалидное значение в type-поле
    ({'subject': NODE_OBJECT_BAD_TYPE, 'relation': RELATION_SIMPLE_OMITED_PROP, 'object': NODE_OBJECT_OMITED_PROP}, None, True),
    # 2. В relation
    # 2.1. пустое prop-поле
    ({'subject': NODE_OBJECT_OMITED_PROP, 'relation': RELATION_SIMPLE_OMITED_PROP, 'object': NODE_OBJECT_OMITED_PROP}, TRIPLET_EMPTY_PROP, False),
    # 2.2. не заполнено name-поле
    # 2.2.1 type = 'simple'
    ({'subject': NODE_OBJECT_OMITED_PROP, 'relation': RELATION_SIMPLE_OMITED_NAME, 'object': NODE_OBJECT_OMITED_PROP,}, None, True),
    # 2.2.2 type = 'hyper'
    ({'subject': NODE_OBJECT_OMITED_PROP, 'relation': RELATION_HYPER_OMITED_NAME, 'object': NODE_HYPER_OMITED_PROP}, TRIPLET_HYPER_WITH_OMITED_NAME, False),
    # 2.2.3 type = 'episodic'
    ({'subject': NODE_OBJECT_OMITED_PROP, 'relation': RELATION_EPISODIC_OMITED_NAME, 'object': NODE_EPISODIC_OMITED_PROP}, TRIPLET_EPISODIC_WITH_OMITED_NAME, False),
    # 2.3. не заполнено type-поле
    ({'subject': NODE_OBJECT_OMITED_PROP, 'relation': RELATION_SIMPLE_OMITED_TYPE, 'object': NODE_OBJECT_OMITED_PROP}, None, True),
    # 2.4. указано невалидное значение в type-поле
    ({'subject': NODE_OBJECT_OMITED_PROP, 'relation': RELATION_SIMPLE_BAD_TYPE, 'object': NODE_OBJECT_OMITED_PROP,}, None, True),
    # 3. В object
    # 3.1. пустое prop-поле
    ({'subject': NODE_OBJECT_OMITED_PROP, 'relation': RELATION_SIMPLE_OMITED_PROP, 'object': NODE_OBJECT_OMITED_PROP}, TRIPLET_EMPTY_PROP, False),
    # 3.2. не заполнено name-поле
    # 3.2.1 type = 'object'
    ({'subject': NODE_OBJECT_OMITED_PROP, 'relation': RELATION_SIMPLE_OMITED_PROP, 'object': NODE_OBJECT_OMITED_NAME}, None, True),
    # 3.2.2 type = 'hyper'
    ({'subject': NODE_OBJECT_OMITED_PROP, 'relation': RELATION_SIMPLE_OMITED_PROP, 'object': NODE_HYPER_OMITED_NAME}, None, True),
    # 3.2.3 type = 'episodic'
    ({'subject': NODE_OBJECT_OMITED_PROP, 'relation': RELATION_SIMPLE_OMITED_PROP, 'object': NODE_EPISODIC_OMITED_NAME}, None, True),
    # 3.3. не заполнено type-поле
    ({'subject': NODE_OBJECT_OMITED_PROP, 'relation': RELATION_SIMPLE_OMITED_PROP, 'object': NODE_OBJECT_OMITED_TYPE}, None, True),
    # 3.4. указано невалидное значение в type-поле
   ({'subject': NODE_OBJECT_OMITED_PROP, 'relation': RELATION_SIMPLE_OMITED_PROP, 'object': NODE_OBJECT_BAD_TYPE}, None, True),
])
def test_create_from_json(json_triplet: Dict, expected_triplet: Triplet, exception: bool):
    try:
        real_triplet = TripletCreator.from_json(json_triplet)
    except (ValueError, KeyError) as e:
        assert exception
    else:
        assert not exception

    if not exception:
        assert real_triplet.id == expected_triplet.id

        assert real_triplet.start_node.id == expected_triplet.start_node.id
        assert real_triplet.start_node.name == expected_triplet.start_node.name
        assert real_triplet.start_node.type == expected_triplet.start_node.type
        assert real_triplet.start_node.prop == expected_triplet.start_node.prop

        assert real_triplet.end_node.id == expected_triplet.end_node.id
        assert real_triplet.end_node.name == expected_triplet.end_node.name
        assert real_triplet.end_node.type == expected_triplet.end_node.type
        assert real_triplet.end_node.prop == expected_triplet.end_node.prop

        assert real_triplet.relation.id == expected_triplet.relation.id
        assert real_triplet.relation.name == expected_triplet.relation.name
        assert real_triplet.relation.type == expected_triplet.relation.type
        assert real_triplet.relation.prop == expected_triplet.relation.prop
