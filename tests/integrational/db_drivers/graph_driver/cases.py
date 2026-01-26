import sys
# TO CHANGE
PROJECT_BASE_DIR = '../'
TEST_VOLUME_DIR = './volumes'
sys.path.insert(0, PROJECT_BASE_DIR)

from src.utils.data_structs import NodeCreator, Relation, RelationType, NodeType, TripletCreator

# TO CHANGE
AVAILABLE_GRAPH_DBS = ['neo4j', 'kuzu', 'inmemory_graph'] # 'neo4j', 'kuzu', 'inmemory_graph'

###############################################################################################

# nodes
OBJECT_NODE1 = NodeCreator.create(name='abc', n_type=NodeType.object, prop={'k1': 'v1'})
OBJECT_NODE1_2 = NodeCreator.create(name='abc', n_type=NodeType.object, prop={'k1_2': 'v1_2'})

OBJECT_NODE2 = NodeCreator.create(name='def', n_type=NodeType.object, prop={'k2': 'v2'})
OBJECT_NODE3 = NodeCreator.create(name='ghi', n_type=NodeType.object, prop={'k3': 'v3'})
OBJECT_NODE4 = NodeCreator.create(name='yhn', n_type=NodeType.object, prop={'k13': 'v13'})

THESIS_NODE1 = NodeCreator.create(name='qwerty', n_type=NodeType.hyper, prop={'k4': 'v4'})
THESIS_NODE2 = NodeCreator.create(name='asdfgh', n_type=NodeType.hyper, prop={'k5': 'v5'})
THESIS_NODE3 = NodeCreator.create(name='zxcvbn', n_type=NodeType.hyper, prop={'k6': 'v6'})

EPISODIC_NODE1 = NodeCreator.create(name='uiop', n_type=NodeType.episodic, prop={'k7': 'v7'})
EPISODIC_NODE1_2 = NodeCreator.create(name='uiop', n_type=NodeType.episodic, prop={'k7_2': 'v7_2'})

EPISODIC_NODE2 = NodeCreator.create(name='jkl', n_type=NodeType.episodic, prop={'k8': 'v8'})
EPISODIC_NODE3 = NodeCreator.create(name='mnbv', n_type=NodeType.episodic, prop={'k9': 'v9'})

# triplets
SIMPLE_TRIPLET1 = TripletCreator.create(start_node=OBJECT_NODE1, relation=Relation(name='simple1', type=RelationType.simple, prop={'k10': 'v10'}), end_node=OBJECT_NODE2)
SIMPLE_TRIPLET1_2 = TripletCreator.create(start_node=OBJECT_NODE1, relation=Relation(name='simple1_1', type=RelationType.simple, prop={'k16': 'v16'}), end_node=OBJECT_NODE2)

SIMPLE_TRIPLET1_3 = TripletCreator.create(start_node=OBJECT_NODE1, relation=Relation(name='simple1_2', type=RelationType.simple, prop={'k16_2': 'v16_2'}), end_node=OBJECT_NODE1_2)


SIMPLE_TRIPLET2 = TripletCreator.create(start_node=OBJECT_NODE2, relation=Relation(name='simple2', type=RelationType.simple, prop={'k11': 'v11'}), end_node=OBJECT_NODE3)
SIMPLE_TRIPLET3 = TripletCreator.create(start_node=OBJECT_NODE3, relation=Relation(name='simple3', type=RelationType.simple, prop={'k12': 'v12'}), end_node=OBJECT_NODE1)
SIMPLE_TRIPLET4 = TripletCreator.create(start_node=OBJECT_NODE3, relation=Relation(name='simple4', type=RelationType.simple, prop={'k14': 'v14'}), end_node=OBJECT_NODE4)
SIMPLE_TRIPLET5 = TripletCreator.create(start_node=OBJECT_NODE1, relation=Relation(name='simple5', type=RelationType.simple, prop={'k15': 'v15'}), end_node=OBJECT_NODE1)

THESIS_TRIPLET1 = TripletCreator.create(start_node=OBJECT_NODE1, relation=Relation(name='hyper', type=RelationType.hyper), end_node=THESIS_NODE1)
THESIS_TRIPLET2 = TripletCreator.create(start_node=OBJECT_NODE2, relation=Relation(name='hyper', type=RelationType.hyper), end_node=THESIS_NODE1)
THESIS_TRIPLET3 = TripletCreator.create(start_node=OBJECT_NODE3, relation=Relation(name='hyper', type=RelationType.hyper), end_node=THESIS_NODE2)

EPISODIC_TRIPLET1 = TripletCreator.create(start_node=OBJECT_NODE1, relation=Relation(name='episodic', type=RelationType.episodic), end_node=EPISODIC_NODE1)
EPISODIC_TRIPLET1_2 = TripletCreator.create(start_node=OBJECT_NODE1, relation=Relation(name='episodic', type=RelationType.episodic), end_node=EPISODIC_NODE1_2)

EPISODIC_TRIPLET2 = TripletCreator.create(start_node=OBJECT_NODE2, relation=Relation(name='episodic', type=RelationType.episodic), end_node=EPISODIC_NODE1)
EPISODIC_TRIPLET3 = TripletCreator.create(start_node=OBJECT_NODE3, relation=Relation(name='episodic', type=RelationType.episodic), end_node=EPISODIC_NODE2)
EPISODIC_TRIPLET4 = TripletCreator.create(start_node=THESIS_NODE2, relation=Relation(name='episodic', type=RelationType.episodic), end_node=EPISODIC_NODE2)

# creation info
FULL_CREATION_INFO = {'s_node': True, 'e_node': True}
WO_SN_CREATION_INFO = {'s_node': False, 'e_node': True}
WO_EN_CREATION_INFO = {'s_node': True, 'e_node': False}
ONLY_REL_CREATION_INFO = {'s_node': False, 'e_node': False}

ALL_N_TYPES = [NodeType.object, NodeType.hyper, NodeType.episodic]

###############################################################################################

