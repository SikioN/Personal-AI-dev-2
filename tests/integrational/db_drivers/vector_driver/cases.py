import torch
import numpy

import sys
# TO CHANGE
PROJECT_BASE_DIR = '../'
TEST_VOLUME_DIR = './volumes'
sys.path.insert(0, PROJECT_BASE_DIR)

from src.db_drivers.vector_driver import VectorDBInstance

# TO CHANGE
AVAILABLE_VECTOR_DBS = ['chroma', 'milvus'] # 'chroma', 'milvus'

###############################################################################################

FULL_INSTANCE1 = VectorDBInstance(id='123', document='qwerty', embedding=[0.1,0.2,0.3], metadata={'k1': 'v1'})
FULL_INSTANCE2 = VectorDBInstance(id='456', document='ytrewq', embedding=[0.4,0.5,0.6], metadata={'k2': 'v2'})

UPDATE_FULL_INSTANCE1 = VectorDBInstance(id='123', document='qwerty qwerty', embedding=[0.1,0.4,0.1], metadata={'k1new': 'v1new'})
UPDATE_FULL_INSTANCE2 = VectorDBInstance(id='456', document='ytrewq ytrewq', embedding=[0.5,0.2,0.5], metadata={'k2new': 'v2new'})

INSTANCE_WO_METADATA = VectorDBInstance(id='456', document='ytrewq', embedding=[0.4,0.5,0.6])
INSTANCE_WO_ID = VectorDBInstance(document='ytrewq', embedding=[0.4,0.5,0.6])
INSTANCE_WO_EMBEDDING = VectorDBInstance(id='456', document='ytrewq')

INSTANCE_WITH_BAD_ID1 = VectorDBInstance(id=123, document='qwerty', embedding=[0.1,0.2,0.3])
INSTANCE_WITH_BAD_ID2 = VectorDBInstance(id=True, document='qwerty', embedding=[0.1,0.2,0.3])
INSTANCE_WITH_BAD_ID3 = VectorDBInstance(id=None, document='qwerty', embedding=[0.1,0.2,0.3])

INSTANCE_WITH_TORCH_EMB = VectorDBInstance(id='123', document='qwerty', embedding=torch.tensor([0.1,0.2,0.3]), metadata={'k1': 'v1'})
INSTANCE_WITH_NUMPY_EMB = VectorDBInstance(id='123', document='qwerty', embedding=numpy.array([0.1,0.2,0.3]), metadata={'k1': 'v1'})

INSTANCE_WITH_BAD_EMB1 = VectorDBInstance(id='456', document='ytrewq', embedding="[0.4,0.5,0.6]")
INSTANCE_WITH_BAD_EMB2 = VectorDBInstance(id='456', document='ytrewq', embedding=None)
INSTANCE_WITH_BAD_EMB3 = VectorDBInstance(id='456', document='ytrewq', embedding=[[0.4,0.5,0.6]])

###############################################################################################

VECTORDB_CREATE_TEST_CASES = [
    # 1. пустой список
    [[[]], {'exception': False, 'db_size': 0}],
    # 2. один элемент с метаданными
    [[[FULL_INSTANCE1]], {'exception': False, 'db_size': 1}],
    # 3. один элемент без метаданных
    [[[INSTANCE_WO_METADATA]], {'exception': False, 'db_size': 1}],
    # 4. один элемент без идентификатора
    [[[INSTANCE_WO_ID]], {'exception': True, 'db_size': 0}],
    # 5. один элемент без ебмеддинга
    [[[INSTANCE_WO_EMBEDDING]], {'exception': True, 'db_size': 0}],
    # 6. несколько элементов
    [[[FULL_INSTANCE1,FULL_INSTANCE2]], {'exception': False, 'db_size': 2}],
    # 7. дубликаты в списке
    [[[FULL_INSTANCE1,FULL_INSTANCE1]], {'exception': True, 'db_size': 0}],
    # 8. элемент существует в бд (по id)
    [[[FULL_INSTANCE1],[FULL_INSTANCE1]], {'exception': False, 'db_size': 1}],
    # 9. torch-тип данных эмбеддинга
    [[[INSTANCE_WITH_TORCH_EMB]], {'exception': True, 'db_size': 0}],
    # 10. numpy-тип данных эмбеддинга
    [[[INSTANCE_WITH_NUMPY_EMB]], {'exception': True, 'db_size': 0}],
    # 11. неверный формат идентикатора 1
    [[[INSTANCE_WITH_BAD_ID1]],{'exception': True, 'db_size': 0}],
    # 12. неверный формат идентификатора 2
    [[[INSTANCE_WITH_BAD_ID2]],{'exception': True, 'db_size': 0}],
    # 13. неверный формат идентификатора 3
    [[[INSTANCE_WITH_BAD_ID3]],{'exception': True, 'db_size': 0}]
    ]

