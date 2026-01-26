import pytest
from typing import List, Tuple, Dict, Union

import sys
# TO CHANGE
PROJECT_BASE_DIR = '../'
TEST_VOLUME_DIR = './volumes'
sys.path.insert(0, PROJECT_BASE_DIR)

from cases import TREEDB_POPULATED_CREATE_TEST_CASES, TREEDB_POPULATED_READ_TEST_CASES, \
    TREEDB_POPULATED_UPDATE_TEST_CASES, TREEDB_POPULATED_DELETE_TEST_CASES, \
        TREEDB_POPULATED_COUNT_TEST_CASES, TREEDB_POPULATED_EXIST_TEST_CASES, \
            TREEDB_POPULATED_CLEAR_TEST_CASES, TREEDB_POPULATED_GETCHILDS_TEST_CASES, TREEDB_POPULATED_GETMAXDEPTH_TEST_CASES, \
                TREEDB_POPULATED_GETLEAFDESCENDANTS_TEST_CASES

from src.utils import Triplet, RelationType, NodeType
from src.utils.data_structs import Node
from src.db_drivers.tree_driver.utils import AbstractTreeDatabaseConnection, TreeNode, TreeIdType

@pytest.mark.parametrize("parents_id, childs_data, exceptions, treedb_conn", TREEDB_POPULATED_CREATE_TEST_CASES, indirect=['treedb_conn'])
def test_create(parents_id: List[object], childs_data: List[TreeNode],
                exceptions: bool, treedb_conn: AbstractTreeDatabaseConnection):

    treedb_conn.clear()
    for parent_id, new_node, excep in zip(parents_id, childs_data, exceptions):
        try:
            treedb_conn.create(parent_id, new_node)
        except ValueError:
            assert excep
        else:
            assert not excep
            assert treedb_conn.item_exist(new_node.id, TreeIdType.external)

@pytest.mark.parametrize("create_pairs, read_ids, ids_type, expected, exception, treedb_conn", TREEDB_POPULATED_READ_TEST_CASES, indirect=['treedb_conn'])
def test_read(
    create_pairs: List[Tuple[str, TreeNode]], read_ids: List[object], exception: bool,
    ids_type: object, expected: Dict[str, TreeNode], treedb_conn: AbstractTreeDatabaseConnection):

    treedb_conn.clear()
    for pair in create_pairs:
        treedb_conn.create(pair[0], pair[1])

    try:
        real_output = treedb_conn.read(read_ids, ids_type)
    except ValueError:
        assert exception
    else:
        assert not exception
        assert len(real_output) == len(expected.values())
        for real_node in real_output:
            assert real_node.id in expected
            assert real_node.text == expected[real_node.id].text
            assert real_node.type == expected[real_node.id].type
            assert real_node.props == expected[real_node.id].props


@pytest.mark.parametrize("create_pairs, update_nodes, exception, treedb_conn", TREEDB_POPULATED_UPDATE_TEST_CASES, indirect=['treedb_conn'])
def test_update(
    create_pairs: List[Tuple[str, TreeNode]], update_nodes: List[TreeNode],
    exception: bool, treedb_conn: AbstractTreeDatabaseConnection):

    treedb_conn.clear()
    for pair in create_pairs:
        treedb_conn.create(pair[0], pair[1])

    try:
        treedb_conn.update(update_nodes)
    except ValueError:
        assert exception
    else:
        assert not exception
        for expected_node in update_nodes:
            real_node = treedb_conn.read([expected_node.id], ids_type=TreeIdType.external)[0]
            assert real_node.id in expected_node.id
            assert real_node.text == expected_node.text
            assert real_node.type == expected_node.type
            assert real_node.props == expected_node.props
            for k,v in expected_node.props.items():
                assert v == real_node.props[k]

@pytest.mark.parametrize("create_pairs, delete_ids, ids_type, exception, treedb_conn", TREEDB_POPULATED_DELETE_TEST_CASES, indirect=['treedb_conn'])
def test_delete(
    create_pairs: List[Tuple[str, TreeNode]], delete_ids: List[object],
    ids_type: object, exception: bool, treedb_conn: AbstractTreeDatabaseConnection):

    treedb_conn.clear()
    for pair in create_pairs:
        treedb_conn.create(pair[0], pair[1])

    try:
        treedb_conn.delete(delete_ids, ids_type)
    except ValueError:
        assert exception
    else:
        assert not exception
        for id in delete_ids:
            assert not treedb_conn.item_exist(id, id_type=ids_type)

@pytest.mark.parametrize("create_pairs, expected_count, treedb_conn", TREEDB_POPULATED_COUNT_TEST_CASES, indirect=['treedb_conn'])
def test_countitems(
    create_pairs: List[Tuple[str, TreeNode]], expected_count: Dict[str, int],
    treedb_conn: AbstractTreeDatabaseConnection):

    treedb_conn.clear()
    for pair in create_pairs:
        treedb_conn.create(pair[0], pair[1])

    real_count = treedb_conn.count_items()
    assert real_count['leaf'] == expected_count['leaf']
    assert real_count['summarized'] == expected_count['summarized']
    assert real_count['root'] == expected_count['root']

