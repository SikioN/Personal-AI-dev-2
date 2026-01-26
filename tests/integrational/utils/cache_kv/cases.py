import sys
import copy
import pickle
import hashlib
# TO CHANGE
PROJECT_BASE_DIR = '../'
TEST_VOLUME_DIR = './volumes'
sys.path.insert(0, PROJECT_BASE_DIR)

from src.agents.connectors.OLlamaConnector import DEFAULT_OLLAMA_CONFIG
from src.db_drivers.kv_driver.utils import KeyValueDBInstance

AVAILABLE_KV_DBS = ['inmemory_kv', 'redis', 'mongo', 'mixed_kv']

KEY_EMPTY = list()

KEY1 = [DEFAULT_OLLAMA_CONFIG.to_str(), "123","asd", "asd"]
KEY_HASH1 = hashlib.sha1(''.join(list(map(lambda k: hashlib.sha1(k.encode()).hexdigest(), KEY1))).encode()).hexdigest()

KEY1_ORDER_MODIF = ["123", DEFAULT_OLLAMA_CONFIG.to_str(), "asd", "asd"]
KEY_HASH1_ORDER_MODIF = hashlib.sha1(''.join(list(map(lambda k: hashlib.sha1(k.encode()).hexdigest(), KEY1_ORDER_MODIF))).encode()).hexdigest()

MODIF_OBJECT1 = copy.deepcopy(DEFAULT_OLLAMA_CONFIG)
MODIF_OBJECT1.credentials['host'] = 'http://localhost:11222'
KEY1_OBJECT_MODIF1 = [MODIF_OBJECT1.to_str(), "123","asd", "asd"]
KEY_HASH1_OBJECT_MODIF1 = hashlib.sha1(''.join(list(map(lambda k: hashlib.sha1(k.encode()).hexdigest(), KEY1_OBJECT_MODIF1))).encode()).hexdigest()

MODIF_OBJECT2 = copy.deepcopy(DEFAULT_OLLAMA_CONFIG)
MODIF_OBJECT2.credentials['model'] = 'qwen2.5'
KEY1_OBJECT_MODIF2 = [MODIF_OBJECT2.to_str(), "123","asd", "asd"]
KEY_HASH1_OBJECT_MODIF2 = hashlib.sha1(''.join(list(map(lambda k: hashlib.sha1(k.encode()).hexdigest(), KEY1_OBJECT_MODIF2))).encode()).hexdigest()

VALUE1 = "Hello World!"
VALUE1_DUMPED = pickle.dumps(VALUE1)

VALUE2 = "Goodbye World!"
VALUE2_DUMPED = pickle.dumps(VALUE2)

VALUE3 = "New cached value"

CACHED_INSTANCES = [
    KeyValueDBInstance(id=KEY_HASH1, value=VALUE1_DUMPED),
    KeyValueDBInstance(id=KEY_HASH1_OBJECT_MODIF1, value=VALUE2_DUMPED)]

# key, expected, exception, key2, expected2
CACHEKV_GETHASH_TEST_CASES = [
 # 1. в key-значении нулевое количество объектов (невалидный key)
 (KEY_EMPTY, None, True, None, None),
 # 2. позитивный тест
 (KEY1, KEY_HASH1, False, None, None),
 # 3. изменённый порядок объектов в key-значении
 (KEY1, KEY_HASH1, False, KEY1_ORDER_MODIF, KEY_HASH1_ORDER_MODIF),
 # 4. изменённые объекты в key-значении
 # 4.1 пример №1
 (KEY1, KEY_HASH1, False, KEY1_OBJECT_MODIF1, KEY_HASH1_OBJECT_MODIF1),
 # 4.2 пример №2
 (KEY1, KEY_HASH1, False, KEY1_OBJECT_MODIF2, KEY_HASH1_OBJECT_MODIF2)
]

# cache_instances, value, key, key_hash, expected, exception
CACHEKV_SAVE_TEST_CASES = [
    # 1. в key-значении нулевое количество объектов (невалидный key)
    (CACHED_INSTANCES, VALUE3, KEY_EMPTY, None, None, True),
    # 2. key- и key_hash-значения пустые
    (CACHED_INSTANCES, VALUE3, None, None, None, True),
    # 3. непустое key-значение (value-отсутствует)
    (CACHED_INSTANCES, VALUE3, KEY1_OBJECT_MODIF2, None, KEY_HASH1_OBJECT_MODIF2, False),
    # 4. непустое key_hash-значение (values-отсутствует)
    (CACHED_INSTANCES, VALUE3, None, KEY_HASH1_OBJECT_MODIF2, KEY_HASH1_OBJECT_MODIF2, False),
    # 5. key-значение уже содержится в кеше
    (CACHED_INSTANCES, VALUE3, KEY1, None, None, True)
]

CACHEKV_POPULATED_SAVE_TEST_CASES = []
for db_vendor in AVAILABLE_KV_DBS:
    for i in range(len(CACHEKV_SAVE_TEST_CASES)):
        CACHEKV_POPULATED_SAVE_TEST_CASES.append(CACHEKV_SAVE_TEST_CASES[i] + (db_vendor,))

# cache_instances, key, key_hash, expected_status, expected_value, exception
CACHEKV_LOAD_TEST_CASES = [
    # 1. в key-значении нулевое количество объектов (невалидный key)
    (CACHED_INSTANCES, KEY_EMPTY, None, None, None, True),
    # 2. key- и key_hash-значения пустые
    (CACHED_INSTANCES, None, None, None, None, True),
    # 3. непустое key-значение (value-присутствует)
    (CACHED_INSTANCES, KEY1, None, 0, VALUE1, False),
    # 4. непустое key_hash-значение (value-присутствует)
    (CACHED_INSTANCES, None, KEY_HASH1_OBJECT_MODIF1, 0, VALUE2, False),
    # 5. непустое key-значение (value-отсутствует)
    (CACHED_INSTANCES, KEY1_OBJECT_MODIF2, None, -1, KEY_HASH1_OBJECT_MODIF2, False),
    # 6. непустое key_hash-значение (value-отсутвтует)
    (CACHED_INSTANCES, None, KEY_HASH1_OBJECT_MODIF2, -1, KEY_HASH1_OBJECT_MODIF2, False)
]

CACHEKV_POPULATED_LOAD_TEST_CASES = []
for db_vendor in AVAILABLE_KV_DBS:
    for i in range(len(CACHEKV_LOAD_TEST_CASES)):
        CACHEKV_POPULATED_LOAD_TEST_CASES.append(CACHEKV_LOAD_TEST_CASES[i] + (db_vendor,))