GRAPHDB_CREATE_TEST_CASES = [
    # 1. пустой список
    [[[]], [{}], {'exception': False, 'triplets_count': 0, 'nodes_count': 0}],
    # 2. добавление одного триплета (полностью с creation_info None)
    # 2.1 simple
    [[[SIMPLE_TRIPLET1]], [{}], {'exception': False, 'triplets_count': 1, 'nodes_count': 2}],
    # 2.2 thesis
    [[[THESIS_TRIPLET2]], [{}], {'exception': False, 'triplets_count': 1, 'nodes_count': 2}],
    # 2.3 episodic with object
    [[[EPISODIC_TRIPLET1]], [{}], {'exception': False, 'triplets_count': 1, 'nodes_count': 2}],
    # 2.4 episodic with thesis
    [[[EPISODIC_TRIPLET4]], [{}], {'exception': False, 'triplets_count': 1, 'nodes_count': 2}],
    # 3. добавление одного триплета (полностью с creation_info не None)
    # 3.1 simple
    [[[SIMPLE_TRIPLET1]], [{0:FULL_CREATION_INFO}], {'exception': False, 'triplets_count': 1, 'nodes_count': 2}],
    # 3.2 thesis
    [[[THESIS_TRIPLET2]], [{0:FULL_CREATION_INFO}], {'exception': False, 'triplets_count': 1, 'nodes_count': 2}],
    # 3.3 episodic with object
    [[[EPISODIC_TRIPLET1]], [{0:FULL_CREATION_INFO}], {'exception': False, 'triplets_count': 1, 'nodes_count': 2}],
    # 3.4 episodic with thesis
    [[[EPISODIC_TRIPLET4]], [{0:FULL_CREATION_INFO}], {'exception': False, 'triplets_count': 1, 'nodes_count': 2}],
    # 4. добалвение одного триплета (только связь c заданным creation_info)
    # 4.1 simple rel
    [[[SIMPLE_TRIPLET1, SIMPLE_TRIPLET2],[SIMPLE_TRIPLET3]], [{0:FULL_CREATION_INFO, 1:WO_SN_CREATION_INFO}, {0:ONLY_REL_CREATION_INFO}], {'exception': False, 'triplets_count': 3, 'nodes_count': 3}],
    # 4.2 hyper (object with thesis)
    [[[SIMPLE_TRIPLET2, THESIS_TRIPLET1],[THESIS_TRIPLET2]], [{0:FULL_CREATION_INFO, 1:FULL_CREATION_INFO}, {0:ONLY_REL_CREATION_INFO}], {'exception': False, 'triplets_count': 3, 'nodes_count': 4}],
    # 4.3 episodic (object with episodic)
    [[[SIMPLE_TRIPLET1, EPISODIC_TRIPLET1],[EPISODIC_TRIPLET2]], [{0:FULL_CREATION_INFO, 1:WO_SN_CREATION_INFO}, {0:ONLY_REL_CREATION_INFO}], {'exception': False, 'triplets_count': 3, 'nodes_count': 3}],
    # 4.4 episodic (thesis with episodic)
    [[[EPISODIC_TRIPLET3, THESIS_TRIPLET3],[EPISODIC_TRIPLET4]], [{0:FULL_CREATION_INFO, 1:WO_SN_CREATION_INFO}, {0:ONLY_REL_CREATION_INFO}], {'exception': False, 'triplets_count': 3, 'nodes_count': 3}],
    # 5. добавление одного триплета (связь и стартовая вершина c заданным creation_info)
    # 5.1 object -[simple]> object
    [[[SIMPLE_TRIPLET2], [SIMPLE_TRIPLET1]], [{0:FULL_CREATION_INFO},{0:WO_EN_CREATION_INFO}], {'exception': False, 'triplets_count': 2, 'nodes_count': 3}],
    # 5.2 object -[hyper]> thesis
    [[[THESIS_TRIPLET2], [THESIS_TRIPLET1]], [{0:FULL_CREATION_INFO},{0:WO_EN_CREATION_INFO}], {'exception': False, 'triplets_count': 2, 'nodes_count': 3}],
    # 5.3 object -[episodic]> episodic
    [[[EPISODIC_TRIPLET2], [EPISODIC_TRIPLET1]], [{0:FULL_CREATION_INFO},{0:WO_EN_CREATION_INFO}], {'exception': False, 'triplets_count': 2, 'nodes_count': 3}],
    # 5.4 thesis -[episodic]> episodic
    [[[EPISODIC_TRIPLET3], [EPISODIC_TRIPLET4]], [{0:FULL_CREATION_INFO},{0:WO_EN_CREATION_INFO}], {'exception': False, 'triplets_count': 2, 'nodes_count': 3}],
    # 6. добавление одного триплета (связь и конечная вершина c заданным creation_info)
    # 6.1 object <[simple]- object
    [[[SIMPLE_TRIPLET1], [SIMPLE_TRIPLET2]], [{0:FULL_CREATION_INFO},{0:WO_SN_CREATION_INFO}], {'exception': False, 'triplets_count': 2, 'nodes_count': 3}],
    # 6.2 thesis <[hyper]- object
    [[[SIMPLE_TRIPLET1], [THESIS_TRIPLET1]], [{0:FULL_CREATION_INFO},{0:WO_SN_CREATION_INFO}], {'exception': False, 'triplets_count': 2, 'nodes_count': 3}],
    # 6.3 episodic <[episodic]- object
    [[[SIMPLE_TRIPLET1], [EPISODIC_TRIPLET1]], [{0:FULL_CREATION_INFO},{0:WO_SN_CREATION_INFO}], {'exception': False, 'triplets_count': 2, 'nodes_count': 3}],
    # 6.4 episodic <[episodic]- thesis
    [[[THESIS_TRIPLET3], [EPISODIC_TRIPLET4]], [{0:FULL_CREATION_INFO},{0:WO_SN_CREATION_INFO}], {'exception': False, 'triplets_count': 2, 'nodes_count': 3}],
    # 7. добавление несколько разных триплетов (полностью c заданным creation_info)
    # 7.1 simple and simple
    [[[SIMPLE_TRIPLET1, SIMPLE_TRIPLET4]], [{0:FULL_CREATION_INFO, 1:FULL_CREATION_INFO}], {'exception': False, 'triplets_count': 2, 'nodes_count': 4}],
    # 7.2 simple and hyper
    [[[SIMPLE_TRIPLET1, THESIS_TRIPLET3]], [{0:FULL_CREATION_INFO, 1:FULL_CREATION_INFO}], {'exception': False, 'triplets_count': 2, 'nodes_count': 4}],
    # 7.3 hyper and episodic
    [[[THESIS_TRIPLET1, EPISODIC_TRIPLET2]], [{0:FULL_CREATION_INFO, 1:FULL_CREATION_INFO}], {'exception': False, 'triplets_count': 2, 'nodes_count': 4}],
    # 7.4 simple and episodic
    [[[SIMPLE_TRIPLET4, EPISODIC_TRIPLET1]], [{0:FULL_CREATION_INFO, 1:FULL_CREATION_INFO}], {'exception': False, 'triplets_count': 2, 'nodes_count': 4}],
    # 8. добавление нескольких связанных триплетов без creation info
    [[[SIMPLE_TRIPLET1, SIMPLE_TRIPLET2]], [{}], {'exception': False, 'triplets_count': 3, 'nodes_count': 4}]
]