@pytest.mark.parametrize("create_pairs, node_id, id_type, exception, expected_value, treedb_conn", TREEDB_POPULATED_EXIST_TEST_CASES, indirect=['treedb_conn'])
def test_itemexist(
    create_pairs: List[Tuple[str, TreeNode]], node_id: object, id_type: object,
    exception: bool, expected_value: Union[bool, None], treedb_conn: AbstractTreeDatabaseConnection):

    treedb_conn.clear()

    for pair in create_pairs:
        treedb_conn.create(pair[0], pair[1])

    try:
        real_value = treedb_conn.item_exist(node_id, id_type)
    except ValueError:
        assert exception
    else:
        assert not exception
        assert real_value == expected_value

@pytest.mark.parametrize("create_pairs, expected_count, treedb_conn", TREEDB_POPULATED_CLEAR_TEST_CASES, indirect=['treedb_conn'])
def test_clear(
    create_pairs: List[Tuple[str, TreeNode]], expected_count: Dict[str, int],
    treedb_conn: AbstractTreeDatabaseConnection):

    treedb_conn.clear()
    real_count = treedb_conn.count_items()
    assert real_count['leaf'] == 0
    assert real_count['summarized'] == 0
    assert real_count['root'] == 1

    for pair in create_pairs:
        treedb_conn.create(pair[0], pair[1])

    real_count = treedb_conn.count_items()
    assert real_count['leaf'] == expected_count['leaf']
    assert real_count['summarized'] == expected_count['summarized']
    assert real_count['root'] == expected_count['root']

    treedb_conn.clear()

    real_count = treedb_conn.count_items()
    assert real_count['leaf'] == 0
    assert real_count['summarized'] == 0
    assert real_count['root'] == 1


@pytest.mark.parametrize("create_pairs, parent_id, expected_cnodes, exception, treedb_conn", TREEDB_POPULATED_GETCHILDS_TEST_CASES, indirect=['treedb_conn'])
def test_getchildnodes(
    create_pairs: List[Tuple[str, TreeNode]], parent_id: object, expected_cnodes: Dict[str, TreeNode],
    exception: bool, treedb_conn: AbstractTreeDatabaseConnection):

    treedb_conn.clear()
    for pair in create_pairs:
        treedb_conn.create(pair[0], pair[1])

    try:
        real_cnodes = treedb_conn.get_child_nodes(parent_id)
    except ValueError:
        assert exception
    else:
        assert not exception
        assert len(real_cnodes) == len(expected_cnodes.values())
        for real_node in real_cnodes:
            assert real_node.id in expected_cnodes
            assert real_node.text == expected_cnodes[real_node.id].text
            assert real_node.type == expected_cnodes[real_node.id].type
            assert real_node.props == expected_cnodes[real_node.id].props
            for k,v in expected_cnodes[real_node.id].props.items():
                assert v == real_node.props[k]


@pytest.mark.parametrize("create_pairs, expected_max_depth, treedb_conn", TREEDB_POPULATED_GETMAXDEPTH_TEST_CASES, indirect=['treedb_conn'])
def test_getmaxdepth(
    create_pairs: List[Tuple[str, TreeNode]], expected_max_depth: int, treedb_conn: AbstractTreeDatabaseConnection):

    treedb_conn.clear()
    for pair in create_pairs:
        treedb_conn.create(pair[0], pair[1])

    real_maxdepth = treedb_conn.get_tree_maxdepth()
    assert real_maxdepth == expected_max_depth

@pytest.mark.parametrize("create_pairs, id, expected_descendants, exception, treedb_conn", TREEDB_POPULATED_GETLEAFDESCENDANTS_TEST_CASES, indirect=['treedb_conn'])
def test_getleafdescendants(create_pairs: List[Tuple[str, TreeNode]], id: str, expected_descendants: Dict[str, TreeNode], exception: bool, treedb_conn: AbstractTreeDatabaseConnection):
    treedb_conn.clear()
    for pair in create_pairs:
        treedb_conn.create(pair[0], pair[1])

    try:
        real_descendants = treedb_conn.get_leaf_descendants(id, id_type=TreeIdType.external)
    except ValueError:
        assert exception
    else:
        assert not exception
        assert len(real_descendants) == len(expected_descendants.values())
        for real_node in real_descendants:
            assert real_node.id in expected_descendants
            assert real_node.text == expected_descendants[real_node.id].text
            assert real_node.type == expected_descendants[real_node.id].type
            assert real_node.props == expected_descendants[real_node.id].props
            for k,v in expected_descendants[real_node.id].props.items():
                assert v == real_node.props[k]