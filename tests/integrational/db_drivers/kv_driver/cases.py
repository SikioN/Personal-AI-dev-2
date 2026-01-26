import sys
sys.path.insert(0, "../")
from src.db_drivers.kv_driver import KeyValueDBInstance

# TO CHANGE
AVAILABLE_KV_DBS = ['inmemory_kv', 'redis', 'mongo', 'mixed_kv'] # 'inmemory_kv', 'redis', 'mongo', 'mixed_kv', 'aerospike

###############################################################################################

FULL_INSTANCE1 = KeyValueDBInstance(id='123', value='v1')
FULL_INSTANCE2 = KeyValueDBInstance(id='456', value='v2')
INSTANCE_WITH_NONE_VALUE = KeyValueDBInstance(id='789', value=None)

INSTANCE_WITH_BAD_ID1 = KeyValueDBInstance(id=123, value='v2')
INSTANCE_WITH_BAD_ID2 = KeyValueDBInstance(id=True, value='v2')
INSTANCE_WITH_BAD_ID3 = KeyValueDBInstance(id=None, value='v2')

###############################################################################################

KVDB_CREATE_TEST_CASES = [
    # 1. пустой список
    [[[]], {'exception': False, 'db_size': 0}],
    # 2. элемент с метаданными
    [[[FULL_INSTANCE1]], {'exception': False, 'db_size': 1}],
    # 3. элемент без метаданныйх (пустой)
    [[[INSTANCE_WITH_NONE_VALUE]], {'exception': True, 'db_size': 0}],
    # 4. несколько элементов
    [[[FULL_INSTANCE1, FULL_INSTANCE2]], {'exception': False, 'db_size': 2}],
    # 5. дубликаты в списке
    [[[FULL_INSTANCE1, FULL_INSTANCE1]], {'exception': True, 'db_size': 0}],
    # 6. элемент существует в бд (по id)
    [[[FULL_INSTANCE1], [FULL_INSTANCE1]], {'exception': False, 'db_size': 1}],
    # 7. неверный формат идентификатора # 1
    [[[INSTANCE_WITH_BAD_ID1]], {'exception': True, 'db_size': 0}],
    # 8. неверный формат идентификатора # 2
    [[[INSTANCE_WITH_BAD_ID2]], {'exception': True, 'db_size': 0}],
    # 9. неверный формат идентификатора # 3
    [[[INSTANCE_WITH_BAD_ID3]], {'exception': True, 'db_size': 0}]
]

KVDB_POPULATED_CREATE_TEST_CASES = []
for db_vendor in AVAILABLE_KV_DBS:
    for i in range(len(KVDB_CREATE_TEST_CASES)):
        KVDB_POPULATED_CREATE_TEST_CASES.append(KVDB_CREATE_TEST_CASES[i] + [db_vendor])

###############################################################################################

KVDB_DELETE_TEST_CASES = [
    # 1. пустой список
    [[FULL_INSTANCE1, FULL_INSTANCE2], [], {'exception': False, 'db_size': 2}],
    # 2. удаление одного существующего элемента
    [[FULL_INSTANCE1, FULL_INSTANCE2], ['456'], {'exception': False, 'db_size': 1}],
    # 3. удаление одного несуществующего элемента
    [[FULL_INSTANCE1, FULL_INSTANCE2], ['789'], {'exception': False, 'db_size': 2}],
    # 4. в списке элементов на удаление есть несуществующие
    [[FULL_INSTANCE1, FULL_INSTANCE2], ['456','789'], {'exception': False, 'db_size': 1}],
    # 5. в списке элементов на удаление все существуют
    [[FULL_INSTANCE1, FULL_INSTANCE2], ['123','456'], {'exception': False, 'db_size': 0}],
    # 6. неверный формат идентификаторов 1
    [[FULL_INSTANCE1, FULL_INSTANCE2], [123], {'exception': True, 'db_size': 2}],
    # 7. неверный формат идентификатора 2
    [[FULL_INSTANCE1, FULL_INSTANCE2], [True], {'exception': True, 'db_size': 2}],
    # 8. неверный формат идентификатора 3
    [[FULL_INSTANCE1, FULL_INSTANCE2], [None], {'exception': True, 'db_size': 2}]
]

KVDB_POPULATED_DELETE_TEST_CASES = []
for db_vendor in AVAILABLE_KV_DBS:
    for i in range(len(KVDB_DELETE_TEST_CASES)):
        KVDB_POPULATED_DELETE_TEST_CASES.append(KVDB_DELETE_TEST_CASES[i] + [db_vendor])

