import pytest
from typing import List, Tuple, Dict, Union

import sys
# TO CHANGE
PROJECT_BASE_DIR = '../'
TEST_VOLUME_DIR = './volumes'
sys.path.insert(0, PROJECT_BASE_DIR)

from cases import GRAPHDB_POPULATED_CREATE_TEST_CASES, GRAPHDB_POPULATED_DELETE_TEST_CASES, \
    GRAPHDB_POPULATED_READ_TEST_CASES, GRAPHDB_POPULATED_COUNT_TEST_CASES, GRAPHDB_POPULATED_EXIST_TEST_CASES, \
    GRAPHDB_POPULATED_CLEAR_TEST_CASES, GRAPHDB_POPULATED_GET_TRIPLETS_TEST_CASES, GRAPHDB_POPULATED_GET_ADJECENT_TEST_CASES, \
        GRAPHDB_POPULATED_READ_BY_NAME_TEST_CASES, GRAPHDB_POPULATED_GET_NSHARED_IDS_TEST_CASES

from src.utils import Triplet, RelationType, NodeType
from src.utils.data_structs import Node
from src.db_drivers.graph_driver.utils import AbstractGraphDatabaseConnection

@pytest.mark.parametrize("inputs, create_info, expected, graphdb_conn", GRAPHDB_POPULATED_CREATE_TEST_CASES, indirect=['graphdb_conn'])
def test_create(inputs, create_info, expected, graphdb_conn):
    graphdb_conn.clear()

    try:
        for inp, info in zip(inputs, create_info):
            graphdb_conn.create(inp, info)
    except Exception as e:
        print(str(e))
        assert expected['exception']
    else:
        assert not expected['exception']

    items_info = graphdb_conn.count_items()
    assert items_info['triplets'] == expected['triplets_count']
    assert items_info['nodes'] == expected['nodes_count']

@pytest.mark.parametrize("instances, create_info, inputs, expected, graphdb_conn", GRAPHDB_POPULATED_READ_TEST_CASES, indirect=['graphdb_conn'])
def test_read(instances, create_info, inputs, expected, graphdb_conn):
    graphdb_conn.clear()
    graphdb_conn.create(instances, create_info)

    try:
        output = graphdb_conn.read(inputs)
    except ValueError as e:
        print(str(e))
        assert expected['exception']
    else:
        assert not expected['exception']

    if not expected['exception']:
        print(output)
        assert len(output) == len(expected['output_ids'])
        assert set(map(lambda item: item.id, output)) == expected['output_ids']


@pytest.mark.parametrize("instances, create_info, inputs, delete_info, expected, graphdb_conn", GRAPHDB_POPULATED_DELETE_TEST_CASES, indirect=['graphdb_conn'])
def test_delete(instances, create_info, inputs, delete_info, expected, graphdb_conn):
    graphdb_conn.clear()
    graphdb_conn.create(instances, create_info)

    try:
        graphdb_conn.delete(inputs, delete_info)
    except ValueError as e:
        print(str(e))
        assert expected['exception']
    else:
        assert not expected['exception']

    items_info = graphdb_conn.count_items()
    assert items_info['triplets'] == expected['triplets_count']
    assert items_info['nodes'] == expected['nodes_count']

@pytest.mark.parametrize("instances, create_info, expected, graphdb_conn", GRAPHDB_POPULATED_COUNT_TEST_CASES, indirect=['graphdb_conn'])
def test_count(instances, create_info, expected, graphdb_conn):
    graphdb_conn.clear()
    graphdb_conn.create(instances, create_info)

    items_info = graphdb_conn.count_items()
    assert items_info['triplets'] == expected['triplets_count']
    assert items_info['nodes'] == expected['nodes_count']

@pytest.mark.parametrize("instances, inputs, expected, graphdb_conn", GRAPHDB_POPULATED_EXIST_TEST_CASES, indirect=['graphdb_conn'])
def test_exist(instances, inputs, expected, graphdb_conn):
    graphdb_conn.clear()
    graphdb_conn.create(instances)

    try:
        real = graphdb_conn.item_exist(inputs, expected['type'])
    except ValueError as e:
        print(str(e))
        assert expected['exception']
    else:
        assert not expected['exception']

    if not expected['exception']:
        assert real == expected['exist']


@pytest.mark.parametrize("instances, base_info, graphdb_conn", GRAPHDB_POPULATED_CLEAR_TEST_CASES, indirect=['graphdb_conn'])
def test_clear(instances, base_info, graphdb_conn):
    graphdb_conn.clear()
    graphdb_conn.create(instances)

    items_info = graphdb_conn.count_items()
    assert items_info['triplets'] == base_info['triplets_count']
    assert items_info['nodes'] == base_info['nodes_count']

    graphdb_conn.clear()

    items_info = graphdb_conn.count_items()
    assert items_info['triplets'] == 0
    assert items_info['nodes'] == 0