VECTORDB_POPULATED_CREATE_TEST_CASES = []
for db_vendor in AVAILABLE_VECTOR_DBS:
    for i in range(len(VECTORDB_CREATE_TEST_CASES)):
        VECTORDB_POPULATED_CREATE_TEST_CASES.append(VECTORDB_CREATE_TEST_CASES[i] + [db_vendor])

###############################################################################################

VECTORDB_DELETE_TEST_CASES = [
    # 1. пустой список
    [[FULL_INSTANCE1,FULL_INSTANCE2], [], {'exception': False, 'db_size': 2}],
    # 2. удаление одного существующего элемента
    [[FULL_INSTANCE1,FULL_INSTANCE2], ['456'], {'exception': False, 'db_size': 1}],
    # 3. удаление одного несуществующего элемента
    [[FULL_INSTANCE1,FULL_INSTANCE2], ['789'], {'exception': False, 'db_size': 2}],
    # 4. в списке элементов на удаление есть несуществующие
    [[FULL_INSTANCE1,FULL_INSTANCE2], ['456','789'], {'exception': False, 'db_size': 1}],
    # 5. в списке элементов на удаление все существуют
    [[FULL_INSTANCE1,FULL_INSTANCE2], ['123','456'], {'exception': False, 'db_size': 0}],
    # 6. неверный формат идентификаторов 1
    [[FULL_INSTANCE1,FULL_INSTANCE2], [123], {'exception': True, 'db_size': 2}],
    # 7. неверный формат идентификатора 2
    [[FULL_INSTANCE1,FULL_INSTANCE2], [True], {'exception': True, 'db_size': 2}],
    # 8. неверный формат идентификатора 3
    [[FULL_INSTANCE1,FULL_INSTANCE2], [None], {'exception': True, 'db_size': 2}]
]

VECTORDB_POPULATED_DELETE_TEST_CASES = []
for db_vendor in AVAILABLE_VECTOR_DBS:
    for i in range(len(VECTORDB_DELETE_TEST_CASES)):
        VECTORDB_POPULATED_DELETE_TEST_CASES.append(VECTORDB_DELETE_TEST_CASES[i] + [db_vendor])

###############################################################################################

VECTORDB_READ_TEST_CASES = [
    # 1. пустой список
    [[FULL_INSTANCE1,FULL_INSTANCE2], [], {'exception': False, 'output_ids': []}],
    # 2. один существующий элемент
    [[FULL_INSTANCE1,FULL_INSTANCE2], ['123'], {'exception': False, 'output_ids': ['123']}],
    # 3. один несуществующий элемент
    [[FULL_INSTANCE1,FULL_INSTANCE2], ['789'], {'exception': False, 'output_ids': []}],
    # 4. несколько существующих элементов
    [[FULL_INSTANCE1,FULL_INSTANCE2], ['123', '456'], {'exception': False, 'output_ids': ['123','456']}],
    # 5. в списке есть несуществующий элемент
    [[FULL_INSTANCE1,FULL_INSTANCE2], ['123', '789', '456'], {'exception': False, 'output_ids': ['123', '456']}],
    # 6. неверный формат идентификаторов 1
    [[FULL_INSTANCE1,FULL_INSTANCE2], [123], {'exception': True, 'output_ids': []}],
    # 7. неверный формат идентификатора 2
    [[FULL_INSTANCE1,FULL_INSTANCE2], [True], {'exception': True, 'output_ids': []}],
    # 8. неверный формат идентификатора 3
    [[FULL_INSTANCE1,FULL_INSTANCE2], [None], {'exception': True, 'output_ids': []}]
]

VECTORDB_POPULATED_READ_TEST_CASES = []
for db_vendor in AVAILABLE_VECTOR_DBS:
    for i in range(len(VECTORDB_READ_TEST_CASES)):
        VECTORDB_POPULATED_READ_TEST_CASES.append(VECTORDB_READ_TEST_CASES[i] + [db_vendor])

###############################################################################################

VECTORDB_UPDATE_TEST_CASES = [
    # TODO
]

###############################################################################################

# init_instance, new_instances, exception, expected_count
VECTORDB_UPSERT_TEST_CASES = [
    # элемент добавляется с нуля
    [[FULL_INSTANCE1],{FULL_INSTANCE2.id: FULL_INSTANCE2},False,2],
    # элемент обновляется
    [[FULL_INSTANCE1, FULL_INSTANCE2],{UPDATE_FULL_INSTANCE2.id: UPDATE_FULL_INSTANCE2},False,2],
    # несколько элементов (один добавляется, другой обновляется)
    [[FULL_INSTANCE1],{FULL_INSTANCE2.id: FULL_INSTANCE2, UPDATE_FULL_INSTANCE1.id: UPDATE_FULL_INSTANCE1},False,2]
]

