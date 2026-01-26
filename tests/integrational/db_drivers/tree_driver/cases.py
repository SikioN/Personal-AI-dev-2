import pytest
from typing import List, Tuple, Dict, Union

import sys
# TO CHANGE
PROJECT_BASE_DIR = '../'
sys.path.insert(0, PROJECT_BASE_DIR)

from src.db_drivers.tree_driver.utils import TreeNode, TreeNodeType, TreeIdType

# TO CHANGE
AVAILABLE_TREE_DBS = ['neo4j']

################################################################

VALID_SUM_TNODE1 = TreeNode(id='123', text='qwe', type=TreeNodeType.summarized, props={'p1': 'k1', 'depth': 1})
VALID_SUM_TNODE2 = TreeNode(id='234', text='asd', type=TreeNodeType.summarized, props={'p2': 'k2', 'depth': 1})
VALID_SUM_TNODE3 = TreeNode(id='rgn', text='dggg', type=TreeNodeType.summarized, props={'p3': 'k3', 'depth': 1})
VALID_SUM_TNODE4 = TreeNode(id='ytjetmf', text='jrtdnf', type=TreeNodeType.summarized, props={'p4': 'k4', 'depth': 1})
VALID_SUM_TNODE5 = TreeNode(id='sthbsfd', text='tendg', type=TreeNodeType.summarized, props={'p5': 'k5', 'depth': 2})
VALID_SUM_TNODE6 = TreeNode(id='rthbdvae', text='sbfbsrga', type=TreeNodeType.summarized, props={'p6': 'k6', 'depth': 3})
VALID_SUM_TNODE7 = TreeNode(id='yurkjda', text='sdfzbnts', type=TreeNodeType.summarized, props={'p7': 'k7', 'depth': 2})
VALID_SUM_TNODE8 = TreeNode(id='dfvsdjtrtj', text='sxbfagrscv', type=TreeNodeType.summarized, props={'p8': 'k8', 'depth': 2})

VALID_LEAF_TNODE1 = TreeNode(id='456', text='zxc', type=TreeNodeType.leaf, props={'p1': 'k1', 'str_id': 'th5h6', 'depth': 2})
VALID_LEAF_TNODE2 = TreeNode(id='756', text='wer', type=TreeNodeType.leaf, props={'p2': 'k2', 'str_id': 'ltutjgh', 'depth': 2})
VALID_LEAF_TNODE3 = TreeNode(id='hrtsfdb', text='agrdv', type=TreeNodeType.leaf, props={'p3': 'k3', 'str_id': 'sbdvfvaa', 'depth': 2})
VALID_LEAF_TNODE4 = TreeNode(id='hbtrvv', text='sdgdbar', type=TreeNodeType.leaf, props={'p4': 'k4', 'str_id': 'lagervfdbfd', 'depth': 2})

INVALID_LEAF_TNODE1 = TreeNode(id=123, text='dfhdf', type=TreeNodeType.leaf, props={'p3': 'k5'})
INVALID_LEAF_TNODE2 = TreeNode(id="636", text='dfhdf', type="leaf", props={'p3': 'k5'})
INVALID_LEAF_TNODE3 = TreeNode(id="636", text=123, type=TreeNodeType.leaf, props={'p3': 'k5'})
INVALID_LEAF_TNODE4 = TreeNode(id="636", text="123", type=TreeNodeType.leaf, props={123: 'k5'})
INVALID_LEAF_TNODE5 = TreeNode(id="636", text="123", type=TreeNodeType.leaf, props={"external_id": '636'})

UPDATE_SUM_TNODE1 = TreeNode(id='123', text='qwe qwe', type=TreeNodeType.summarized, props={'p1new': 'k1new'})
UPDATE_LEAF_TNODE1 = TreeNode(id='456', text='zxc zxc', type=TreeNodeType.leaf, props={'p1new': 'k1new', 'str_id': 'th5h6'})
UPDATE_LEAF_TNODE1_TO_SUMM = TreeNode(id='456', text='zxc zxc rfv', type=TreeNodeType.summarized, props={'p1_1new': 'k1_1new'})

