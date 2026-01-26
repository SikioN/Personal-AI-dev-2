import pytest
from typing import List, Dict, Set

import sys
sys.path.insert(0, "../")

from src.utils import Triplet
from src.kg_model import GraphModel

from cases import GM_POPULATED_CREATE_TEST_CASES, GM_POPULATED_DELETE_TEST_CASES

@pytest.mark.parametrize("init_triplets, expected_init_count, expected_create_info, graph_model", GM_POPULATED_CREATE_TEST_CASES, indirect=['graph_model'])
def test_create_triplets(init_triplets: List[Triplet], expected_init_count: Dict[str, int],
                         expected_create_info: Dict[str, Set[str]], graph_model: GraphModel):
    graph_model.db_conn.clear()

    real_create_info = graph_model.create_triplets(init_triplets, batch_size=1)
    assert real_create_info == expected_create_info

    real_items_count = graph_model.count_items()
    assert real_items_count == expected_init_count

    for node_id in real_create_info['nodes']:
        assert graph_model.db_conn.item_exist(node_id, id_type='node')
    for triplet_id in real_create_info['triplets']:
        assert graph_model.db_conn.item_exist(triplet_id, id_type='triplet')

    for triplet in init_triplets:
        assert graph_model.db_conn.item_exist(triplet.start_node.id, id_type='node')
        assert graph_model.db_conn.item_exist(triplet.end_node.id, id_type='node')
        assert graph_model.db_conn.item_exist(triplet.id, id_type='triplet')
        assert graph_model.db_conn.item_exist(triplet.relation.id, id_type='relation')

@pytest.mark.parametrize("init_triplets, expected_create_info, expected_init_count, triplets_to_delete, expected_delete_ginfo, expected_final_count, expected_delete_vinfo, graph_model", GM_POPULATED_DELETE_TEST_CASES, indirect=['graph_model'])
def test_delete_triplets(init_triplets: List[Triplet], expected_create_info: Dict[str, Set[str]], expected_init_count: Dict[str, int],
                         triplets_to_delete: List[Triplet], expected_delete_ginfo: Dict[int, Dict[str, bool]],
                         expected_final_count: Dict[str, int], expected_delete_vinfo: Dict[int, Dict[str, bool]],
                         graph_model: GraphModel):
    graph_model.db_conn.clear()

    real_create_info = graph_model.create_triplets(init_triplets, batch_size=1)
    assert real_create_info == expected_create_info

    real_items_count = graph_model.count_items()
    assert real_items_count == expected_init_count

    real_gdb_dinfo, real_vdb_dinfo = graph_model.delete_triplets(triplets_to_delete)
    assert real_gdb_dinfo == expected_delete_ginfo
    assert real_vdb_dinfo == expected_delete_vinfo

    real_items_count = graph_model.count_items()
    assert real_items_count == expected_final_count

    for i, triplet in enumerate(triplets_to_delete):
        assert not graph_model.db_conn.item_exist(triplet.id, id_type='triplet')
        if real_gdb_dinfo[i]['s_node']:
            assert not graph_model.db_conn.item_exist(triplet.start_node.id, id_type='node')
        if real_gdb_dinfo[i]['e_node']:
            assert not graph_model.db_conn.item_exist(triplet.end_node.id, id_type='node')
