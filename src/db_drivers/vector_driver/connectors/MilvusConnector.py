from typing import List, Dict, Tuple, Union
from pymilvus.orm.connections import ConnectionNotExistException
from pymilvus import MilvusClient, DataType
from time import sleep
import numpy as np
import torch
import ast

from ..utils import AbstractVectorDatabaseConnection, VectorDBInstance, VectorDBConnectionConfig


DEFAULT_MILVUS_CONFIG = VectorDBConnectionConfig(
    conn={'host': 'localhost', 'port': 19530, 'user': 'root', 'pass': 'Milvus'},
    db_info={'db': 'test_db', 'table': 'test_collection'},
    params={'id_length': 32, 'vector_dim': 1024, 'document_max_length': 51200, 'load': True,
            'flush': True, 'create_sleep': 1, 'search_metric': 'IP'})

class MilvusConnector(AbstractVectorDatabaseConnection):
    def __init__(self, config: VectorDBConnectionConfig):
        self.config = config
        self.client = None

    def prepare_structure(self) -> None:
        # создать бд
        existing_dbs = self.client.list_databases()
        if self.config.db_info['db'] not in existing_dbs:
            self.client.create_database(db_name=self.config.db_info['db'])
        self.client.using_database(db_name=self.config.db_info['db'])

        # cоздать коллекцию
        existing_collections = self.client.list_collections()
        if self.config.db_info['table'] not in existing_collections:
            self.create_collection()

    def create_collection(self) -> None:
        schema = MilvusClient.create_schema(auto_id=False)
        schema.add_field(field_name="id", datatype=DataType.VARCHAR, max_length=self.config.params['id_length'], is_primary=True)
        schema.add_field(field_name="embedding", datatype=DataType.FLOAT_VECTOR, dim=self.config.params['vector_dim'])
        schema.add_field(field_name="document", datatype=DataType.VARCHAR, max_length=self.config.params['document_max_length'])
        schema.add_field(field_name="metadata", datatype=DataType.JSON)

        self.client.create_collection(
            collection_name=self.config.db_info['table'],
            schema=schema, consistency_level="Strong")

    def create_index(self):
        cur_indexes = self.client.list_indexes(collection_name=self.config.db_info['table'])
        index_params = self.client.prepare_index_params()
        if "id_index" not in cur_indexes:
            # создать индекс
            index_params.add_index(field_name="id", index_name="id_index")
        if "embedding_index" not in cur_indexes:
            index_params.add_index(
                field_name="embedding", index_type="IVF_FLAT",
                index_name="embedding_index", metric_type=self.config.params['search_metric'])
        if len(cur_indexes) != 2:
            self.client.create_index(
                collection_name=self.config.db_info['table'],
                index_params=index_params)

    def open_connection(self) -> None:
        uri = f"http://{self.config.conn['host']}:{self.config.conn['port']}"
        auth = f"{self.config.conn['user']}:{self.config.conn['pass']}"
        self.client = MilvusClient(uri=uri,token=auth)

        self.prepare_structure()

        if self.config.need_to_clear:
            self.clear()

        self.create_index()

        load_state = self.client.get_load_state(self.config.db_info['table'])['state'].value
        if self.config.params['load'] and load_state != 3:
            self.client.load_collection(
                collection_name=self.config.db_info['table'],
                skip_load_dynamic_field=True)

    def close_connection(self) -> None:
        load_state = self.client.get_load_state(self.config.db_info['table'])['state'].value
        if load_state != 3:
            self.client.release_collection(
                collection_name=self.config.db_info['table'])
        self.client.close()

    def is_open(self) -> bool:
        if self.client is None:
            return False

        try:
            self.client.list_collections()
            return True
        except ConnectionNotExistException as e:
            return False

    def create(self, items: List[VectorDBInstance]) -> None:
        # validation
        for item in items:
            if type(item.id) is not str:
                raise ValueError
            if type(item.embedding) in [torch.Tensor, np.ndarray]:
                raise ValueError
        unique_ids = set(map(lambda item: item.id, items))
        if len(items) != len(unique_ids):
            raise ValueError

        filtered_items = []
        for item in items:
            item_exists = self.item_exist(item.id)
            if not item_exists:
                filtered_items.append(item)

        formated_data = list(map(lambda item: item.dict(), filtered_items))

        out = self.client.insert(
            collection_name=self.config.db_info['table'],
            data=formated_data)

        # костыль
        if self.config.params['flush']:
            self.client.flush(collection_name=self.config.db_info['table'])
        else:
            sleep(self.config.params['create_sleep'])

    def read(self, ids: List[str], includes=["embeddings", "documents", "metadatas"]) -> List[VectorDBInstance]:
        # validation
        for id in ids:
            if (id is None) or (type(id) is not str):
                raise ValueError
        if len(ids) < 1:
            return []

        # костыль
        f_includes = list(map(lambda f_name: f_name[:-1],includes))

        raw_output = self.client.get(
            collection_name=self.config.db_info['table'],
            ids=ids,output_fields=f_includes)

        formated_output = list(map(lambda raw_item: VectorDBInstance(**raw_item), raw_output))

        return formated_output

    def update(self, items: List[VectorDBInstance]) -> None:
        # TODO
        pass

    def upsert(self, items: List[VectorDBInstance]) -> None:
        # validation
        for item in items:
            if type(item.id) is not str:
                raise ValueError
        unique_ids = set(map(lambda item: item.id, items))
        if len(items) != len(unique_ids):
            raise ValueError

        formated_data = list(map(lambda item: item.dict(), items))
        self.client.upsert(collection_name=self.config.db_info['table'], data=formated_data)

        # костыль
        if self.config.params['flush']:
            self.client.flush(collection_name=self.config.db_info['table'])
        else:
            sleep(self.config.params['create_sleep'])

    def delete(self, ids: List[str]) -> None:
        # validation
        for id in ids:
            if type(id) is not str:
                raise ValueError

        if len(ids):
            filtered_ids = [id for id in ids if self.item_exist(id)]
            if len(filtered_ids):
                self.client.delete(collection_name=self.config.db_info['table'], ids=filtered_ids)

                # костыль
                if self.config.params['flush']:
                    self.client.flush(collection_name=self.config.db_info['table'])
                else:
                    sleep(self.config.params['create_sleep'])

    def retrieve(
            self, query_instances: List[VectorDBInstance], n_results: int = 50, subset_ids: Union[None, List[str]]= None,
            includes: List[str]  = ['embeddings', 'documents', 'metadatas']) -> List[List[Tuple[float, VectorDBInstance]]]:
        if len(query_instances) < 1:
            return ValueError
        for inst in query_instances:
            if type(inst.embedding) in [torch.Tensor, np.ndarray]:
                raise ValueError

        if n_results < 1:
            return [[]*len(query_instances)]

        # костыль
        f_includes = list(map(lambda f_name: f_name[:-1],includes))

        filtering_expr = {'search_params': {"metric_type": self.config.params['search_metric']}}
        if subset_ids is not None:
            filtering_expr['search_params']["hints"] = "iterative_filter"
            filtering_expr['filter']=f'id in {subset_ids}'

        #
        raw_output = self.client.search(
            collection_name=self.config.db_info['table'],
            data=[inst.embedding for inst in query_instances],
            limit=n_results, output_fields=f_includes, **filtering_expr)

        formated_output = []
        for q_output in raw_output:
            # CARE: работает только для COSINE и IP - метрик
            # костыль: полученные значения семантической близости векторов [similarity] приводим к шкале расстояний [distances]
            f_items = list(map(lambda r_item: (1 - r_item['distance'], VectorDBInstance(id=r_item['id'], **r_item['entity'])), q_output))
            f_items = sorted(f_items, key=lambda v: v[0], reverse=False)
            formated_output.append(f_items)

        return formated_output

    def count_items(self) -> int:
        raw_output = self.client.query(self.config.db_info['table'], filter='', output_fields=['count(*)'])
        return raw_output[0]['count(*)']

    def item_exist(self, id: str) -> bool:
        # validation
        if type(id) is not str:
            raise ValueError

        #
        res = self.client.get(
            collection_name=self.config.db_info['table'],
            ids=[id],output_fields=[])

        return bool(len(res))

    def clear(self) -> None:
        load_state = self.client.get_load_state(self.config.db_info['table'])['state'].value
        if load_state != 3:
            self.client.release_collection(collection_name=self.config.db_info['table'])

        self.client.drop_collection(collection_name=self.config.db_info['table'])
        self.prepare_structure()
        self.create_index()

        if self.config.params['load']:
            self.client.load_collection(
                collection_name=self.config.db_info['table'],
                skip_load_dynamic_field=True)