UPDATE_INVALID_LEAF_TNODE1 = TreeNode(id='456', text='zxc zxc', type='leaf', props={'p1new': 'k1new', 'str_id': 'th5h6'})
UPDATE_INVALID_LEAF_TNODE2 = TreeNode(id=456, text='zxc zxc', type='leaf', props={'p1new': 'k1new', 'str_id': 'th5h6'})
UPDATE_INVALID_LEAF_TNODE3 = TreeNode(id='456', text=123, type='leaf', props={'p1new': 'k1new', 'str_id': 'th5h6'})
UPDATE_INVALID_LEAF_TNODE4 = TreeNode(id='456', text='zxc zxc', type='leaf', props={123: 'k1new', 'str_id': 'th5h6'})
UPDATE_INVALID_LEAF_TNODE5 = TreeNode(id='456', text='zxc zxc', type='leaf', props={'p1new': 'k1new', 'external_id': '456', 'str_id': 'th5h6'})


################################################################

# parents_id, childs_data, exceptions
TREEDB_CREATE_TEST_CASES = [
    # 1. позитивный тест
    # 1.1. одна новая вершина
    (["ROOT_NODE_ID"],[VALID_LEAF_TNODE1],[False]),
    # 1.2. несколько новых вершин
    (["ROOT_NODE_ID", VALID_SUM_TNODE1.id, VALID_LEAF_TNODE1.id, VALID_SUM_TNODE1.id],
     [VALID_SUM_TNODE1, VALID_LEAF_TNODE1, VALID_LEAF_TNODE2],[False, False, False]),
    # 3. parent_id не существует
    (["ROOT_NODE_ID", VALID_SUM_TNODE1.id],[VALID_LEAF_TNODE1, VALID_LEAF_TNODE2],[False, True]),
    # 4.1 parent_id невалидный
    (["ROOT_NODE_ID", 123],[VALID_LEAF_TNODE1, VALID_LEAF_TNODE2],[False, True]),
    # 4.2 parent_id невалидный
    (["ROOT_NODE_ID", None],[VALID_LEAF_TNODE1, VALID_LEAF_TNODE2],[False, True]),
    # 5. у new_node невалидный id
    (["ROOT_NODE_ID"],[INVALID_LEAF_TNODE1],[True]),
    # 6. у new_node невалидный type
    (["ROOT_NODE_ID"],[INVALID_LEAF_TNODE2],[True]),
    # 7. у new_node невалидный text
    (["ROOT_NODE_ID"],[INVALID_LEAF_TNODE3],[True]),
    # 8. у new_node невалидный тип полей в props
    (["ROOT_NODE_ID"],[INVALID_LEAF_TNODE4],[True]),
    # 9. у new_node в props присутствуют зарезервированные поля
    (["ROOT_NODE_ID"],[INVALID_LEAF_TNODE5],[True]),
    # 10. new_node с таким id уже существует
    (["ROOT_NODE_ID", VALID_SUM_TNODE1.id, VALID_LEAF_TNODE1.id, VALID_SUM_TNODE1.id],
     [VALID_SUM_TNODE1, VALID_LEAF_TNODE1, VALID_LEAF_TNODE1],[False, False, True]),
]

TREEDB_POPULATED_CREATE_TEST_CASES = []
for db_vendor in AVAILABLE_TREE_DBS:
    for i in range(len(TREEDB_CREATE_TEST_CASES)):
        TREEDB_POPULATED_CREATE_TEST_CASES.append(TREEDB_CREATE_TEST_CASES[i] + (db_vendor,))

################################################################

# create_pairs, read_ids, ids_type, expected, exception
TREEDB_READ_TEST_CASES = [
    # 1. позитивный случай
    # 1.1. external_id
    ([("ROOT_NODE_ID",VALID_LEAF_TNODE1), ("ROOT_NODE_ID",VALID_LEAF_TNODE2)],
     [VALID_LEAF_TNODE1.id, VALID_LEAF_TNODE2.id], TreeIdType.external,
     {VALID_LEAF_TNODE1.id: VALID_LEAF_TNODE1, VALID_LEAF_TNODE2.id: VALID_LEAF_TNODE2}, False),
    # 1.2. str_id
    ([("ROOT_NODE_ID",VALID_LEAF_TNODE1), ("ROOT_NODE_ID",VALID_LEAF_TNODE2)],
     [VALID_LEAF_TNODE1.props['str_id'], VALID_LEAF_TNODE2.props['str_id']], TreeIdType.str,
     {VALID_LEAF_TNODE1.id: VALID_LEAF_TNODE1, VALID_LEAF_TNODE2.id: VALID_LEAF_TNODE2}, False),
    # 2. невалидный тип
    ([("ROOT_NODE_ID",VALID_LEAF_TNODE1), ("ROOT_NODE_ID",VALID_LEAF_TNODE2)],
     [VALID_LEAF_TNODE1.id], 'external_id', None, True),
    # 3. невалидный id (несколько id в списке)
    ([("ROOT_NODE_ID",VALID_LEAF_TNODE1), ("ROOT_NODE_ID",VALID_LEAF_TNODE2)],
     [VALID_LEAF_TNODE1.id, 123], TreeIdType.external, None, True),
    # 4. id такого типа не существует (несколько id в списке)
    # 4.1. external_id
    ([("ROOT_NODE_ID",VALID_LEAF_TNODE1), ("ROOT_NODE_ID",VALID_LEAF_TNODE2)],
     [VALID_LEAF_TNODE1.id, "not_existing_id"], TreeIdType.external,
     {VALID_LEAF_TNODE1.id: VALID_LEAF_TNODE1}, False),
    # 4.2. str_id
    ([("ROOT_NODE_ID",VALID_LEAF_TNODE1), ("ROOT_NODE_ID",VALID_LEAF_TNODE2)],
     [VALID_LEAF_TNODE1.props['str_id'], "not_existing_id"], TreeIdType.str,
     {VALID_LEAF_TNODE1.id: VALID_LEAF_TNODE1}, False)
]