GRAPHDB_POPULATED_CREATE_TEST_CASES = []
for db_vendor in AVAILABLE_GRAPH_DBS:
    for i in range(len(GRAPHDB_CREATE_TEST_CASES)):
        GRAPHDB_POPULATED_CREATE_TEST_CASES.append(GRAPHDB_CREATE_TEST_CASES[i] + [db_vendor])

###############################################################################################

GRAPHDB_DELETE_TEST_CASES = [
    # 1. пустой список
    [[SIMPLE_TRIPLET3, SIMPLE_TRIPLET4], {0:FULL_CREATION_INFO, 1:WO_SN_CREATION_INFO},
     [], dict(), {'exception': False, 'triplets_count': 2, 'nodes_count': 3}],
    # 2. один существующий триплет (удаляется связь и вершины)
    [[SIMPLE_TRIPLET1, SIMPLE_TRIPLET4], {0:FULL_CREATION_INFO, 1:FULL_CREATION_INFO},
     [SIMPLE_TRIPLET1.id], dict(),
     {'exception': False, 'triplets_count': 1, 'nodes_count': 2}],
    # 3. один существующий триплет (удаляется только связь)
    [[SIMPLE_TRIPLET1, SIMPLE_TRIPLET2, SIMPLE_TRIPLET3],
     {0:FULL_CREATION_INFO, 1:WO_SN_CREATION_INFO, 2:ONLY_REL_CREATION_INFO},
     [SIMPLE_TRIPLET3.id], {0: {'s_node': False, 'e_node': False}},
     {'exception': False, 'triplets_count': 2, 'nodes_count': 3}],
    # 4. один несуществующий триплет
    [[SIMPLE_TRIPLET1], {0:FULL_CREATION_INFO},
     [SIMPLE_TRIPLET2.id], dict(), {'exception': False, 'triplets_count': 1, 'nodes_count': 2}],
    # 5. несколько триплетов (на удаление связи; связи и вершины; связи и вершин)
    [[SIMPLE_TRIPLET1, SIMPLE_TRIPLET3, THESIS_TRIPLET2, EPISODIC_TRIPLET2],
     {0:FULL_CREATION_INFO, 1:WO_EN_CREATION_INFO, 2:WO_SN_CREATION_INFO, 3:WO_SN_CREATION_INFO},
     [SIMPLE_TRIPLET1.id, THESIS_TRIPLET2.id, EPISODIC_TRIPLET2.id],
     {0: {'s_node': False, 'e_node': False}, 1: {'s_node': False, 'e_node': True}, 2: {'s_node': True, 'e_node': True}},
     {'exception': False, 'triplets_count': 1, 'nodes_count': 2}],
    # 6. несколько триплетов (на удаление связи; удаление несуществующего триплета; удаление связи и вершины)
    [[SIMPLE_TRIPLET1, SIMPLE_TRIPLET3, THESIS_TRIPLET2, EPISODIC_TRIPLET2],
     {0:FULL_CREATION_INFO, 1:WO_EN_CREATION_INFO, 2:WO_SN_CREATION_INFO, 3:WO_SN_CREATION_INFO},
     [SIMPLE_TRIPLET1.id, 'unknow_id', THESIS_TRIPLET2.id],
     {0: {'s_node': False, 'e_node': False}, 2: {'s_node': False, 'e_node': True}},
     {'exception': False, 'triplets_count': 2, 'nodes_count': 4}],
    # 7. неверный формат идентификатора 1
    [[SIMPLE_TRIPLET1], {0:FULL_CREATION_INFO}, [123], dict(),
      {'exception': True, 'triplets_count': 1, 'nodes_count': 2}],
    # 8. неверный формат идентификатора 2
    [[SIMPLE_TRIPLET1], {0:FULL_CREATION_INFO}, [True], dict(),
      {'exception': True, 'triplets_count': 1, 'nodes_count': 2}],
    # 9. неверный формат идентификатора 3
    [[SIMPLE_TRIPLET1], {0:FULL_CREATION_INFO}, [None], dict(),
      {'exception': True, 'triplets_count': 1, 'nodes_count': 2}]
]

GRAPHDB_POPULATED_DELETE_TEST_CASES = []
for db_vendor in AVAILABLE_GRAPH_DBS:
    for i in range(len(GRAPHDB_DELETE_TEST_CASES)):
        GRAPHDB_POPULATED_DELETE_TEST_CASES.append(GRAPHDB_DELETE_TEST_CASES[i] + [db_vendor])

###############################################################################################

