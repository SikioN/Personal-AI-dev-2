import pytest

import sys
# TO CHANGE
PROJECT_BASE_DIR = '../'
TEST_VOLUME_DIR = './volumes'
sys.path.insert(0, PROJECT_BASE_DIR)

from src.utils.data_structs import NodeType, RelationType
from src.db_drivers.graph_driver import GraphDriver, GraphDriverConfig, GraphDBConnectionConfig

#!!!AVAILABLE GRAPH CONNECTIONS!!!#

@pytest.fixture(scope='package')
def inmemory_graph_conn():
    config = GraphDriverConfig(db_vendor='inmemory_graph', db_config=GraphDBConnectionConfig(
        db_info={'db': 'testing', 'table': 'testing'}, need_to_clear=True))
    return GraphDriver.connect(config)

@pytest.fixture(scope='package')
def neo4j_conn():
    config = GraphDriverConfig(db_vendor='neo4j', db_config=GraphDBConnectionConfig(
        host="localhost", port="7680", db_info={'db': 'testing', 'table': 'testing'}, # host: personalai_mmenschikov_test_neo4j
        params={'user': "neo4j", 'pwd': 'password'}, need_to_clear=True))
    return GraphDriver.connect(config)

@pytest.fixture(scope='package')
def kuzu_conn():
    config = GraphDriverConfig(db_vendor='kuzu', db_config=GraphDBConnectionConfig(
        db_info={'db': 'testing', 'table': 'testing'},
        params={'path': f'{TEST_VOLUME_DIR}/kuzu', 'buffer_pool_size': 1024**3,
            'schema': [
                "CREATE NODE TABLE IF NOT EXISTS object (id SERIAL, name STRING, prop MAP(STRING, STRING), str_id STRING, PRIMARY KEY(id));",
                "CREATE NODE TABLE IF NOT EXISTS hyper (id SERIAL, name STRING, prop MAP(STRING, STRING), str_id STRING, PRIMARY KEY(id));",
                "CREATE NODE TABLE IF NOT EXISTS episodic (id SERIAL, name STRING, prop MAP(STRING, STRING), str_id STRING, PRIMARY KEY(id));",
                "CREATE REL TABLE IF NOT EXISTS simple (FROM object TO object, name STRING, t_id STRING, str_id STRING, prop MAP(STRING, STRING));",
                "CREATE REL TABLE IF NOT EXISTS hyper_rel (FROM object TO hyper, name STRING, t_id STRING, str_id STRING, prop MAP(STRING, STRING));",
                "CREATE REL TABLE GROUP IF NOT EXISTS episodic_rel (FROM object TO episodic, FROM hyper TO episodic, name STRING, t_id STRING, str_id STRING, prop MAP(STRING, STRING));"
            ],
            'table_type_map': {
                'relations': {'forward': {RelationType.simple.value: 'simple', RelationType.hyper.value: 'hyper_rel', RelationType.episodic.value: 'episodic_rel'},},
                'nodes': {'forward': {NodeType.object.value: 'object', NodeType.hyper.value: 'hyper', NodeType.episodic.value: 'episodic'}}
            }},
        need_to_clear=True
    ))
    return GraphDriver.connect(config)

#------------------------------#

@pytest.fixture(scope='package')
def available_graph_connections(
    inmemory_graph_conn,
    neo4j_conn,
   kuzu_conn
):
    return {
        'neo4j': neo4j_conn,
        'inmemory_graph': inmemory_graph_conn,
        'kuzu': kuzu_conn
    }

@pytest.fixture(scope='function')
def graphdb_conn(available_graph_connections, request):
    return available_graph_connections[request.param]
