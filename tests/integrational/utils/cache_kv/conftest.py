import pytest

import sys
# TO CHANGE
PROJECT_BASE_DIR = '../'
TEST_VOLUME_DIR = './volumes'
sys.path.insert(0, PROJECT_BASE_DIR)

from src.db_drivers.kv_driver import KeyValueDriverConfig, KVDBConnectionConfig
from src.utils.cache_kv import CacheKV

@pytest.fixture(scope='package')
def inmemory_kv_cache_conn():
    inmemorykv_config = KVDBConnectionConfig(
        params={'kvstore_dump_name': 'inmemory_cache_store', 'load_from_disk': False, 'max_storage': 5e+8,
        'load_dump_dir': TEST_VOLUME_DIR, 'save_on_disk': True, 'save_dump_dir': TEST_VOLUME_DIR}, need_to_clear=True)

    kvdriver_config = KeyValueDriverConfig(db_vendor='inmemory_kv', db_config=inmemorykv_config)
    return CacheKV(kvdriver_config)

@pytest.fixture(scope='package')
def redis_cache_conn():
    redis_config = KVDBConnectionConfig(host='localhost', port=6379, need_to_clear=True, db_info={'db': 0, 'table': 'test_cache_collection'},
        params={'ss_name': 'sorted_node_pairs', 'hs_name': 'node_pairs', 'max_storage': 5e+8})

    kvdriver_config = KeyValueDriverConfig(db_vendor='redis', db_config=redis_config)
    return CacheKV(kvdriver_config)


@pytest.fixture(scope='package')
def mongo_cache_conn():
    mongo_config = KVDBConnectionConfig(
        host='localhost', port=27017, db_info={'db': 'test_cache_db', 'table': 'test_cache_collection'},
        params={'username': 'user', 'password': 'pass', 'max_storage': -1}, need_to_clear=True)

    kvdriver_config = KeyValueDriverConfig(db_vendor='mongo', db_config=mongo_config)
    return CacheKV(kvdriver_config)

@pytest.fixture(scope='package')
def mixed_cache_conn():
    redis_config = KVDBConnectionConfig(
        host='localhost', port=6379,
        params={'ss_name': 'sorted_node_pairs', 'hs_name': 'node_pairs', 'max_storage': 5e+8})

    mongo_config = KVDBConnectionConfig(
        host='localhost', port=27017,
        params={'username': 'user', 'password': 'pass', 'max_storage': -1},
        need_to_clear=True)

    mixed_config = KVDBConnectionConfig(db_info={'db': 'test_cache_db', 'table': 'test_cache_collection'},
                                        need_to_clear=True, params={'mongo_config': mongo_config, 'redis_config': redis_config})
    kvdriver_config = KeyValueDriverConfig(db_vendor='mixed_kv', db_config=mixed_config)

    return CacheKV(kvdriver_config)

#------------------------------#

@pytest.fixture(scope='package')
def available_cachekv_connections(
    inmemory_kv_cache_conn,
    redis_cache_conn,
    mongo_cache_conn,
    mixed_cache_conn
):
    return {
        'inmemory_kv': inmemory_kv_cache_conn,
        'redis': redis_cache_conn,
        'mongo': mongo_cache_conn,
        'mixed_kv': mixed_cache_conn
    }

@pytest.fixture(scope='function')
def cachekv_conn(available_cachekv_connections, request):
    return available_cachekv_connections[request.param]
