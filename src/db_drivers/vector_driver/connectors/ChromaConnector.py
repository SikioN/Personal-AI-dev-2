from typing import List, Tuple

# Try to use pysqlite3 if available (required for older ChromaDB versions)
# On modern systems, regular sqlite3 should work fine
try:
    __import__('pysqlite3')
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    # pysqlite3 not available, use system sqlite3
    pass

import chromadb
import logging
import gc
import torch
import numpy as np

from ....utils.errors import ReturnInfo
from ..utils import VectorDBConnectionConfig, AbstractVectorDatabaseConnection, VectorDBInstance
logging.getLogger("chromadb").setLevel(logging.CRITICAL)

DEFAULT_CHROMA_CONFIG = VectorDBConnectionConfig(
    params={"hnsw:space": "ip","hnsw:M": 4096},
    conn={'path':'../data/graph_structures/default_vectorstore'})

class ChromaConnection(AbstractVectorDatabaseConnection):

    def __init__(self, config: VectorDBConnectionConfig = DEFAULT_CHROMA_CONFIG) -> None:
        self.config = config
        self.collection = None
        self.client = None

    def open_connection(self) -> ReturnInfo:
        self.client = chromadb.PersistentClient(path=self.config.conn['path'])
        
        # In newer ChromaDB versions, metadata cannot be an empty dictionary
        if self.config.params:
            self.collection = self.client.get_or_create_collection(name=self.config.db_info['table'], metadata=self.config.params)
        else:
            self.collection = self.client.get_or_create_collection(name=self.config.db_info['table'])

        if self.config.need_to_clear:
            self.clear()

    def is_open(self) -> bool:
        # TODO
        pass

    def close_connection(self) -> ReturnInfo:
        self.collection = None
        self.client = None
        gc.collect()

    def create(self, items: List[VectorDBInstance]) -> ReturnInfo:
        # validating
        for item in items:
            if type(item.id) is not str:
                raise ValueError
            if type(item.embedding) in [torch.Tensor, np.ndarray]:
                raise ValueError
        unique_ids = set(map(lambda item: item.id, items))
        if len(items) != len(unique_ids):
            raise ValueError

        insts_idxs = list(range(len(items)))
        insts_with_md = list(filter(lambda i: len(items[i].metadata.keys()) > 0, insts_idxs))
        insts_wo_md = set(insts_idxs).difference(set(insts_with_md))

        if len(insts_with_md) > 0:
            self.collection.add(
                documents=list(map(lambda idx: items[idx].document, insts_with_md)),
                embeddings=list(map(lambda idx: items[idx].embedding, insts_with_md)),
                metadatas=list(map(lambda idx: items[idx].metadata, insts_with_md)),
                ids=list(map(lambda idx: items[idx].id, insts_with_md)))

        if len(insts_wo_md) > 0:
            self.collection.add(
                documents=list(map(lambda idx: items[idx].document, insts_wo_md)),
                embeddings=list(map(lambda idx: items[idx].embedding, insts_wo_md)),
                ids=list(map(lambda idx: items[idx].id, insts_wo_md)))

    def read(self, ids: List[str], includes: List[str] = ['embeddings', 'documents', 'metadatas']) -> List[VectorDBInstance]:
        formates_instances = []
        if len(ids):
            raw_instances = self.collection.get(
                include=includes,
                ids=ids)

            for i in range(len(raw_instances['ids'])):
                tmp_inst = {requested_field[:-1]: raw_instances[requested_field][i]
                            for requested_field in includes + ['ids']}
                formates_instances.append(VectorDBInstance(**tmp_inst))

        return formates_instances

    def update(self) -> ReturnInfo:
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

        for item in items:
            if self.item_exist(item.id):
                self.delete([item.id])
            self.create([item])

    def delete(self, ids: List[str]) -> None:
        # validation
        for id in ids:
            if type(id) is not str:
                raise ValueError

        if len(ids):
            self.collection.delete(ids=ids)

    def retrieve(
            self, query_instances: List[VectorDBInstance], n_results: int = 50, subset_ids=None,
            includes: List[str]  = ['embeddings', 'documents', 'metadatas']) -> List[List[Tuple[float, VectorDBInstance]]]:
        # validating
        if len(query_instances) < 1:
            return ValueError
        for inst in query_instances:
            if type(inst.embedding) in [torch.Tensor, np.ndarray]:
                raise ValueError

        collection_size = self.count_items()
        n_results = collection_size if collection_size < n_results else n_results
        if n_results < 1:
            return [[]*len(query_instances)]

        filtering_expr = dict()
        if subset_ids is not None:
            filtering_expr['ids'] = subset_ids

        # Attention: в случае использования ip-метрики будут получены значения расстояний [distances] между векторами,
        # а не значения их семантической блозости [similarity]
        raw_retrieved_instances = self.collection.query(
            query_embeddings=[inst.embedding for inst in query_instances],
            include=includes + ['distances'], n_results=n_results, **filtering_expr)

        #
        formated_instances = []
        for i in range(len(query_instances)):
            cur_formated_instances = []
            for j in range(len(raw_retrieved_instances['ids'][i])):
                tmp_inst = {requested_field[:-1]: raw_retrieved_instances[requested_field][i][j]
                        for requested_field in includes + ['ids']}
                cur_distance = raw_retrieved_instances['distances'][i][j]

                cur_formated_instances.append((cur_distance, VectorDBInstance(**tmp_inst)))

            cur_formated_instances = sorted(cur_formated_instances, key=lambda v: v[0], reverse=False)
            formated_instances.append(cur_formated_instances)

        return formated_instances

    def count_items(self) -> int:
        return self.collection.count()

    def item_exist(self, id: str) -> bool:
        output = self.collection.get(ids=[id])
        return len(output['ids']) > 0

    def clear(self) -> None:
        self.client.delete_collection(name=self.config.db_info['table'])
        if self.config.params:
            self.collection = self.client.create_collection(
                name=self.config.db_info['table'], metadata=self.config.params)
        else:
            self.collection = self.client.create_collection(
                name=self.config.db_info['table'])
