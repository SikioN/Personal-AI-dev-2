import redis
from typing import List, Dict
from collections import defaultdict
import numpy as np
import pickle

from src.db_drivers.kv_driver.utils import AbstractKVDatabaseConnection, KVDBConnectionConfig, KeyValueDBInstance

DEFAULT_REDISKV_CONFIG = KVDBConnectionConfig(host='localhost', port=6380, need_to_clear=False, db_info={'db': 0, 'table': 'test_collection'},
                                              params={'ss_name': 'sorted_node_pairs', 'hs_name': 'node_pairs', 'max_storage': 5e+8})

class RedisKVConnector(AbstractKVDatabaseConnection):
    def __init__(self, config: KVDBConnectionConfig = DEFAULT_REDISKV_CONFIG):
        self.config = config
        self.config.params['ss_name'] = f"{self.config.db_info['table']}_{self.config.params['ss_name']}"
        self.config.params['hs_name'] = f"{self.config.db_info['table']}_{self.config.params['hs_name']}"

    def open_connection(self):
        self.conn = redis.Redis(
            host=self.config.host, port=self.config.port,
            db=self.config.db_info['db'])

        if self.config.need_to_clear:
            self.clear()

    def is_open(self):
        try:
            self.conn.ping()
            return True
        except (redis.exceptions.ConnectionError, ConnectionRefusedError):
            return False

    def close_connection(self):
        self.conn.close()

    def create(self, items: List[KeyValueDBInstance]):
        for item in items:
            if item is None or item.id is None or item.value is None:
                raise ValueError

            if type(item.id) is not str:
                raise ValueError(f"id: t - {type(item.id)}; v - {item.id} value: t - {type(item.value)}; v - {item.value}")

        unique_ids = set(map(lambda item: item.id, items))
        if len(items) != len(unique_ids):
            raise ValueError

        filtered_items = []
        for item in items:
            item_exists = self.conn.hexists(self.config.params['hs_name'], item.id)
            if not item_exists:
                filtered_items.append(item)

        # находимся в фиксированном размере хранилища
        if self.config.params['max_storage'] > 0:
            n_items_to_delete = (self.count_items() + len(filtered_items)) - self.config.params['max_storage']
            if n_items_to_delete > 0:
                self.delete_rare_items(n_items_to_delete)

        if len(filtered_items) > 0:
            formated_items = []
            for item in filtered_items:
                if type(item.value) is bytes:
                    dumped_value = pickle.dumps((item.value, 'bytes'))
                else:
                    dumped_value = pickle.dumps((item.value, 'notbytes'))
                formated_items.append((item.id, dumped_value))

            self.conn.hset(self.config.params['hs_name'], mapping={item[0]: item[1] for item in formated_items})
            self.conn.zadd(self.config.params['ss_name'], {item[0]: 0 for item in formated_items})

    def read(self, ids: List[str]):
        for id in ids:
            if type(id) is not str:
                raise ValueError
        if len(ids) < 1:
            return []

        values = self.conn.hmget(self.config.params['hs_name'], ids)
        formated_items = []
        item_scores = defaultdict(lambda: 0)
        for i, val in enumerate(values):
            if val is None:
                formated_items.append(val)
            else:
                item_scores[ids[i]] += 1

                loaded_value = pickle.loads(val)[0]
                formated_items.append(
                    KeyValueDBInstance(id=ids[i], value=loaded_value))

        # Обновляем метрику использования элементов
        self.update_item_scores(item_scores)

        return formated_items

    def update(self, items: List[KeyValueDBInstance]):
        for item in items:
            if item is None or item.id is None or item.value is None:
                raise ValueError

            if type(item.id) is not str or type(item.value) not in [str, float, int]:
                raise ValueError

        filtered_items = [item for item in items if self.conn.hexists(self.config.params['hs_name'], item.id)]

        if len(filtered_items) > 0:
            formated_items = []
            for item in filtered_items:
                if type(item.value) is bytes:
                    dumped_value = pickle.dumps((item.value, 'bytes'))
                else:
                    dumped_value = pickle.dumps((item.value, 'notbytes'))
                formated_items.append((item.id, dumped_value))

            self.conn.hset(self.config.params['hs_name'], mapping={item[0]: item[1] for item in formated_items})
            self.conn.zadd(self.config.params['ss_name'], {item[0]: 0 for item in formated_items})

    def delete(self, ids: List[str]):
        for id in ids:
            if type(id) is not str:
                raise ValueError

        filtered_ids = [id for id in ids if self.conn.hexists(self.config.params['hs_name'], id)]

        if len(filtered_ids) > 0:
            self.conn.hdel(self.config.params['hs_name'], *filtered_ids)
            self.conn.zrem(self.config.params['ss_name'], *filtered_ids)

    def update_item_scores(self, mapping: Dict[str, int]) -> None:
        existed_keys = [id for id in list(mapping.keys()) if self.conn.hexists(self.config.params['hs_name'], id)]
        filtered_mapping = {k: mapping[k] for k in existed_keys}

        if len(existed_keys) > 0:
            for k,v in filtered_mapping.items():
                self.conn.zincrby(self.config.params['ss_name'], v, k)

    def delete_rare_items(self, num: int) -> None:
        rarest_values = self.conn.zrangebyscore(self.config.params['ss_name'], 0, "+inf", start=0, num=num)
        if len(rarest_values) > 0:
            self.conn.zrem(self.config.params['ss_name'], *rarest_values)
            self.conn.hdel(self.config.params['hs_name'], *rarest_values)

    def count_items(self):
        return self.conn.hlen(self.config.params['hs_name'])

    def item_exist(self, id: str):
        if type(id) is not str:
            raise ValueError
        return self.conn.hexists(self.config.params['hs_name'], id)

    def clear(self):
        self.conn.delete(self.config.params['hs_name'])
        self.conn.delete(self.config.params['ss_name'])
