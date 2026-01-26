import pytest

import sys
sys.path.insert(0, "../")
from src.utils import NodeCreator, NodeType
from src.utils.data_structs import create_id


TEST_NODE_NAME = 'abc'
TEST_TIME = '12.12.2012'
STRING_PROP_VALUE = 'string_value'
INT_PROP_VALUE = 1001

@pytest.mark.parametrize("params, expected", [
    # добавить строковое представление в вершину
    ({'add_stringified_node': True, 'name': TEST_NODE_NAME, 'prop': {}}, {'str': TEST_NODE_NAME}),
    # не добавлять строковое представление в вершину
    ({'add_stringified_node': False, 'name': TEST_NODE_NAME, 'prop': {}}, {'str': TEST_NODE_NAME}),
    # строковое представление с отметкой времени
    ({'add_stringified_node': True, 'name': TEST_NODE_NAME, 'prop': {'time': TEST_TIME}}, {'str': f"{TEST_TIME}: {TEST_NODE_NAME}"}),
    # строковое представление без отметки времени
    ({'add_stringified_node': True, 'name': TEST_NODE_NAME, 'prop': {}}, {'str': TEST_NODE_NAME}),
    # строкое представление со свойствами
    ({'add_stringified_node': True, 'name': TEST_NODE_NAME, 'prop': {'p1': STRING_PROP_VALUE, 'p2': INT_PROP_VALUE}}, {'str': f"{TEST_NODE_NAME} (p1: {STRING_PROP_VALUE}; p2: {INT_PROP_VALUE})"}),
    # строкоове представление без свойств/имени
    ({'add_stringified_node': True, 'name': '', 'prop': {}}, {'str': ''}),
    # строковое представление со специальными свойствами
    ({'add_stringified_node': True, 'name': TEST_NODE_NAME, 'prop': {'name': STRING_PROP_VALUE, 'type': STRING_PROP_VALUE, 'raw_time': STRING_PROP_VALUE, 'time': TEST_TIME, 'str_id': STRING_PROP_VALUE}}, {'str': f"{TEST_TIME}: {TEST_NODE_NAME}"}),
])
def test_create_object_node(params, expected):
    node = NodeCreator.create(n_type=NodeType.object, **params)
    if params['add_stringified_node']:
        assert expected['str'] == node.stringified
    else:
        assert node.stringified is None

    assert node.id == create_id(NodeCreator.stringify(node)[1])

@pytest.mark.parametrize("params, expected", [
    # добавить строковое представление в вершину
    ({'add_stringified_node': True, 'name': TEST_NODE_NAME, 'prop': {}}, {'str': TEST_NODE_NAME}),
    # не добавлять строковое представление в вершину
    ({'add_stringified_node': False, 'name': TEST_NODE_NAME, 'prop': {}}, {'str': TEST_NODE_NAME}),
    # строковое представление с отметкой времени
    ({'add_stringified_node': True, 'name': TEST_NODE_NAME, 'prop': {'time': TEST_TIME}}, {'str': f"{TEST_TIME}: {TEST_NODE_NAME}"}),
    # строковое представление без отметки времени
    ({'add_stringified_node': True, 'name': TEST_NODE_NAME, 'prop': {}}, {'str': TEST_NODE_NAME}),
    # строкое представление со свойствами
    ({'add_stringified_node': True, 'name': TEST_NODE_NAME, 'prop': {'p1': STRING_PROP_VALUE, 'p2': INT_PROP_VALUE}}, {'str': f"{TEST_NODE_NAME} (p1: {STRING_PROP_VALUE}; p2: {INT_PROP_VALUE})"}),
    # строкоове представление без свойств/имени
    ({'add_stringified_node': True, 'name': '', 'prop': {}}, {'str': ''}),
    # строковое представление со специальными свойствами
    ({'add_stringified_node': True, 'name': TEST_NODE_NAME, 'prop': {'name': STRING_PROP_VALUE, 'type': STRING_PROP_VALUE, 'raw_time': STRING_PROP_VALUE, 'time': TEST_TIME, 'str_id': STRING_PROP_VALUE}}, {'str': f"{TEST_TIME}: {TEST_NODE_NAME}"}),
])
def test_create_thesis_node(params, expected):
    node = NodeCreator.create(n_type=NodeType.hyper, **params)
    if params['add_stringified_node']:
        assert expected['str'] == node.stringified
    else:
        assert node.stringified is None

    assert node.id == create_id(NodeCreator.stringify(node)[1])

@pytest.mark.parametrize("params, expected", [
    # добавить строковое представление в вершину
    ({'add_stringified_node': True, 'name': TEST_NODE_NAME, 'prop': {}}, {'str': TEST_NODE_NAME}),
    # не добавлять строковое представление в вершину
    ({'add_stringified_node': False, 'name': TEST_NODE_NAME, 'prop': {}}, {'str': TEST_NODE_NAME}),
    # строковое представление с отметкой времени
    ({'add_stringified_node': True, 'name': TEST_NODE_NAME, 'prop': {'time': TEST_TIME}}, {'str': f"{TEST_TIME}: {TEST_NODE_NAME}"}),
    # строковое представление без отметки времени
    ({'add_stringified_node': True, 'name': TEST_NODE_NAME, 'prop': {}}, {'str': TEST_NODE_NAME}),
    # строкое представление со свойствами
    ({'add_stringified_node': True, 'name': TEST_NODE_NAME, 'prop': {'p1': STRING_PROP_VALUE, 'p2': INT_PROP_VALUE}}, {'str': f"{TEST_NODE_NAME} (p1: {STRING_PROP_VALUE}; p2: {INT_PROP_VALUE})"}),
    # строкоове представление без свойств/имён
    ({'add_stringified_node': True, 'name': '', 'prop': {}}, {'str': ''}),
    # строковое представление со специальными свойствами
    ({'add_stringified_node': True, 'name': TEST_NODE_NAME, 'prop': {'name': STRING_PROP_VALUE, 'type': STRING_PROP_VALUE, 'raw_time': STRING_PROP_VALUE, 'time': TEST_TIME, 'str_id': STRING_PROP_VALUE}}, {'str': f"{TEST_TIME}: {TEST_NODE_NAME}"}),
])
def test_create_episodic_node(params, expected):
    node = NodeCreator.create(n_type=NodeType.episodic, **params)
    if params['add_stringified_node']:
        assert expected['str'] == node.stringified
    else:
        assert node.stringified is None

    assert node.id == create_id(NodeCreator.stringify(node)[1])