GRAPHDB_READ_TEST_CASES = [
    # 1. пустой список
    [[SIMPLE_TRIPLET1,SIMPLE_TRIPLET2], {0:FULL_CREATION_INFO, 1:WO_SN_CREATION_INFO}, [], {'exception': False, 'output_ids': set()}],
    # 2. один существующий триплет
    [[SIMPLE_TRIPLET1,SIMPLE_TRIPLET2], {0:FULL_CREATION_INFO, 1:WO_SN_CREATION_INFO}, [SIMPLE_TRIPLET1.id], {'exception': False, 'output_ids': {SIMPLE_TRIPLET1.id}}],
    # 3. один несуществующий триплет
    [[SIMPLE_TRIPLET1,SIMPLE_TRIPLET2], {0:FULL_CREATION_INFO, 1:WO_SN_CREATION_INFO}, [SIMPLE_TRIPLET3.id], {'exception': False, 'output_ids': set()}],
    # 4. несколько существующих триплетов
    [[SIMPLE_TRIPLET1,SIMPLE_TRIPLET2], {0:FULL_CREATION_INFO, 1:WO_SN_CREATION_INFO}, [SIMPLE_TRIPLET1.id, SIMPLE_TRIPLET2.id], {'exception': False, 'output_ids': {SIMPLE_TRIPLET1.id, SIMPLE_TRIPLET2.id}}],
    # 5. в списке есть несуществующий идентификатор триплета
    [[SIMPLE_TRIPLET1,SIMPLE_TRIPLET2], {0:FULL_CREATION_INFO, 1:WO_SN_CREATION_INFO}, [SIMPLE_TRIPLET1.id, SIMPLE_TRIPLET3.id], {'exception': False, 'output_ids': {SIMPLE_TRIPLET1.id}}],
    # 6. неверный формат идентификатора 1
    [[SIMPLE_TRIPLET1,SIMPLE_TRIPLET2], {0:FULL_CREATION_INFO, 1:WO_SN_CREATION_INFO}, [123], {'exception': True, 'output_ids': set()}],
    # 7. неверный формат идентификатора 2
    [[SIMPLE_TRIPLET1,SIMPLE_TRIPLET2], {0:FULL_CREATION_INFO, 1:WO_SN_CREATION_INFO}, [True], {'exception': True, 'output_ids': set()}],
    # 8. неверный формат идентификатора 3
    [[SIMPLE_TRIPLET1,SIMPLE_TRIPLET2], {0:FULL_CREATION_INFO, 1:WO_SN_CREATION_INFO}, [None], {'exception': True, 'output_ids': set()}]
]

GRAPHDB_POPULATED_READ_TEST_CASES = []
for db_vendor in AVAILABLE_GRAPH_DBS:
    for i in range(len(GRAPHDB_READ_TEST_CASES)):
        GRAPHDB_POPULATED_READ_TEST_CASES.append(GRAPHDB_READ_TEST_CASES[i] + [db_vendor])

###############################################################################################

GRAPHDB_COUNT_TEST_CASES = [
    # 1. нуль элементов
    [[], {}, {'triplets_count': 0, 'nodes_count': 0}],
    # 2. один элемент
    [[SIMPLE_TRIPLET1], {}, {'triplets_count': 1, 'nodes_count': 2}],
    # 3. несколько элементов с creation_info = None
    [[SIMPLE_TRIPLET1,SIMPLE_TRIPLET2], {}, {'triplets_count': 3, 'nodes_count': 4}],
    # 4. несколько элементов с меками объектов-дубликатов (creation_info != None)
    [[SIMPLE_TRIPLET1, SIMPLE_TRIPLET2], {0:FULL_CREATION_INFO, 1:WO_SN_CREATION_INFO}, {'triplets_count': 2, 'nodes_count': 3}]
]

GRAPHDB_POPULATED_COUNT_TEST_CASES = []
for db_vendor in AVAILABLE_GRAPH_DBS:
    for i in range(len(GRAPHDB_COUNT_TEST_CASES)):
        GRAPHDB_POPULATED_COUNT_TEST_CASES.append(GRAPHDB_COUNT_TEST_CASES[i] + [db_vendor])

###############################################################################################

GRAPHDB_EXIST_TEST_CASES = [
    # 1. элемент существует
    [[SIMPLE_TRIPLET1, EPISODIC_TRIPLET3], SIMPLE_TRIPLET1.id, {'exception': False, 'exist': True, 'type': 'triplet'}],
    # 2. элемента не существует
    [[SIMPLE_TRIPLET1, EPISODIC_TRIPLET3], 'unknown_id', {'exception': False, 'exist': False, 'type': 'triplet'}],
    # 3. неверный формат идентификатора # 1
    [[SIMPLE_TRIPLET1, EPISODIC_TRIPLET3], 789, {'exception': True, 'exist': False, 'type': 'triplet'}],
    # 4. неверный формат идентификатора # 2
    [[SIMPLE_TRIPLET1, EPISODIC_TRIPLET3], False, {'exception': True, 'exist': False, 'type': 'triplet'}],
    # 5. неверный формат идентификатора # 3
    [[SIMPLE_TRIPLET1, EPISODIC_TRIPLET3], None, {'exception': True, 'exist': False, 'type': 'triplet'}],
    # 6. Вершина существует
    [[SIMPLE_TRIPLET1, EPISODIC_TRIPLET3], OBJECT_NODE1.id, {'exception': False, 'exist': True, 'type': 'node'}],
    # 7. Вершины не существует
    [[SIMPLE_TRIPLET1, EPISODIC_TRIPLET3], OBJECT_NODE4.id, {'exception': False, 'exist': False, 'type': 'node'}]
]

GRAPHDB_POPULATED_EXIST_TEST_CASES = []
for db_vendor in AVAILABLE_GRAPH_DBS:
    for i in range(len(GRAPHDB_EXIST_TEST_CASES)):
        GRAPHDB_POPULATED_EXIST_TEST_CASES.append(GRAPHDB_EXIST_TEST_CASES[i] + [db_vendor])

###############################################################################################

GRAPHDB_CLEAR_TEST_CASES = [
    # 1. чистка пустой бд
    [[], {'triplets_count': 0, 'nodes_count': 0}],
    # 2. чистка бд с одним триплетом
    # 2.1. simple
    [[SIMPLE_TRIPLET1], {'triplets_count': 1, 'nodes_count': 2}],
    # 2.2. thesis with object
    [[THESIS_TRIPLET1], {'triplets_count': 1, 'nodes_count': 2}],
    # 2.3. episodic with object
    [[EPISODIC_TRIPLET1], {'triplets_count': 1, 'nodes_count': 2}],
    # 2.4. episodic with thesis
    [[EPISODIC_TRIPLET4], {'triplets_count': 1, 'nodes_count': 2}],
    # 3. чиста бд с несколькими элементами
    [[SIMPLE_TRIPLET1, THESIS_TRIPLET1, EPISODIC_TRIPLET1, EPISODIC_TRIPLET4], {'triplets_count': 7, 'nodes_count': 8}]
]