###############################################################################################

KVDB_READ_TEST_CASES = [
    # 1. пустой список
    [[FULL_INSTANCE1, FULL_INSTANCE2], [], {'exception': False, 'output_ids': []}],
    # 2. один существующий элемент
    [[FULL_INSTANCE1, FULL_INSTANCE2], ['123'], {'exception': False, 'output_ids': ['123']}],
    # 3. один несуществующий элемент
    [[FULL_INSTANCE1,FULL_INSTANCE2], ['789'], {'exception': False, 'output_ids': [None]}],
    # 4. несколько существующих элементов
    [[FULL_INSTANCE1,FULL_INSTANCE2], ['123', '456'], {'exception': False, 'output_ids': ['123','456']}],
    # 5. в списке есть несуществующий элемент
    [[FULL_INSTANCE1,FULL_INSTANCE2], ['123', '789', '456'], {'exception': False, 'output_ids': ['123', None, '456']}],
    # 6. неверный формат идентификатора 1
    [[FULL_INSTANCE1,FULL_INSTANCE2], [123], {'exception': True, 'output_ids': []}],
    # 7. неверный формат идентификатора 2
    [[FULL_INSTANCE1,FULL_INSTANCE2], [True], {'exception': True, 'output_ids': []}],
    # 8. неверный формат идентификатора 3
    [[FULL_INSTANCE1,FULL_INSTANCE2], [None], {'exception': True, 'output_ids': []}]
]

KVDB_POPULATED_READ_TEST_CASES = []
for db_vendor in AVAILABLE_KV_DBS:
    for i in range(len(KVDB_READ_TEST_CASES)):
        KVDB_POPULATED_READ_TEST_CASES.append(KVDB_READ_TEST_CASES[i] + [db_vendor])

###############################################################################################

KVDB_COUNT_TEST_CASES = [
    # 1. нуль элементов
    [[], 0],
    # 2. один Элемент
    [[FULL_INSTANCE1], 1],
    # 3. несколько элементов
    [[FULL_INSTANCE1,FULL_INSTANCE2], 2]
]

KVDB_POPULATED_COUNT_TEST_CASES = []
for db_vendor in AVAILABLE_KV_DBS:
    for i in range(len(KVDB_COUNT_TEST_CASES)):
        KVDB_POPULATED_COUNT_TEST_CASES.append(KVDB_COUNT_TEST_CASES[i] + [db_vendor])

###############################################################################################

KVDB_EXIST_TEST_CASES = [
    # 1. элемент существует
    [[FULL_INSTANCE1,FULL_INSTANCE2], '123', {'exception': False, 'exist': True}],
    # 2. элемента не существует
    [[FULL_INSTANCE1,FULL_INSTANCE2], '789', {'exception': False, 'exist': False}],
    # 3. неверный формат идентификатора # 1
    [[FULL_INSTANCE1,FULL_INSTANCE2], 789, {'exception': True, 'exist': False}],
    # 4. неверный формат идентификатора # 2
    [[FULL_INSTANCE1,FULL_INSTANCE2], False, {'exception': True, 'exist': False}],
    # 5. неверный формат идентификатора # 3
    [[FULL_INSTANCE1,FULL_INSTANCE2], None, {'exception': True, 'exist': False}]
]

KVDB_POPULATED_EXIST_TEST_CASES = []
for db_vendor in AVAILABLE_KV_DBS:
    for i in range(len(KVDB_EXIST_TEST_CASES)):
        KVDB_POPULATED_EXIST_TEST_CASES.append(KVDB_EXIST_TEST_CASES[i] + [db_vendor])

###############################################################################################

KVDB_CLEAR_TEST_CASES = [
    # 1. чистка пустой бд
    [[]],
    # 2. чиста бд с одним элементов
    [[FULL_INSTANCE1]],
    # 3. чиста бд с несколькими элементами
    [[FULL_INSTANCE1,FULL_INSTANCE2]]
]

KVDB_POPULATED_CLEAR_TEST_CASES = []
for db_vendor in AVAILABLE_KV_DBS:
    for i in range(len(KVDB_CLEAR_TEST_CASES)):
        KVDB_POPULATED_CLEAR_TEST_CASES.append(KVDB_CLEAR_TEST_CASES[i] + [db_vendor])
