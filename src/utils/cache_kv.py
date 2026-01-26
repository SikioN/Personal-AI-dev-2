from ..db_drivers.kv_driver.KeyValueDriver import KeyValueDriver, KeyValueDriverConfig
from ..db_drivers.kv_driver.utils import KeyValueDBInstance, KVDBConnectionConfig

from typing import List, Union, Tuple
import pickle
import hashlib

DEFAULT_CACHEKV_CONFIG = KeyValueDriverConfig(
    db_vendor='mongo',
    db_config=KVDBConnectionConfig(
        db_info={'db': 'personalaidb_results_cache', 'table': 'personalaitable_results_cache'},
        host='localhost', port=27018, params={'username': 'user', 'password': 'pass', 'max_storage': -1},
        need_to_clear=False))

from abc import ABC, abstractmethod
from typing import Tuple


class AbstractCacheUtils(ABC):
    @abstractmethod
    def get_cache_key(self, *args, **kwargs):
        pass

class CacheUtils(AbstractCacheUtils):

    def cache_method_output(function):
        def wrapper(self, *args, **kwargs):
            cached_flag = False
            cache_key = self.get_cache_key(*args, **kwargs)
            key_hash = None

            if self.cachekv is not None:
                self.log("Поиск результата в кеше...", verbose=self.verbose)
                cstatus, key_hash, cached_result = self.cachekv.load_value(key=cache_key)
                if cstatus == 0:
                    self.log("Результат по заданной конфигурации гиперпараметров уже был получен.", verbose=self.verbose)
                    self.log(f"* CACHE_TABLE_NAME {self.cachekv.kv_conn.config.db_info['table']}", verbose=self.verbose)
                    self.log(f"* CACHE_HASH_KEY: {key_hash}.", verbose=self.verbose)
                    self.log(f"* HASH_SEEDS: {cache_key}.", verbose=self.verbose)
                    self.log(f"* CACHED_VALUE: {cached_result}.", verbose=self.verbose)


                    cached_flag = True
                    output = cached_result
                else:
                    self.log("Результата по заданной конфигурации гиперпараметров в кеше нет.", verbose=self.verbose)
                    self.log(f"* CACHE_TABLE_NAME {self.cachekv.kv_conn.config.db_info['table']}", verbose=self.verbose)
                    self.log(f"* CACHE_HASH_KEY: {key_hash}.", verbose=self.verbose)
                    self.log(f"* HASH_SEEDS: {cache_key}.", verbose=self.verbose)

            if not cached_flag:
                self.log("Получем результат с нуля...", verbose=self.verbose)
                output = function(self, *args, **kwargs)

                if self.cachekv is not None:
                    self.log("Кешируем полученный результат.", verbose=self.verbose)
                    self.log(f"* CACHE_TABLE_NAME {self.cachekv.kv_conn.config.db_info['table']}", verbose=self.verbose)
                    self.log(f"* CACHE_HASH_KEY: {key_hash}.", verbose=self.verbose)
                    self.cachekv.save_value(value=output, key_hash=key_hash)

            return output
        return wrapper

class CacheKV:
    def __init__(self, kvdriver_config: KeyValueDriverConfig = DEFAULT_CACHEKV_CONFIG):
        self.kv_conn = KeyValueDriver.connect(kvdriver_config)

    @staticmethod
    def prepare_key(key: List[object] = None, key_hash: str = None) -> str:
        # либо key- либо key_hash-значение должно быть указано,
        # инчае ошибка.
        if key is not None:
            if not CacheKV.is_key_valid(key):
                raise ValueError

            key_hash = CacheKV.get_hash(key)
        elif key_hash is not None:
            pass
        else:
            raise ValueError

        return key_hash

    @staticmethod
    def get_hash(key: List[str]) -> str:
        if not CacheKV.is_key_valid(key):
            raise ValueError

        hashes = list(map(lambda k: hashlib.sha1(k.encode()).hexdigest(), key))
        concated_hashes = ''.join(hashes)
        key_hash = hashlib.sha1(concated_hashes.encode()).hexdigest()
        return key_hash

    @staticmethod
    def is_key_valid(key: List[str]) -> bool:
        return len(key) > 0

    def load_value(self, key: List[str] = None, key_hash: str = None) -> Tuple[int, str, Union[str, object]]:
        key_hash = CacheKV.prepare_key(key, key_hash)

        output = self.kv_conn.read([key_hash])
        filtered_output = list(filter(lambda item: item is not None, output))

        if len(filtered_output) < 1:
            return (-1, key_hash, None)

        raw_value = filtered_output[0].value
        formated_value = pickle.loads(raw_value)
        return (0, key_hash, formated_value)

    def save_value(self, value: object, key: List[str] = None, key_hash: str = None) -> str:
        key_hash = CacheKV.prepare_key(key, key_hash)
        if self.kv_conn.item_exist(key_hash):
            raise ValueError

        new_item = KeyValueDBInstance(id=key_hash, value=pickle.dumps(value))
        self.kv_conn.create([new_item])
        return key_hash

    def check_key_exist(self, key: List[object] = None, key_hash: str = None) -> bool:
        key_hash = CacheKV.prepare_key(key, key_hash)
        return self.kv_conn.item_exist(key_hash)