TREEDB_POPULATED_READ_TEST_CASES = []
for db_vendor in AVAILABLE_TREE_DBS:
    for i in range(len(TREEDB_READ_TEST_CASES)):
        TREEDB_POPULATED_READ_TEST_CASES.append(TREEDB_READ_TEST_CASES[i] + (db_vendor,))

################################################################

# create_pairs, update_nodes, exception
TREEDB_UPDATE_TEST_CASES = [
    # 1. позитивный случай (несколько items в списке)
    ([["ROOT_NODE_ID", VALID_SUM_TNODE1], [VALID_SUM_TNODE1.id, VALID_LEAF_TNODE1]],
     [UPDATE_SUM_TNODE1, UPDATE_LEAF_TNODE1],False),
    # 2. позитивный случай (меняем тип у вершины)
    ([["ROOT_NODE_ID", VALID_SUM_TNODE1], [VALID_SUM_TNODE1.id, VALID_LEAF_TNODE1]],
     [UPDATE_LEAF_TNODE1_TO_SUMM], False),
    # 3. навалидный тип (несколько items в списке)
    ([["ROOT_NODE_ID", VALID_SUM_TNODE1], [VALID_SUM_TNODE1.id, VALID_LEAF_TNODE1]],
     [UPDATE_SUM_TNODE1, UPDATE_INVALID_LEAF_TNODE1], True),
    # 4. навалидный id (несколько items в списке)
    ([["ROOT_NODE_ID", VALID_SUM_TNODE1], [VALID_SUM_TNODE1.id, VALID_LEAF_TNODE1]],
     [UPDATE_SUM_TNODE1, UPDATE_INVALID_LEAF_TNODE2], True),
    # 5. навалидный text (несколько items в списке)
    ([["ROOT_NODE_ID", VALID_SUM_TNODE1], [VALID_SUM_TNODE1.id, VALID_LEAF_TNODE1]],
     [UPDATE_SUM_TNODE1, UPDATE_INVALID_LEAF_TNODE3], True),
    # 6. навалидный props (несколько items в списке)
    ([["ROOT_NODE_ID", VALID_SUM_TNODE1], [VALID_SUM_TNODE1.id, VALID_LEAF_TNODE1]],
     [UPDATE_SUM_TNODE1, UPDATE_INVALID_LEAF_TNODE4], True),
    # 7. зарезервированное поле в props (несколько items в списке)
    ([["ROOT_NODE_ID", VALID_SUM_TNODE1], [VALID_SUM_TNODE1.id, VALID_LEAF_TNODE1]],
     [UPDATE_SUM_TNODE1, INVALID_LEAF_TNODE5], True),
    # 8. элемента с таким id не существует (несколько items в списке)
    ([["ROOT_NODE_ID", VALID_SUM_TNODE1], [VALID_SUM_TNODE1.id, VALID_LEAF_TNODE1]],
     [UPDATE_SUM_TNODE1, VALID_LEAF_TNODE2], True)
]

TREEDB_POPULATED_UPDATE_TEST_CASES = []
for db_vendor in AVAILABLE_TREE_DBS:
    for i in range(len(TREEDB_UPDATE_TEST_CASES)):
        TREEDB_POPULATED_UPDATE_TEST_CASES.append(TREEDB_UPDATE_TEST_CASES[i] + (db_vendor,))

################################################################