VECTORDB_POPULATED_UPSERT_TEST_CASES = []
for db_vendor in AVAILABLE_VECTOR_DBS:
    for i in range(len(VECTORDB_UPSERT_TEST_CASES)):
        VECTORDB_POPULATED_UPSERT_TEST_CASES.append(VECTORDB_UPSERT_TEST_CASES[i] + [db_vendor])

###############################################################################################

VECTORDB_RETRIEVE_TEST_CASES = [
    # 1.1 ретрив по одному квери
    [[FULL_INSTANCE1,FULL_INSTANCE2], [FULL_INSTANCE1], 1, None, {'exception': False, 'output_size': 1}],
    # 1.2 ретрив по одному квери (из подмножества)
    [[FULL_INSTANCE1,FULL_INSTANCE2], [FULL_INSTANCE1], 2, [FULL_INSTANCE1.id], {'exception': False, 'output_size': 1}],
    # 2. ретрив по нескольким квери
    [[FULL_INSTANCE1,FULL_INSTANCE2], [FULL_INSTANCE1, FULL_INSTANCE1], 1, None, {'exception': False, 'output_size': 1}],
    # 3. в бд меньше элементов, чем заданное количество
    [[FULL_INSTANCE1], [FULL_INSTANCE1], 2, None, {'exception': False, 'output_size': 1}],
    # 4. torch-тип данных эмбеддинга
    [[FULL_INSTANCE1,FULL_INSTANCE2], [INSTANCE_WITH_TORCH_EMB], 2, None, {'exception': True, 'output_size': -1}],
    # 5. numpy-тип данных эмбеддинга
    [[FULL_INSTANCE1,FULL_INSTANCE2], [INSTANCE_WITH_NUMPY_EMB], 2, None, {'exception': True, 'output_size': -1}],
    # 6. неверный формат ембеддинга квери # 1
    [[FULL_INSTANCE1,FULL_INSTANCE2], [INSTANCE_WITH_BAD_EMB1], 2, None, {'exception': True, 'output_size': -1}],
    # 7. неверный формат ембеддинга квери # 2
    [[FULL_INSTANCE1,FULL_INSTANCE2], [INSTANCE_WITH_BAD_EMB2], 2, None, {'exception': True, 'output_size': -1}],
    # 8. неверный формат ебмеддинга квери # 3
    [[FULL_INSTANCE1,FULL_INSTANCE2], [INSTANCE_WITH_BAD_EMB2], 2, None, {'exception': True, 'output_size': -1}],
    # 9. В векторной бд нуль объектов
    [[], [FULL_INSTANCE1], 2, None, {'exception': False, 'output_size': 0}]
]

VECTORDB_POPULATED_RETRIEVE_TEST_CASES = []
for db_vendor in AVAILABLE_VECTOR_DBS:
    for i in range(len(VECTORDB_RETRIEVE_TEST_CASES)):
        VECTORDB_POPULATED_RETRIEVE_TEST_CASES.append(VECTORDB_RETRIEVE_TEST_CASES[i] + [db_vendor])

###############################################################################################

VECTORDB_COUNT_TEST_CASES = [
    # 1. нуль элементов
    [[], 0],
    # 2. один Элемент
    [[FULL_INSTANCE1], 1],
    # 3. несколько элементов
    [[FULL_INSTANCE1,FULL_INSTANCE2], 2]
]

VECTORDB_POPULATED_COUNT_TEST_CASES = []
for db_vendor in AVAILABLE_VECTOR_DBS:
    for i in range(len(VECTORDB_COUNT_TEST_CASES)):
        VECTORDB_POPULATED_COUNT_TEST_CASES.append(VECTORDB_COUNT_TEST_CASES[i] + [db_vendor])

###############################################################################################

VECTORDB_EXIST_TEST_CASES = [
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

VECTORDB_POPULATED_EXIST_TEST_CASES = []
for db_vendor in AVAILABLE_VECTOR_DBS:
    for i in range(len(VECTORDB_EXIST_TEST_CASES)):
        VECTORDB_POPULATED_EXIST_TEST_CASES.append(VECTORDB_EXIST_TEST_CASES[i] + [db_vendor])

###############################################################################################

VECTORDB_CLEAR_TEST_CASES = [
    # 1. чистка пустой бд
    [[]],
    # 2. чиста бд с одним элементов
    [[FULL_INSTANCE1]],
    # 3. чиста бд с несколькими элементами
    [[FULL_INSTANCE1,FULL_INSTANCE2]]
]

VECTORDB_POPULATED_CLEAR_TEST_CASES = []
for db_vendor in AVAILABLE_VECTOR_DBS:
    for i in range(len(VECTORDB_CLEAR_TEST_CASES)):
        VECTORDB_POPULATED_CLEAR_TEST_CASES.append(VECTORDB_CLEAR_TEST_CASES[i] + [db_vendor])
