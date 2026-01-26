import sys
import pickle
# TO CHANGE
PROJECT_BASE_DIR = '../'
sys.path.insert(0, PROJECT_BASE_DIR)

from src.db_drivers.kv_driver.utils import AbstractKVDatabaseConnection, KeyValueDBInstance
from src.utils.cache_kv import CacheKV
import pytest
from typing import List

from cases import CACHEKV_GETHASH_TEST_CASES, CACHEKV_POPULATED_LOAD_TEST_CASES,\
    CACHEKV_POPULATED_SAVE_TEST_CASES

@pytest.mark.parametrize("key, expected, exception, key2, expected2", CACHEKV_GETHASH_TEST_CASES)
def test_gethash(key: List[object], expected: str, exception: bool, key2: List[object], expected2: str):
    try:
        real = CacheKV.get_hash(key)
    except ValueError as e:
        assert exception
    else:
        assert not exception
        assert real == expected

    if (key2 is not None) and (expected2 is not None):
        real2 = CacheKV.get_hash(key2)
        assert real2 == expected2
        assert real != real2

@pytest.mark.parametrize("cache_instances, key, key_hash, expected_status, expected_value, exception, cachekv_conn", CACHEKV_POPULATED_LOAD_TEST_CASES, indirect=['cachekv_conn'])
def test_load_value(cache_instances: List[KeyValueDBInstance], key: List[object], key_hash: str,
                    expected_status: bool, expected_value: object, exception: bool, cachekv_conn: CacheKV):
    cachekv_conn.kv_conn.clear()
    cachekv_conn.kv_conn.create(cache_instances)

    try:
        real_status, real_hash_key, real_value = cachekv_conn.load_value(key, key_hash)
        if real_status != 0:
            real_value = real_hash_key
    except ValueError as e:
        assert exception
    else:
        assert not exception
        assert real_status == expected_status
        assert real_value == expected_value

@pytest.mark.parametrize("cache_instances, value, key, key_hash, expected, exception, cachekv_conn", CACHEKV_POPULATED_SAVE_TEST_CASES, indirect=['cachekv_conn'])
def test_save_value(cache_instances: List[KeyValueDBInstance], value: object, key: List[object], key_hash: str,
                    expected: str, exception: bool, cachekv_conn: CacheKV):
    cachekv_conn.kv_conn.clear()
    cachekv_conn.kv_conn.create(cache_instances)

    try:
        real_key_hash = cachekv_conn.save_value(value, key=key, key_hash=key_hash)
    except ValueError as e:
        assert exception
    else:
        assert not exception
        assert real_key_hash == expected

        assert cachekv_conn.kv_conn.item_exist(real_key_hash)
        real_value = pickle.loads(cachekv_conn.kv_conn.read([real_key_hash])[0].value)
        assert real_value == value