GRAPHDB_POPULATED_CLEAR_TEST_CASES = []
for db_vendor in AVAILABLE_GRAPH_DBS:
    for i in range(len(GRAPHDB_CLEAR_TEST_CASES)):
        GRAPHDB_POPULATED_CLEAR_TEST_CASES.append(GRAPHDB_CLEAR_TEST_CASES[i] + [db_vendor])

###############################################################################################

GRAPHDB_GET_ADJECENT_TEST_CASES = [
    # 1. одна смежная вершина
    [[SIMPLE_TRIPLET1, SIMPLE_TRIPLET2],{0:FULL_CREATION_INFO, 1:WO_SN_CREATION_INFO}, OBJECT_NODE1.id, ALL_N_TYPES, {'exception': False, 'output_ids': {OBJECT_NODE2.id}}],
    # 2. несколько смежных вершин
    [[SIMPLE_TRIPLET1, SIMPLE_TRIPLET2],{0:FULL_CREATION_INFO, 1:WO_SN_CREATION_INFO}, OBJECT_NODE2.id, ALL_N_TYPES, {'exception': False, 'output_ids': {OBJECT_NODE1.id, OBJECT_NODE3.id}}],
    # 3. несуществующий идентифкатор
    [[SIMPLE_TRIPLET1, SIMPLE_TRIPLET2],{0:FULL_CREATION_INFO, 1:WO_SN_CREATION_INFO}, OBJECT_NODE4.id, ALL_N_TYPES, {'exception': False, 'output_ids': set()}],
    # 4. неверный формат идентификатора 1
    [[SIMPLE_TRIPLET1, SIMPLE_TRIPLET2],{0:FULL_CREATION_INFO, 1:WO_SN_CREATION_INFO}, 123, ALL_N_TYPES, {'exception': True, 'output_ids': set()}],
    # 5. неверный формат идентификатора 2
    [[SIMPLE_TRIPLET1, SIMPLE_TRIPLET2],{0:FULL_CREATION_INFO, 1:WO_SN_CREATION_INFO}, True, ALL_N_TYPES, {'exception': True, 'output_ids': set()}],
    # 6. неверный формат идентификатора 3
    [[SIMPLE_TRIPLET1, SIMPLE_TRIPLET2],{0:FULL_CREATION_INFO, 1:WO_SN_CREATION_INFO}, None, ALL_N_TYPES, {'exception': True, 'output_ids': set()}]
]

GRAPHDB_POPULATED_GET_ADJECENT_TEST_CASES = []
for db_vendor in AVAILABLE_GRAPH_DBS:
    for i in range(len(GRAPHDB_GET_ADJECENT_TEST_CASES)):
        GRAPHDB_POPULATED_GET_ADJECENT_TEST_CASES.append(GRAPHDB_GET_ADJECENT_TEST_CASES[i] + [db_vendor])

###############################################################################################

GRAPHDB_GET_TRIPLETS_TEST_CASES = [
    # 1. между нодами нет связей
    [[SIMPLE_TRIPLET1, SIMPLE_TRIPLET4],{0:FULL_CREATION_INFO, 1:FULL_CREATION_INFO}, (OBJECT_NODE1.id,OBJECT_NODE3.id), {
        'exception': False, 'exist': [True,True], 'output_ids': set(), 'count': 0, 'triplets': 2, 'nodes': 4}],
    # 2.между нодами одна связь
    # 2.1 циклическая связь
    [[SIMPLE_TRIPLET5],{0:WO_EN_CREATION_INFO}, (OBJECT_NODE1.id,OBJECT_NODE1.id), {
        'exception': False, 'exist': [True,True],'output_ids': {SIMPLE_TRIPLET5.id}, 'count': 1, 'triplets': 1, 'nodes': 1}],
    # 2.2 между разными вершинами
    [[SIMPLE_TRIPLET1],{0:FULL_CREATION_INFO}, (OBJECT_NODE1.id,OBJECT_NODE2.id), {
        'exception': False, 'exist': [True,True],'output_ids': {SIMPLE_TRIPLET1.id}, 'count': 1, 'triplets': 1, 'nodes': 2}],
    # 3.между нодами несколько связей
    [[SIMPLE_TRIPLET1, SIMPLE_TRIPLET1_2], {0:FULL_CREATION_INFO, 1:ONLY_REL_CREATION_INFO}, (OBJECT_NODE1.id, OBJECT_NODE2.id), {
        'exception': False, 'exist': [True,True], 'output_ids': {SIMPLE_TRIPLET1.id, SIMPLE_TRIPLET1_2.id}, 'count': 2, 'triplets': 2, 'nodes': 2}],
    # 4.несуществующий идентифкатор
    # 4.1 стартовый
    [[SIMPLE_TRIPLET1],{0:FULL_CREATION_INFO}, ('unkown_id', OBJECT_NODE1.id), {
        'exception': True, 'exist': [False,True], 'output_ids': {}, 'count': 0, 'triplets': 1, 'nodes': 2}],
    # 4.2 конечный
    [[SIMPLE_TRIPLET1],{0:FULL_CREATION_INFO}, (OBJECT_NODE1.id, 'unknown_id'), {
        'exception': True, 'exist': [True,False], 'output_ids': {}, 'count': 0, 'triplets': 1, 'nodes': 2}],
    # 4.3 оба
    [[SIMPLE_TRIPLET1],{0:FULL_CREATION_INFO}, ('unknown_id', 'unknown_id'), {
        'exception': True, 'exist': [False, False], 'output_ids': {}, 'count': 0, 'triplets': 1, 'nodes': 2}],
    # 5.неверный формат идентификатора 1
    [[SIMPLE_TRIPLET1],{0:FULL_CREATION_INFO}, (OBJECT_NODE1.id, 123), {
        'exception': True, 'exist': [True,None], 'output_ids': {}, 'count': 0, 'triplets': 1, 'nodes': 2}],
    # 6.неверный формат идентификатора 2
    [[SIMPLE_TRIPLET1],{0:FULL_CREATION_INFO}, (OBJECT_NODE1.id, True), {
        'exception': True, 'exist': [True,None], 'output_ids': {}, 'count': 0, 'triplets': 1, 'nodes': 2}],
    # 7.неверный формат идентификатора 3
    [[SIMPLE_TRIPLET1],{0:FULL_CREATION_INFO}, (OBJECT_NODE1.id, None), {
        'exception': True, 'exist': [True,None], 'output_ids': {}, 'count': 0, 'triplets': 1, 'nodes': 2}]
]

