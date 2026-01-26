from typing import List, Dict, Union
from dataclasses import dataclass
from collections import Counter
from copy import deepcopy

from .utils import AbstractTripletsRetriever, BaseGraphSearchConfig
from ......db_drivers.vector_driver import VectorDBInstance
from ......kg_model import KnowledgeGraphModel
from ......utils import Logger
from ......utils.data_structs import QueryInfo, Triplet, create_id, NODES_TYPES_MAP
from ......utils.cache_kv import CacheKV, CacheUtils
from ......db_drivers.kv_driver import KeyValueDriverConfig, KVDBConnectionConfig

@dataclass
class NaiveGraphSearchConfig(BaseGraphSearchConfig):
    max_k: int = 50
    cache_table_name: str = 'qa_naive_t_retriever_cache'

    def to_str(self):
        return f"{self.max_k}"

class NaiveTripletsRetriever(AbstractTripletsRetriever, CacheUtils):

    def __init__(self, kg_model: KnowledgeGraphModel, log: Logger, search_config: Union[NaiveGraphSearchConfig,Dict] = NaiveGraphSearchConfig(),
                 cache_kvdriver_config: KeyValueDriverConfig = None, verbose: bool = False) -> None:
        self.log = log
        self.verbose = verbose
        self.kg_model = kg_model

        if type(search_config) is dict:
            search_config = NaiveGraphSearchConfig(**search_config)
        self.config = search_config

        if cache_kvdriver_config is not None and self.config.cache_table_name is not None:
            cache_config = deepcopy(cache_kvdriver_config)
            cache_config.db_config.db_info['table'] = self.config.cache_table_name
            self.cachekv = CacheKV(cache_config)
        else:
            self.cachekv = None

    def get_cache_key(self, query_info: QueryInfo) -> List[object]:
        return [self.config.to_str(), query_info.to_str()]

    @CacheUtils.cache_method_output
    def get_relevant_triplets(self, query_info: QueryInfo) -> List[Triplet]:
        self.log("START KNOWLEDGE RETRIEVING ...", verbose=self.verbose)
        self.log("RETRIEVER: NaiveTripletsRetriever", verbose=self.verbose)
        self.log(f"BASE_QUESTION ID: {create_id(query_info.query)}", verbose=self.verbose)
        self.log(f"BASE_QUESTION: {query_info.query}", verbose=self.verbose)

        query_embd = self.kg_model.embeddings_struct.embedder.encode_queries([query_info.query])[0]
        query_instance = VectorDBInstance(embedding=query_embd)

        raw_relevant_triplets = self.kg_model.embeddings_struct.vectordbs['triplets'].retrieve(
                [query_instance], self.config.max_k, includes=['metadatas'])[0]

        triplet_ids = list(map(lambda item: item[1].metadata['t_id'], raw_relevant_triplets))
        self.log(f"Количество извлечённых объектов из векторной бд (triplets): {len(triplet_ids)}", verbose=self.verbose)

        triplets = self.kg_model.graph_struct.db_conn.read(triplet_ids)
        self.log(f"Количество полученных трипелтов из графовой бд: {len(triplets)}", verbose=self.verbose)
        self.log(f"Распределение типов связей в наборе извлечённых триплетов: {Counter([triplet.relation.type for triplet in triplets])}", verbose=self.verbose)

        return triplets