# create_pairs, delete_ids, ids_type, exception
TREEDB_DELETE_TEST_CASES = [
    # 1. позитивный случай (несколько id в списке)
    # 1.1 external_id
    ([["ROOT_NODE_ID", VALID_SUM_TNODE1], [VALID_SUM_TNODE1.id,  VALID_LEAF_TNODE1],
      [VALID_SUM_TNODE1.id, VALID_LEAF_TNODE2]], [VALID_LEAF_TNODE2.id, VALID_LEAF_TNODE1.id],
      TreeIdType.external, False),
    # 1.2 str_id
    ([["ROOT_NODE_ID", VALID_SUM_TNODE1], [VALID_SUM_TNODE1.id,  VALID_LEAF_TNODE1],
      [VALID_SUM_TNODE1.id, VALID_LEAF_TNODE2]], [VALID_LEAF_TNODE2.props['str_id'], VALID_LEAF_TNODE1.props['str_id']],
      TreeIdType.str, False),
    # 2. невалидный тип
    ([["ROOT_NODE_ID", VALID_SUM_TNODE1], [VALID_SUM_TNODE1.id,  VALID_LEAF_TNODE1],
      [VALID_SUM_TNODE1.id, VALID_LEAF_TNODE2]], [VALID_LEAF_TNODE2.id, VALID_LEAF_TNODE1.id],
      'external', True),
    # 3. невалидный id (несколько id в списке)
    ([["ROOT_NODE_ID", VALID_SUM_TNODE1], [VALID_SUM_TNODE1.id,  VALID_LEAF_TNODE1],
      [VALID_SUM_TNODE1.id, VALID_LEAF_TNODE2]], [VALID_LEAF_TNODE2.id, 123],
      TreeIdType.external, True),
    # 4. id с таким типом не существует (несколько id в списке)
    # 4.1. external_id
    ([["ROOT_NODE_ID", VALID_SUM_TNODE1], [VALID_SUM_TNODE1.id,  VALID_LEAF_TNODE1],
      [VALID_SUM_TNODE1.id, VALID_LEAF_TNODE2]], [VALID_LEAF_TNODE2.id, VALID_SUM_TNODE2.id],
      TreeIdType.external, False),
    # 4.2. str_id
    ([["ROOT_NODE_ID", VALID_SUM_TNODE1], [VALID_SUM_TNODE1.id,  VALID_LEAF_TNODE1],
      [VALID_SUM_TNODE1.id, VALID_LEAF_TNODE2]], [VALID_LEAF_TNODE2.id, "not_existing_id"],
      TreeIdType.str, False),
    # 5. у вершины-родителя есть вершины-дети
    ([["ROOT_NODE_ID", VALID_SUM_TNODE1], [VALID_SUM_TNODE1.id,  VALID_LEAF_TNODE1],
      [VALID_SUM_TNODE1.id, VALID_LEAF_TNODE2]], [VALID_SUM_TNODE1.id],
      TreeIdType.external, True)
]

TREEDB_POPULATED_DELETE_TEST_CASES = []
for db_vendor in AVAILABLE_TREE_DBS:
    for i in range(len(TREEDB_DELETE_TEST_CASES)):
        TREEDB_POPULATED_DELETE_TEST_CASES.append(TREEDB_DELETE_TEST_CASES[i] + (db_vendor,))

################################################################

# create_pairs, expected_count
TREEDB_COUNT_TEST_CASES = [
    # 1. нуль leaf-элементов
    ([["ROOT_NODE_ID",VALID_SUM_TNODE1]], {'leaf': 0, 'summarized': 1, 'root': 1}),
    # 2. нуль summed-элементов
    ([["ROOT_NODE_ID",VALID_LEAF_TNODE1], ["ROOT_NODE_ID", VALID_LEAF_TNODE2]], {'leaf': 2, 'summarized': 0, 'root': 1}),
    # 3. графовая бд пустая
    ([], {'leaf': 0, 'summarized': 0, 'root': 1}),
    # 4. ненулевая графовая бд с leaf- и summed-элементами
    ([["ROOT_NODE_ID",VALID_SUM_TNODE1], [VALID_SUM_TNODE1.id,VALID_LEAF_TNODE1],
        [VALID_SUM_TNODE1.id, VALID_LEAF_TNODE2]],  {'leaf': 2, 'summarized': 1, 'root': 1})
]

TREEDB_POPULATED_COUNT_TEST_CASES = []
for db_vendor in AVAILABLE_TREE_DBS:
    for i in range(len(TREEDB_COUNT_TEST_CASES)):
        TREEDB_POPULATED_COUNT_TEST_CASES.append(TREEDB_COUNT_TEST_CASES[i] + (db_vendor,))

