import pytest

import sys
# TO CHANGE
PROJECT_BASE_DIR = '../'
TEST_VOLUME_DIR = './volumes'
sys.path.insert(0, PROJECT_BASE_DIR)

from src.db_drivers.kv_driver import KeyValueDriver, KeyValueDriverConfig, KVDBConnectionConfig

#!!!AVAILABLE KEYVALUE CONNECTIONS!!!#

@pytest.fixture(scope='package')
def inmemory_kv_conn():
    inmemorykv_config = KVDBConnectionConfig(
        params={'kvstore_dump_name': 'inmemory_store', 'load_from_disk': False, 'max_storage': 5e+8,
        'load_dump_dir': TEST_VOLUME_DIR, 'save_on_disk': True, 'save_dump_dir': TEST_VOLUME_DIR}, need_to_clear=True)

    driver_config = KeyValueDriverConfig(db_vendor='inmemory_kv', db_config=inmemorykv_config)
    return KeyValueDriver.connect(driver_config)

#@pytest.fixture(scope='package')
#def aerospike_conn():
#    aerospike_config = KVDBConnectionConfig(
#        host='localhost', port=3000, db_info={'db': 'personalai_db', 'table': 'personalai_table'},
#        need_to_clear=True)
#
#    driver_config = KeyValueDriverConfig(db_vendor='aerospike', db_config=aerospike_config)
#    return KeyValueDriver.connect(driver_config)

@pytest.fixture(scope='package')
def redis_conn():
    redis_config = KVDBConnectionConfig(host='localhost', port=6370, need_to_clear=True, db_info={'db': 0, 'table': 'test_collection'},
        params={'ss_name': 'sorted_node_pairs', 'hs_name': 'node_pairs', 'max_storage': 5e+8})

    driver_config = KeyValueDriverConfig(db_vendor='redis', db_config=redis_config)
    return KeyValueDriver.connect(driver_config)


@pytest.fixture(scope='package')
def mongo_conn():
    mongo_config = KVDBConnectionConfig(
        host='localhost', port=27010, db_info={'db': 'test_db', 'table': 'test_collection'},
        params={'username': 'user', 'password': 'pass', 'max_storage': -1}, need_to_clear=True)

    driver_config = KeyValueDriverConfig(db_vendor='mongo', db_config=mongo_config)
    return KeyValueDriver.connect(driver_config)

@pytest.fixture(scope='package')
def mixed_conn():
    redis_config = KVDBConnectionConfig(
        host='localhost', port=6370, need_to_clear=True, db_info={'db': 0, 'table': 'test_collection'},
        params={'ss_name': 'sorted_node_pairs', 'hs_name': 'node_pairs', 'max_storage': 5e+8})

    mongo_config = KVDBConnectionConfig(
        host='localhost', port=27010, db_info={'db': 'test_db', 'table': 'test_collection'},
        params={'username': 'user', 'password': 'pass', 'max_storage': -1},
        need_to_clear=True)

    mixed_config = KVDBConnectionConfig(params={'mongo_config': mongo_config, 'redis_config': redis_config})
    driver_config = KeyValueDriverConfig(db_vendor='mixed_kv', db_config=mixed_config)

    return KeyValueDriver.connect(driver_config)

#------------------------------#

@pytest.fixture(scope='package')
def available_keyvalue_connections(
    inmemory_kv_conn,
    redis_conn,
    mongo_conn,
    mixed_conn
):
    return {
        'inmemory_kv': inmemory_kv_conn,
        'redis': redis_conn,
        'mongo': mongo_conn,
        'mixed_kv': mixed_conn
    }

@pytest.fixture(scope='function')
def keyvaluedb_conn(available_keyvalue_connections, request):
    return available_keyvalue_connections[request.param]
