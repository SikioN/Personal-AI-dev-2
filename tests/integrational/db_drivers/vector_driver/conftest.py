import pytest

import sys
# TO CHANGE
PROJECT_BASE_DIR = '../'
TEST_VOLUME_DIR = './volumes'
sys.path.insert(0, PROJECT_BASE_DIR)

from src.db_drivers.vector_driver import VectorDriver, VectorDriverConfig, VectorDBConnectionConfig

#!!!AVAILABLE VECTOR CONNECTIONS!!!#

@pytest.fixture(scope='package')
def chromadb_conn():
    config = VectorDriverConfig(db_vendor='chroma', db_config=VectorDBConnectionConfig(
            conn={'path':f"{TEST_VOLUME_DIR}/chroma"}, db_info={'db':'testing', 'table': 'testing'},
            params={"hnsw:space": "ip","hnsw:M": 4096}, need_to_clear=True))
    return VectorDriver.connect(config)

@pytest.fixture(scope='package')
def milvusdb_conn():
    config = VectorDriverConfig(db_vendor='milvus', db_config=VectorDBConnectionConfig(
        conn={'host': 'localhost', 'port': 19520, 'user': 'root', 'pass': 'Milvus'},
        db_info={'db': 'testing', 'table': 'testing'}, need_to_clear=True,
        params={'id_length': 32, 'vector_dim': 3, 'document_max_length': 51200,
                'load': True, 'flush': True, 'create_sleep': 1, 'search_metric': 'IP'}))
    return VectorDriver.connect(config)

#------------------------------#

@pytest.fixture(scope='package')
def available_vector_connections(
    chromadb_conn, milvusdb_conn):
    return {
        'chroma': chromadb_conn,
        'milvus': milvusdb_conn}

@pytest.fixture(scope='function')
def vectordb_conn(available_vector_connections, request):
    return available_vector_connections[request.param]
