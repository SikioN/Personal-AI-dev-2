from typing import List, Dict
import gc
import joblib
import pickle
import os
import time
import hashlib
import numpy as np
from collections import defaultdict

from ..utils import KVDBConnectionConfig, AbstractKVDatabaseConnection, KeyValueDBInstance

DEFAULT_INMEMORYKV_CONFIG = KVDBConnectionConfig(
    host='localhost',
    params={
        'kvstore_dump_name': 'inmemory_store',
        'load_from_disk': False, 'load_dump_dir': '.',
        'save_on_disk': True, 'save_dump_dir': '.',
        'max_storage': 5e+8
    })

class InMemoryKVConnector(AbstractKVDatabaseConnection):

    def __init__(self, config: KVDBConnectionConfig = DEFAULT_INMEMORYKV_CONFIG) -> None:
        self.config = config

    def open_connection(self) -> None:
        if self.config.params['load_from_disk']:
            load_path = f"{self.config.params['load_dump_dir']}/{self.config.params['kvstore_dump_name']}.dump"
            if os.path.exists(load_path):
                self.kv_store = joblib.load(load_path)
            else:
                print(f"warning: kvstore-dump '{load_path}' doesnt exists. creating empty kv-store")
                self.kv_store = dict()
        else:
            self.kv_store = dict()

        if self.config.need_to_clear:
            self.clear()

    def is_open(self) -> bool:
        return hasattr(self, 'kv_store')

    def close_connection(self) -> None:
        if self.config.params['save_on_disk']:
            save_path = f"{self.config.params['save_dump_dir']}/{self.config.params['kvstore_dump_name']}"
            if os.path.exists(save_path):
                print("warning: file on that path is already exists")
                postfix = hashlib.md5(str(time.time()).encode()).hexdigest()
                save_path += postfix
            save_path += '.dump'

            joblib.dump(self.kv_store, save_path)
        del self.kv_store
        gc.collect()

    def create(self, items: List[KeyValueDBInstance]) -> None:
        for item in items:
            if item is None or item.id is None or item.value is None:
                raise ValueError

            if type(item.id) is not str:
                raise ValueError(f"id: t - {type(item.id)}; v - {item.id} value: t - {type(item.value)}; v - {item.value}")

        unique_ids = set(map(lambda item: item.id, items))
        if len(items) != len(unique_ids):
            raise ValueError

        filtered_items = [item for item in items if not self.item_exist(item.id)]

        # находимся в фиксированном размере хранилища
        if self.config.params['max_storage'] > 0:
            n_items_to_delete = (self.count_items() + len(filtered_items)) - self.config.params['max_storage']
            if n_items_to_delete > 0:
                self.delete_rare_items(n_items_to_delete)

        for item in filtered_items:
            if type(item.value) is bytes:
                dumped_value = pickle.dumps((item.value, 'bytes'))
            else:
                dumped_value = pickle.dumps((item.value, 'notbytes'))

            self.kv_store[item.id] = dumped_value

    def delete_rare_items(self, num: int) -> None:
        # TODO
        pass

    def read(self, ids: List[str]) -> List[KeyValueDBInstance]:
        for id in ids:
            if (id is None) or (type(id) is not str):
                raise ValueError

        items = []
        item_scores = defaultdict(lambda: 0)
        for id in ids:
            item = None
            if self.item_exist(id):
                loaded_value = pickle.loads(self.kv_store[id])[0]
                item = KeyValueDBInstance(id=id, value=loaded_value)
                item_scores[id] += 1
            items.append(item)

        # Обновляем метрику использования элементов
        self.update_item_scores(item_scores)

        return items

    def update_item_scores(self, mapping: Dict[str, int]) -> None:
        # TODO
        pass

    def update(self, items: List[KeyValueDBInstance]) -> None:
        # TODO
        pass

    def delete(self, ids: List[str]):
        for id in ids:
            if type(id) is not str:
                raise ValueError

        for id in ids:
            if self.item_exist(id):
                del self.kv_store[id]

    def clear(self):
        del self.kv_store
        gc.collect()
        self.kv_store = dict()

    def count_items(self) -> int:
        return len(self.kv_store)

    def item_exist(self, id: str):
        if type(id) is not str:
            raise ValueError
        return id in self.kv_store
