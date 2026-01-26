from typing import Dict, List

import sys
sys.path.insert(0, "../")

from .RedisConnector import DEFAULT_REDISKV_CONFIG, RedisKVConnector
from .MongoConnector import DEFAULT_MONGOKV_CONFIG, MongoKVConnector
from ..utils import AbstractKVDatabaseConnection, KVDBConnectionConfig, KeyValueDBInstance

DEFAULT_MIXEDKV_CONFIG = KVDBConnectionConfig(params={'redis_config': DEFAULT_REDISKV_CONFIG, 'mongo_config': DEFAULT_MONGOKV_CONFIG})

class MixedKVConnector(AbstractKVDatabaseConnection):
    def __init__(self, config: KVDBConnectionConfig = DEFAULT_MIXEDKV_CONFIG):
        self.config = config

        self.config.params['mongo_config'].db_info['db'] = self.config.db_info['db']
        self.config.params['mongo_config'].db_info['table'] = self.config.db_info['table']
        self.config.params['mongo_config'].need_to_clear = False
        self.config.params['redis_config'].db_info['db'] = 0
        self.config.params['redis_config'].db_info['table'] = self.config.db_info['table']
        self.config.params['redis_config'].need_to_clear = False

        self.redis_conn = RedisKVConnector(self.config.params['redis_config'])
        self.mongo_conn = MongoKVConnector(self.config.params['mongo_config'])

    def open_connection(self):
        self.redis_conn.open_connection()
        self.mongo_conn.open_connection()

        if self.config.need_to_clear:
            self.clear()

    def is_open(self) -> bool:
        return self.redis_conn.is_open() and self.mongo_conn.is_open()

    def close_connection(self):
        self.redis_conn.close_connection()
        self.mongo_conn.close_connection()

    def create(self, items: List[KeyValueDBInstance]):
        self.mongo_conn.create(items)

    def read(self, ids: List[str]) -> List[KeyValueDBInstance]:
        # находим элементы, которых нет в оперативной памяти
        ram_items = self.redis_conn.read(ids)
        not_cached_item_ids = [ids[i] for i, item in enumerate(ram_items) if item is None]

        # получаем элементы из дискового хранилища
        persistent_items = self.mongo_conn.read(not_cached_item_ids)
        existing_p_items = [item for item in persistent_items if item is not None]

        # существующие элементы кешируем в оперативную память
        self.redis_conn.create(existing_p_items)

        # объединяем элементы из оперативного и жёсткого хранилищ
        union_items = []
        p_idx = 0
        for ram_idx in range(len(ram_items)):
            if ram_items[ram_idx] is None:
                union_items.append(persistent_items[p_idx])
                p_idx += 1
            else:
                union_items.append(ram_items[ram_idx])

        return union_items

    def update(self, items: List[KeyValueDBInstance]) -> None:
        self.redis_conn.update(items)
        self.mongo_conn.update(items)

    def delete(self, ids: List[str]) -> None:
        self.redis_conn.delete(ids)
        self.mongo_conn.delete(ids)

    def count_items(self, storage_type: int = 0) -> int:
        if storage_type == 0:
            return self.mongo_conn.count_items()
        elif storage_type == 1:
            return self.redis_conn.count_items()
        else:
            raise ValueError

    def item_exist(self, id: str, storage_type: int = 0) -> bool:
        if type(id) is not str:
            raise ValueError

        if storage_type == 0:
            return self.mongo_conn.item_exist(id)
        elif storage_type == 1:
            return self.redis_conn.item_exist(id)
        else:
            raise ValueError

    def clear(self) -> None:
        self.redis_conn.clear()
        self.mongo_conn.clear()

    def update_item_scores(self, mapping: Dict[str, int]) -> None:
        pass

    def delete_rare_items(self, num: int) -> None:
        pass

    def __del__(self):
        pass