################################################################

# create_pairs, node_id, type, exception, expected_value
TREEDB_EXIST_TEST_CASES = [
    # 1. id существует
    # 1.1. external_id
    ([["ROOT_NODE_ID",VALID_SUM_TNODE1], [VALID_SUM_TNODE1.id,VALID_LEAF_TNODE1],
        [VALID_SUM_TNODE1.id, VALID_LEAF_TNODE2]], VALID_LEAF_TNODE2.id, TreeIdType.external, False, True),
    # 1.2. str_id
    ([["ROOT_NODE_ID",VALID_SUM_TNODE1], [VALID_SUM_TNODE1.id,VALID_LEAF_TNODE1],
        [VALID_SUM_TNODE1.id, VALID_LEAF_TNODE2]], VALID_LEAF_TNODE1.props['str_id'], TreeIdType.str, False, True),
    # 2. невалидный id
    ([["ROOT_NODE_ID",VALID_SUM_TNODE1], [VALID_SUM_TNODE1.id,VALID_LEAF_TNODE1],
        [VALID_SUM_TNODE1.id, VALID_LEAF_TNODE2]], 123, TreeIdType.external, True, None),
    # 3. id не существует впринципе
    # 3.1. external_id
    ([["ROOT_NODE_ID",VALID_SUM_TNODE1], [VALID_SUM_TNODE1.id,VALID_LEAF_TNODE1],
        [VALID_SUM_TNODE1.id, VALID_LEAF_TNODE2]], "not_existing_id", TreeIdType.external, False, False),
    # 3.2. str_id
    ([["ROOT_NODE_ID",VALID_SUM_TNODE1], [VALID_SUM_TNODE1.id,VALID_LEAF_TNODE1],
        [VALID_SUM_TNODE1.id, VALID_LEAF_TNODE2]], "not_existing_id", TreeIdType.str, False, False)
]

TREEDB_POPULATED_EXIST_TEST_CASES = []
for db_vendor in AVAILABLE_TREE_DBS:
    for i in range(len(TREEDB_EXIST_TEST_CASES)):
        TREEDB_POPULATED_EXIST_TEST_CASES.append(TREEDB_EXIST_TEST_CASES[i] + (db_vendor,))

################################################################

# create_pairs, expected_count
TREEDB_CLEAR_TEST_CASES = [
    # 1. нуль leaf-элементов
    ([["ROOT_NODE_ID",VALID_SUM_TNODE1]], {'leaf': 0, 'summarized': 1, 'root': 1}),
    # 2. нуль summed-элементов
    ([["ROOT_NODE_ID",VALID_LEAF_TNODE1], ["ROOT_NODE_ID", VALID_LEAF_TNODE2]], {'leaf': 2, 'summarized': 0, 'root': 1}),
    # 3. графовая бд пустая
    ([], {'leaf': 0, 'summarized': 0, 'root': 1}),
    # 4. ненулевая графовая бд с leaf- и summed-элементами
    ([["ROOT_NODE_ID",VALID_SUM_TNODE1], [VALID_SUM_TNODE1.id,VALID_LEAF_TNODE1],
        [VALID_SUM_TNODE1.id, VALID_LEAF_TNODE2]],  {'leaf': 2, 'summarized': 1, 'root': 1})
]

TREEDB_POPULATED_CLEAR_TEST_CASES = []
for db_vendor in AVAILABLE_TREE_DBS:
    for i in range(len(TREEDB_CLEAR_TEST_CASES)):
        TREEDB_POPULATED_CLEAR_TEST_CASES.append(TREEDB_CLEAR_TEST_CASES[i] + (db_vendor,))

################################################################

TEST_TREE = [("ROOT_NODE_ID", VALID_SUM_TNODE1),("ROOT_NODE_ID", VALID_SUM_TNODE2), ("ROOT_NODE_ID", VALID_SUM_TNODE3),("ROOT_NODE_ID", VALID_SUM_TNODE4),
 (VALID_SUM_TNODE1.id, VALID_LEAF_TNODE1), (VALID_SUM_TNODE1.id, VALID_SUM_TNODE5), (VALID_SUM_TNODE5.id, VALID_SUM_TNODE6), (VALID_SUM_TNODE2.id, VALID_SUM_TNODE7),
  (VALID_SUM_TNODE2.id, VALID_SUM_TNODE8), (VALID_SUM_TNODE3.id, VALID_LEAF_TNODE2), (VALID_SUM_TNODE4.id, VALID_LEAF_TNODE3), (VALID_SUM_TNODE4.id, VALID_LEAF_TNODE4)]