GRAPHDB_POPULATED_GET_TRIPLETS_TEST_CASES = []
for db_vendor in AVAILABLE_GRAPH_DBS:
    for i in range(len(GRAPHDB_GET_TRIPLETS_TEST_CASES)):
        GRAPHDB_POPULATED_GET_TRIPLETS_TEST_CASES.append(GRAPHDB_GET_TRIPLETS_TEST_CASES[i] + [db_vendor])

###############################################################################################

# instances, create_info, init_count, name, type, object, expected_output, exception

from src.utils.data_structs import NodeType, RelationType


GRAPHDB_READ_BY_NAME_TEST_CASES = [
    # 1. NODE - OBJECT
    # объектов с таким именем (name) не существует
    [[THESIS_TRIPLET1, SIMPLE_TRIPLET1], {0: {'s_node': True, 'e_node': True}, 1: {'s_node': False, 'e_node': True}},
     {'triplets': 2, 'nodes': 3}, 'not existing name', NodeType.object, 'node', [], False],
    # объектов с таким типом (type) не существует
    [[EPISODIC_TRIPLET4], {0: {'s_node': True, 'e_node': True}},
     {'triplets': 1, 'nodes': 2}, EPISODIC_TRIPLET4.start_node.name, NodeType.object, 'node', [], False],
    # такие объекты (node) отсутствуют
    [[], dict(), {'triplets': 0, 'nodes': 0}, "may existing name",
     NodeType.object, 'node', [], False],
    # невалидный тип (type)
    [[THESIS_TRIPLET1], {0: {'s_node': True, 'e_node': True}}, {'triplets': 1, 'nodes': 2},
     THESIS_TRIPLET1.start_node.name, 'not valid type', 'node', None, True],
    # невалидный объект (object)
    [[THESIS_TRIPLET1], {0: {'s_node': True, 'e_node': True}}, {'triplets': 1, 'nodes': 2},
     THESIS_TRIPLET1.start_node.name, NodeType.object, 'not valid object', None, True],
    # бд пустая
    [[], dict(), {'triplets': 0, 'nodes': 0}, THESIS_TRIPLET1.start_node.name, NodeType.object, 'node', [], False],
    # найден один объект
    [[THESIS_TRIPLET1, SIMPLE_TRIPLET1], {0:{'s_node': True, 'e_node': True}, 1:{'s_node': False, 'e_node': True}},
     {'triplets': 2, 'nodes': 3}, THESIS_TRIPLET1.start_node.name, NodeType.object, 'node', [THESIS_TRIPLET1.start_node], False],
    # найдено несколько объектов
    [[SIMPLE_TRIPLET1_3, SIMPLE_TRIPLET1], {0: {'s_node': True, 'e_node': True}, 1:{'s_node': False, 'e_node': True}},
     {'triplets': 2, 'nodes': 3}, SIMPLE_TRIPLET1_3.start_node.name, NodeType.object, 'node', [SIMPLE_TRIPLET1_3.start_node, SIMPLE_TRIPLET1_3.end_node], False],
    # поле name имеет пустое значение
    [[THESIS_TRIPLET1, SIMPLE_TRIPLET1], {0:{'s_node': True, 'e_node': True}, 1:{'s_node': False, 'e_node': True}},
     {'triplets': 2, 'nodes': 3}, '', NodeType.object, 'node', None, True],
    # поле name имее нвалидный тип (не str)
    [[THESIS_TRIPLET1, SIMPLE_TRIPLET1], {0:{'s_node': True, 'e_node': True}, 1:{'s_node': False, 'e_node': True}},
      {'triplets': 2, 'nodes': 3}, 123, NodeType.object, 'node', None, True],
    [[THESIS_TRIPLET1, SIMPLE_TRIPLET1], {0:{'s_node': True, 'e_node': True}, 1:{'s_node': False, 'e_node': True}},
     {'triplets': 2, 'nodes': 3}, None, NodeType.object, 'node', None, True],

    # 2. NODE - HYPER
    # TODO

    # 3. NODE - EPISODIC
    # объектов с таким именем (name) не существует
    [[EPISODIC_TRIPLET2], {0:{'s_node': True, 'e_node': True}},
     {'triplets': 1, 'nodes': 2}, 'not existing name', NodeType.episodic, 'node', [], False],
    # объектов с таким типом (type) не существует
    [[THESIS_TRIPLET1], {0:{'s_node': True, 'e_node': True}},
     {'triplets': 1, 'nodes': 2}, THESIS_TRIPLET1.start_node.name, NodeType.episodic, 'node', [], False],
    # такие объекты (node) отсутствуют
    [[], dict(), {'triplets': 0, 'nodes': 0}, "may existing name", NodeType.episodic, 'node', [], False],
    # невалидный тип (type)
    [[EPISODIC_TRIPLET2], {0:{'s_node': True, 'e_node': True}},
     {'triplets': 1, 'nodes': 2}, EPISODIC_TRIPLET2.end_node.name, 'not valid type', 'node', None, True],
    # невалидный объект (object)
    [[EPISODIC_TRIPLET2], {0:{'s_node': True, 'e_node': True}},
     {'triplets': 1, 'nodes': 2}, EPISODIC_TRIPLET2.end_node.name, NodeType.episodic, 'not valid object', None, True],
    # бд пустая
    [[], dict(), {'triplets': 0, 'nodes': 0}, 'may existing name', NodeType.episodic, 'node', [], False],
    # найден один объект
    [[EPISODIC_TRIPLET2], {0:{'s_node': True, 'e_node': True}}, {'triplets': 1, 'nodes': 2},
     EPISODIC_TRIPLET2.end_node.name, NodeType.episodic, 'node', [EPISODIC_TRIPLET2.end_node], False],
    # найдено несколько объектов
    [[EPISODIC_TRIPLET1, EPISODIC_TRIPLET1_2], {0:{'s_node': True, 'e_node': True}, 1:{'s_node': False, 'e_node': True}},
      {'triplets': 2, 'nodes': 3}, EPISODIC_TRIPLET1.end_node.name, NodeType.episodic, 'node', [EPISODIC_TRIPLET1.end_node, EPISODIC_TRIPLET1_2.end_node], False],
    # поле name имеет пустое значение
    [[EPISODIC_TRIPLET2], {0:{'s_node': True, 'e_node': True}},
     {'triplets': 1, 'nodes': 2}, '', NodeType.episodic, 'node', None, True],
    # поле name имее нвалидный тип (не str)
    [[EPISODIC_TRIPLET2], {0:{'s_node': True, 'e_node': True}},
     {'triplets': 1, 'nodes': 2}, 123, NodeType.episodic, 'node', None, True],
    [[EPISODIC_TRIPLET2], {0:{'s_node': True, 'e_node': True}},
     {'triplets': 1, 'nodes': 2}, None, NodeType.episodic, 'node', None, True],

    # 4. RELATION - SIMPLE
    # TODO

    # 5. REALTION - HYPER
    # TODO

    # 6. RELATION - EPISODIC
    # объектов с таким именем (name) не существует
    [[EPISODIC_TRIPLET2], {0:{'s_node': True, 'e_node': True}},
     {'triplets': 1, 'nodes': 2}, 'not existing name', RelationType.episodic, 'relation', [], False],
    # объектов с таким типом (type) не существует
    [[THESIS_TRIPLET1], {0:{'s_node': True, 'e_node': True}},
     {'triplets': 1, 'nodes': 2}, THESIS_TRIPLET1.relation.name, RelationType.episodic, 'relation', [], False],
    # такие объекты (realation) отсутствуют
    [[], dict(), {'triplets': 0, 'nodes': 0}, "may existing name", RelationType.episodic, 'relation', [], False],
    # невалидный тип (type)
    [[EPISODIC_TRIPLET2], {0:{'s_node': True, 'e_node': True}},
     {'triplets': 1, 'nodes': 2}, EPISODIC_TRIPLET2.relation.name, 'not valid type', 'relation', None, True],
    # невалидный объект (object)
    [[EPISODIC_TRIPLET2], {0:{'s_node': True, 'e_node': True}},
     {'triplets': 1, 'nodes': 2}, EPISODIC_TRIPLET2.relation.name, RelationType.episodic, 'not valid object', None, True],
    # бд пустая
    [[], dict(), {'triplets': 0, 'nodes': 0}, 'may existing name', RelationType.episodic, 'relation', [], False],
    # найден один объект
    [[EPISODIC_TRIPLET2], {0:{'s_node': True, 'e_node': True}},
     {'triplets': 1, 'nodes': 2}, EPISODIC_TRIPLET2.relation.name, RelationType.episodic, 'relation', [EPISODIC_TRIPLET2], False],
    # найдено несколько объектов
    [[EPISODIC_TRIPLET1, EPISODIC_TRIPLET1_2], {0:{'s_node': True, 'e_node': True}, 1:{'s_node': False, 'e_node': True}},
      {'triplets': 2, 'nodes': 3}, EPISODIC_TRIPLET1.relation.name, RelationType.episodic, 'relation', [EPISODIC_TRIPLET1, EPISODIC_TRIPLET1_2], False],
    # поле name имеет пустое значение
    [[EPISODIC_TRIPLET2], {0: {'s_node': True, 'e_node': True}},
     {'triplets': 1, 'nodes': 2}, '', RelationType.episodic, 'relation', None, True],
    # поле name имее нвалидный тип (не str)
    [[EPISODIC_TRIPLET2], {0: {'s_node': True, 'e_node': True}},
     {'triplets': 1, 'nodes': 2}, 123, RelationType.episodic, 'relation', None, True],
    [[EPISODIC_TRIPLET2], {0: {'s_node': True, 'e_node': True}},
     {'triplets': 1, 'nodes': 2}, None, RelationType.episodic, 'relation', None, True]
]