@pytest.mark.parametrize("instances, create_info, node, accepted_n_types, expected, graphdb_conn", GRAPHDB_POPULATED_GET_ADJECENT_TEST_CASES, indirect=['graphdb_conn'])
def test_get_adjecent_nids(instances, create_info, node, accepted_n_types, expected, graphdb_conn):
    graphdb_conn.clear()
    graphdb_conn.create(instances, create_info)

    try:
        output = graphdb_conn.get_adjecent_nids(node, accepted_n_types=accepted_n_types)
    except ValueError as e:
        print(str(e))
        assert expected['exception']
    else:
        assert not expected['exception']
        assert expected['output_ids'] == set(output)

@pytest.mark.parametrize("instances, create_info, nodes, expected, graphdb_conn", GRAPHDB_POPULATED_GET_TRIPLETS_TEST_CASES, indirect=['graphdb_conn'])
def test_get_triplets(instances: List[Triplet], create_info: Dict, nodes: List[str],
                      expected: Dict, graphdb_conn: AbstractGraphDatabaseConnection):
    graphdb_conn.clear()
    graphdb_conn.create(instances, create_info)

    if expected['exist'][0] is not None:
        assert graphdb_conn.item_exist(nodes[0],id_type='node') == expected['exist'][0]
    if expected['exist'][1] is not None:
        assert graphdb_conn.item_exist(nodes[1],id_type='node') == expected['exist'][1]

    try:
        output = graphdb_conn.get_triplets(*nodes)
    except ValueError as e:
        print(str(e))
        assert expected['exception']
    else:
        assert not expected['exception']

        items_info = graphdb_conn.count_items()
        assert items_info['triplets'] == expected['triplets']
        assert items_info['nodes'] == expected['nodes']

        assert expected['output_ids'] == set(list(map(lambda triplet: triplet.id, output)))
        assert expected['count'] == len(output)

@pytest.mark.parametrize("instances, create_info, init_count, name, type, object, expected_output, exception, graphdb_conn", GRAPHDB_POPULATED_READ_BY_NAME_TEST_CASES, indirect=['graphdb_conn'])
def test_read_by_name(instances: List[Triplet], create_info: Dict, init_count: Dict, name: str,
                      type: Union[RelationType,NodeType], object: str, expected_output: List[Union[Triplet,Node]],
                      exception: bool, graphdb_conn: AbstractGraphDatabaseConnection):
    graphdb_conn.clear()
    graphdb_conn.create(instances, create_info)

    items_info = graphdb_conn.count_items()
    assert items_info['triplets'] == init_count['triplets']
    assert items_info['nodes'] == init_count['nodes']

    try:
        real_output = graphdb_conn.read_by_name(name, type, object)
    except ValueError as e:
        print(str(e))
        assert exception
    else:
        assert not exception

        assert len(real_output) == len(expected_output)
        if object == 'relation':
            expec_t_ids = set([item.id for item in expected_output])
            for real_t in real_output:
                assert real_t.relation.name == name
                assert real_t.relation.type == type
                assert real_t.id in expec_t_ids

        elif object == 'node':
            expec_n_ids = set([item.id for item in expected_output])
            for real_n in real_output:
                assert real_n.name == name
                assert real_n.type == type
                assert real_n.id in expec_n_ids

        else:
            raise ValueError

@pytest.mark.parametrize("instances, create_info, graph_info, node1_id, node2_id, id_type, expected_output, exception, graphdb_conn",
                         GRAPHDB_POPULATED_GET_NSHARED_IDS_TEST_CASES, indirect=['graphdb_conn'])
def test_get_nodes_shared_ids(
    instances: List[Triplet], create_info: Dict, graph_info: Tuple[int], node1_id: str, node2_id: str, id_type: str,
    expected_output: List[Dict[str,str]], exception: bool, graphdb_conn: AbstractGraphDatabaseConnection):
    graphdb_conn.clear()
    graphdb_conn.create(instances, create_info)

    real_ginfo =graphdb_conn.count_items()
    assert real_ginfo['triplets'] == graph_info[0]
    assert real_ginfo['nodes'] == graph_info[1]

    try:
        real_output = graphdb_conn.get_nodes_shared_ids(node1_id, node2_id, id_type)
    except ValueError:
        assert exception
    else:
        assert not exception

        if id_type == 'both':
            expected_ids = set(map(lambda p: (p['t_id'],p['r_id']), expected_output))
            real_ids = set(map(lambda p: (p['t_id'],p['r_id']), real_output))
            assert expected_ids == real_ids

        elif id_type == 'triplet':
            expected_t_ids = set(map(lambda p: p['t_id'], expected_output))
            real_t_ids = set(map(lambda p: p['t_id'], real_output))
            assert expected_t_ids == real_t_ids

        elif id_type  == 'relation':
            expected_r_ids = set(map(lambda p: p['r_id'], expected_output))
            real_r_ids = set(map(lambda p: p['r_id'], real_output))
            assert expected_r_ids == real_r_ids

        else:
            raise ValueError(id_type)