# create_pairs, parent_id, expected_cnodes, exception
TREEDB_GETCHILDS_TEST_CASES = [
    # 1. родительской вершины не существует
    (TEST_TREE, 'not_existing_id', None, True),
    # 2. родительская вершина существует
    # 2.1. один ребёнок
    # 2.1.1 leaf-элемент
    (TEST_TREE, VALID_SUM_TNODE3.id, {VALID_LEAF_TNODE2.id: VALID_LEAF_TNODE2}, False),
    # 2.1.2 summed-элемент
    (TEST_TREE, VALID_SUM_TNODE5.id, {VALID_SUM_TNODE6.id: VALID_SUM_TNODE6}, False),
    # 2.2. несколько детей
    # 2.2.1 все leaf-элементы
    (TEST_TREE, VALID_SUM_TNODE4.id, {VALID_LEAF_TNODE3.id: VALID_LEAF_TNODE3, VALID_LEAF_TNODE4.id: VALID_LEAF_TNODE4}, False),
    # 2.2.2 все summed-элементы
    (TEST_TREE, VALID_SUM_TNODE2.id, {VALID_SUM_TNODE7.id: VALID_SUM_TNODE7, VALID_SUM_TNODE8.id: VALID_SUM_TNODE8}, False),
    # 2.3 разные элементы
    (TEST_TREE, VALID_SUM_TNODE1.id, {VALID_LEAF_TNODE1.id: VALID_LEAF_TNODE1, VALID_SUM_TNODE5.id: VALID_SUM_TNODE5}, False),
    # 2.3. нуль детей
    (TEST_TREE, VALID_SUM_TNODE6.id, dict(), False)
]

TREEDB_POPULATED_GETCHILDS_TEST_CASES = []
for db_vendor in AVAILABLE_TREE_DBS:
    for i in range(len(TREEDB_GETCHILDS_TEST_CASES)):
        TREEDB_POPULATED_GETCHILDS_TEST_CASES.append(TREEDB_GETCHILDS_TEST_CASES[i] + (db_vendor,))

################################################################

# create_pairs, expected_max_depth
TREEDB_GETMAXDEPTH_TEST_CASES = [
    # 1. позитивный случай
    (TEST_TREE, 3),
]

TREEDB_POPULATED_GETMAXDEPTH_TEST_CASES = []
for db_vendor in AVAILABLE_TREE_DBS:
    for i in range(len(TREEDB_GETMAXDEPTH_TEST_CASES)):
        TREEDB_POPULATED_GETMAXDEPTH_TEST_CASES.append(TREEDB_GETMAXDEPTH_TEST_CASES[i] + (db_vendor,))

################################################################

# create_pairs, id, expected_descendants, exception
TREEDB_GETLEAFDESCENDANTS_TEST_CASES = [
    (TEST_TREE, 'ROOT_NODE_ID', {VALID_LEAF_TNODE1.id: VALID_LEAF_TNODE1, VALID_LEAF_TNODE2.id: VALID_LEAF_TNODE2, 
        VALID_LEAF_TNODE3.id: VALID_LEAF_TNODE3, VALID_LEAF_TNODE4.id: VALID_LEAF_TNODE4}, False),
    (TEST_TREE, VALID_SUM_TNODE4.id, {VALID_LEAF_TNODE3.id: VALID_LEAF_TNODE3, VALID_LEAF_TNODE4.id: VALID_LEAF_TNODE4}, False),
    (TEST_TREE, VALID_SUM_TNODE3.id, {VALID_LEAF_TNODE2.id: VALID_LEAF_TNODE2}, False),
    (TEST_TREE, VALID_SUM_TNODE2.id, dict(), False),
    (TEST_TREE, VALID_SUM_TNODE1.id, {VALID_LEAF_TNODE1.id: VALID_LEAF_TNODE1}, False)
]

TREEDB_POPULATED_GETLEAFDESCENDANTS_TEST_CASES = []
for db_vendor in AVAILABLE_TREE_DBS:
    for i in range(len(TREEDB_GETLEAFDESCENDANTS_TEST_CASES)):
        TREEDB_POPULATED_GETLEAFDESCENDANTS_TEST_CASES.append(TREEDB_GETLEAFDESCENDANTS_TEST_CASES[i] + (db_vendor,))