GRAPHDB_POPULATED_READ_BY_NAME_TEST_CASES = []
for db_vendor in AVAILABLE_GRAPH_DBS:
    for i in range(len(GRAPHDB_READ_BY_NAME_TEST_CASES)):
        GRAPHDB_POPULATED_READ_BY_NAME_TEST_CASES.append(GRAPHDB_READ_BY_NAME_TEST_CASES[i] + [db_vendor])

###############################################################################################

GET_NSHARED_IDS_SIMPLE_GRAPH = [
    [SIMPLE_TRIPLET1, SIMPLE_TRIPLET1_2, SIMPLE_TRIPLET1_3],
    {0: FULL_CREATION_INFO, 1: ONLY_REL_CREATION_INFO, 2: WO_SN_CREATION_INFO}, (3, 3)]

# instances, create_info, graph_info, node1_id, node2_id, id_type, expected_output, exception
GRAPHDB_GET_NSHARED_IDS_TEST_CASES = [
    # 1 невалидный тип идентифиаторов вершин
    # 1.1 первая вершина
    (GET_NSHARED_IDS_SIMPLE_GRAPH[0], GET_NSHARED_IDS_SIMPLE_GRAPH[1], GET_NSHARED_IDS_SIMPLE_GRAPH[2],
     123, GET_NSHARED_IDS_SIMPLE_GRAPH[0][0].start_node.id, 'both', None, True),
    # 1.2 вторая вершина
    (GET_NSHARED_IDS_SIMPLE_GRAPH[0], GET_NSHARED_IDS_SIMPLE_GRAPH[1], GET_NSHARED_IDS_SIMPLE_GRAPH[2],
     GET_NSHARED_IDS_SIMPLE_GRAPH[0][0].start_node.id, 123, 'both', None, True),
    # 2. невалидное id_type-значение
    # 2.1 число
    (GET_NSHARED_IDS_SIMPLE_GRAPH[0], GET_NSHARED_IDS_SIMPLE_GRAPH[1], GET_NSHARED_IDS_SIMPLE_GRAPH[2],
     GET_NSHARED_IDS_SIMPLE_GRAPH[0][0].start_node.id, GET_NSHARED_IDS_SIMPLE_GRAPH[0][0].end_node.id, 123654, None, True),
    # 2.2 None
    (GET_NSHARED_IDS_SIMPLE_GRAPH[0], GET_NSHARED_IDS_SIMPLE_GRAPH[1], GET_NSHARED_IDS_SIMPLE_GRAPH[2],
     GET_NSHARED_IDS_SIMPLE_GRAPH[0][0].start_node.id, GET_NSHARED_IDS_SIMPLE_GRAPH[0][0].end_node.id, None, None, True),
    # 2.3 значение
    (GET_NSHARED_IDS_SIMPLE_GRAPH[0], GET_NSHARED_IDS_SIMPLE_GRAPH[1], GET_NSHARED_IDS_SIMPLE_GRAPH[2],
     GET_NSHARED_IDS_SIMPLE_GRAPH[0][0].start_node.id, GET_NSHARED_IDS_SIMPLE_GRAPH[0][0].end_node.id, "not_supported_type", None, True),
    # 3 вершины с таким id нет в бд
    # 3.1 перая вершина
    (GET_NSHARED_IDS_SIMPLE_GRAPH[0], GET_NSHARED_IDS_SIMPLE_GRAPH[1], GET_NSHARED_IDS_SIMPLE_GRAPH[2],
     OBJECT_NODE4.id, GET_NSHARED_IDS_SIMPLE_GRAPH[0][0].end_node.id, "both", [], False),
    # 3.2 вторая вершина
    (GET_NSHARED_IDS_SIMPLE_GRAPH[0], GET_NSHARED_IDS_SIMPLE_GRAPH[1], GET_NSHARED_IDS_SIMPLE_GRAPH[2],
     GET_NSHARED_IDS_SIMPLE_GRAPH[0][0].start_node.id, OBJECT_NODE4.id, "both", [], False),
    # 4 между вершинами нет связей
    # 4.1 у вершин есть другие связи
    (GET_NSHARED_IDS_SIMPLE_GRAPH[0], GET_NSHARED_IDS_SIMPLE_GRAPH[1], GET_NSHARED_IDS_SIMPLE_GRAPH[2],
     GET_NSHARED_IDS_SIMPLE_GRAPH[0][0].end_node.id, GET_NSHARED_IDS_SIMPLE_GRAPH[0][-1].end_node.id, "both", [], False),
    # 4.2 у вершин нет других связей
    # TO THINK
    # 5 между вершинами одна связь
    # 5.1 у вершин есть/нет другие связи
    (GET_NSHARED_IDS_SIMPLE_GRAPH[0], GET_NSHARED_IDS_SIMPLE_GRAPH[1], GET_NSHARED_IDS_SIMPLE_GRAPH[2],
     GET_NSHARED_IDS_SIMPLE_GRAPH[0][-1].start_node.id, GET_NSHARED_IDS_SIMPLE_GRAPH[0][-1].end_node.id, "both",
    [{'t_id': GET_NSHARED_IDS_SIMPLE_GRAPH[0][-1].id, 'r_id': GET_NSHARED_IDS_SIMPLE_GRAPH[0][-1].relation.id}], False),
    # 6 между вершинами несколько связей
    # 6.1 у вершин есть/нет другие связи
    (GET_NSHARED_IDS_SIMPLE_GRAPH[0], GET_NSHARED_IDS_SIMPLE_GRAPH[1], GET_NSHARED_IDS_SIMPLE_GRAPH[2],
     GET_NSHARED_IDS_SIMPLE_GRAPH[0][0].start_node.id, GET_NSHARED_IDS_SIMPLE_GRAPH[0][0].end_node.id, "both",
    [{'t_id': GET_NSHARED_IDS_SIMPLE_GRAPH[0][0].id, 'r_id': GET_NSHARED_IDS_SIMPLE_GRAPH[0][0].relation.id},
     {'t_id': GET_NSHARED_IDS_SIMPLE_GRAPH[0][1].id, 'r_id': GET_NSHARED_IDS_SIMPLE_GRAPH[0][1].relation.id}], False),
    # 7 между вершинами несколько триплетов с одинаковым relation_id
    # TO THINK
    # 8 Возвращается определённая информация
    # 8.1 triplet
    (GET_NSHARED_IDS_SIMPLE_GRAPH[0], GET_NSHARED_IDS_SIMPLE_GRAPH[1], GET_NSHARED_IDS_SIMPLE_GRAPH[2],
     GET_NSHARED_IDS_SIMPLE_GRAPH[0][0].start_node.id, GET_NSHARED_IDS_SIMPLE_GRAPH[0][0].end_node.id, 'triplet',
    [{'t_id': GET_NSHARED_IDS_SIMPLE_GRAPH[0][0].id},
     {'t_id': GET_NSHARED_IDS_SIMPLE_GRAPH[0][1].id}], False),
    # 8.2 relation
    (GET_NSHARED_IDS_SIMPLE_GRAPH[0], GET_NSHARED_IDS_SIMPLE_GRAPH[1], GET_NSHARED_IDS_SIMPLE_GRAPH[2],
     GET_NSHARED_IDS_SIMPLE_GRAPH[0][0].start_node.id, GET_NSHARED_IDS_SIMPLE_GRAPH[0][0].end_node.id, 'relation',
    [{'r_id': GET_NSHARED_IDS_SIMPLE_GRAPH[0][0].relation.id},
     {'r_id': GET_NSHARED_IDS_SIMPLE_GRAPH[0][1].relation.id}], False)
]

GRAPHDB_POPULATED_GET_NSHARED_IDS_TEST_CASES = []
for db_vendor in AVAILABLE_GRAPH_DBS:
    for i in range(len(GRAPHDB_GET_NSHARED_IDS_TEST_CASES)):
        GRAPHDB_POPULATED_GET_NSHARED_IDS_TEST_CASES.append(GRAPHDB_GET_NSHARED_IDS_TEST_CASES[i] + (db_vendor,))
