import pymongo
from typing import List, Dict
from collections import defaultdict
import numpy as np
import pickle

from src.db_drivers.kv_driver.utils import AbstractKVDatabaseConnection, KVDBConnectionConfig, KeyValueDBInstance

DEFAULT_MONGOKV_CONFIG = KVDBConnectionConfig(host='localhost', port=27017,
                                              db_info={'db': 'test_db', 'table': 'test_collection'},
                                              params={'username': 'user', 'password': 'pass', 'max_storage': -1})

class MongoKVConnector(AbstractKVDatabaseConnection):

    def __init__(self, config: KVDBConnectionConfig = DEFAULT_MONGOKV_CONFIG) -> None:
        self.config = config

    def is_open(self) -> bool:
        try:
            self._client.server_info()
            return True
        except pymongo.errors.ServerSelectionTimeoutError as err:
            print(str(err))
            return False

    def open_connection(self) -> None:
        self._client = pymongo.MongoClient(f'mongodb://{self.config.host}:{self.config.port}',
                                           username=self.config.params['username'], password=self.config.params['password'])
        self._collection = self._client[self.config.db_info['db']][self.config.db_info['table']]

        if self.config.need_to_clear:
            self.clear()

    def close_connection(self) -> None:
        self._client.close()

    def create(self, items: List[KeyValueDBInstance]) -> None:
        for item in items:
            if item is None or item.id is None or item.value is None:
                raise ValueError

            if type(item.id) is not str:
                raise ValueError(f"{item} {type(item.id)} {type(item.value)}")

        unique_ids = set(map(lambda item: item.id, items))
        if len(items) != len(unique_ids):
            raise ValueError

        filtered_items = []
        for item in items:
            if self._collection.find_one({'_id': item.id}) is None:
                if type(item.value) is bytes:
                    dumped_value = pickle.dumps((item.value, 'bytes'))
                else:
                    dumped_value = pickle.dumps((item.value, 'notbytes'))
                filtered_items.append({'_id': item.id, 'value': dumped_value, 'score': 0})

        # находимся в фиксированном размере хранилища
        if self.config.params['max_storage'] > 0:
            n_items_to_delete = (self.count_items() + len(filtered_items)) - self.config.params['max_storage']
            if n_items_to_delete > 0:
                self.delete_rare_items(n_items_to_delete)

        if len(filtered_items) > 0:
            self._collection.insert_many(filtered_items)

    def delete_rare_items(self, num: int) -> None:
        # TODO
        pass

    def read(self, ids: List[str]) -> List[KeyValueDBInstance]:
        for id in ids:
            if (id is None) or (type(id) is not str):
                raise ValueError

        if len(ids) < 1:
            return []

        items = self._collection.find({"_id": {"$in": ids}})
        items_dict = {item['_id']: item for item in items}

        sorted_items = []
        item_scores = defaultdict(lambda: 0)
        for id in ids:
            item = items_dict.get(id, None)
            if item is not None:
                loaded_value = pickle.loads(item['value'])[0]
                item = KeyValueDBInstance(id=item['_id'], value=loaded_value)
                item_scores[item.id] += 1

            sorted_items.append(item)

        # Обновляем метрику использования элементов
        self.update_item_scores(item_scores)

        return sorted_items

    def update_item_scores(self, mapping: Dict[str, int]) -> None:
        # TODO
        pass

    def update(self, items: List[KeyValueDBInstance]) -> None:
        for item in items:
            if item is None or item.id is None or item.value is None:
                raise ValueError

            if type(item.id) is not str or type(item.value) not in [str, float, int]:
                raise ValueError

        if len(items) < 1:
            return

        existig_items = self._collection.find({"_id": {"$in": [item.id for item in items]}})
        items_dict = {item.id: item for item in items}

        for exist_item in existig_items:
            if items_dict[exist_item['_id']] is not None:
                cur_item = items_dict[exist_item['_id']]

                if type(item.value) is bytes:
                    dumped_value = pickle.dumps((cur_item.value, 'bytes'))
                else:
                    dumped_value = pickle.dumps((cur_item.value, 'notbytes'))

                self._collection.update_one({'_id': cur_item.id}, {"$set": { "value": dumped_value}})


    def delete(self, ids: List[str]) -> None:
        for id in ids:
            if type(id) is not str:
                raise ValueError

        if len(ids) > 0:
            self._collection.delete_many({'_id': {"$in": ids}})

    def count_items(self) -> int:
        return self._collection.count_documents({})

    def item_exist(self, id: str) -> bool:
        if type(id) is not str:
            raise ValueError

        item = self._collection.find_one({'_id': id})
        return item is not None

    def clear(self) -> None:
        self._collection.drop()
