from dataclasses import dataclass, field
from typing import List, Union, Dict
from copy import deepcopy

from .utils import AbstractQuadrupletsRetriever, BaseGraphSearchConfig
from .AStarQuadrupletsRetriever import AStarGraphSearchConfig, AStarTripletsRetriever
from .WaterCirclesQuadrupletsRetriever import WaterCirclesSearchConfig, WaterCirclesQuadrupletsRetriever
from .NaiveBFSQuadrupletsRetriever import NaiveBFSTripletsRetriever
from .BeamSearchQuadrupletsRetriever import BeamSearchTripletsRetriever
from ......utils.data_structs import QueryInfo, Quadruplet, create_id, NodeType, NODES_TYPES_MAP
from ......kg_model import KnowledgeGraphModel
from ......utils import Logger
from ......utils.cache_kv import CacheKV, CacheUtils
from ......db_drivers.kv_driver import KeyValueDriverConfig, KVDBConnectionConfig

@dataclass
class MixturedGraphSearchConfig(BaseGraphSearchConfig):
    retriever1_name: str = 'astar'
    retriever1_config: Union[BaseGraphSearchConfig, Dict] = field(default_factory=lambda: AStarGraphSearchConfig())
    retriever2_name: str = 'watercircles'
    retriever2_config: Union[BaseGraphSearchConfig, Dict] = field(default_factory=lambda: WaterCirclesSearchConfig())
    accepted_node_types: List[NodeType] = field(default_factory=lambda:[NodeType.object, NodeType.hyper, NodeType.episodic, NodeType.time])
    cache_table_name: str = 'qa_mixture_q_retriever_cache'

    def to_str(self):
        retriever1_pair = (self.retriever1_name, self.retriever1_config.to_str())
        retriever2_pair = (self.retriever2_name, self.retriever2_config.to_str())
        sorted_pretr = sorted([retriever1_pair, retriever2_pair], key=lambda p: p[0])

        str_accepted_nodes = ";".join(sorted(list(map(lambda v: v.value, self.accepted_node_types))))
        return f"{sorted_pretr[0][0]};{sorted_pretr[0][1]};{sorted_pretr[1][0]};{sorted_pretr[1][1]};{str_accepted_nodes}"

class MixturedTripletsRetriever(AbstractQuadrupletsRetriever): # Keeping class name for configs.py compatibility
    def __init__(self, kg_model: KnowledgeGraphModel, log: Logger, search_config: Union[MixturedGraphSearchConfig, Dict] = MixturedGraphSearchConfig(),
                 cache_kvdriver_config: KeyValueDriverConfig = None, verbose: bool = False) -> None:
        self.log = log
        self.verbose = verbose

        if type(search_config) is dict:
            if 'accepted_node_types' in search_config:
                search_config['accepted_node_types'] = list(map(lambda k: NODES_TYPES_MAP[k], search_config['accepted_node_types']))
            search_config = MixturedGraphSearchConfig(**search_config)
        self.config = search_config

        self.available_retrievers = {
            'astar': AStarTripletsRetriever,
            'watercircles': WaterCirclesQuadrupletsRetriever,
            'naive_bfs': NaiveBFSTripletsRetriever,
            'beamsearch': BeamSearchTripletsRetriever
        }

        self.retriever1 = self.available_retrievers[search_config.retriever1_name](
            kg_model, log, search_config.retriever1_config, cache_kvdriver_config, verbose)
        self.retriever2 = self.available_retrievers[search_config.retriever2_name](
            kg_model, log, search_config.retriever2_config, cache_kvdriver_config, verbose)

        # accepted nodes
        self.retriever1.config.accepted_node_types = search_config.accepted_node_types
        self.config.retriever1_config = self.retriever1.config
        self.retriever2.config.accepted_node_types = search_config.accepted_node_types
        self.config.retriever2_config = self.retriever2.config


        if cache_kvdriver_config is not None and self.config.cache_table_name is not None:
            cache_config = deepcopy(cache_kvdriver_config)
            cache_config.db_config.db_info['table'] = self.config.cache_table_name
            self.cachekv = CacheKV(cache_config)
        else:
            self.cachekv = None

    def get_relevant_quadruplets(self, query_info: QueryInfo) -> List[Quadruplet]:
        self.log("START KNOWLEDGE RETRIEVING ...", verbose=self.verbose)
        self.log(f"RETRIEVER: MixturedQuadrupletsRetriever ({self.config.retriever1_name} + {self.config.retriever2_name})", verbose=self.verbose)
        self.log(f"BASE_QUESTION ID: {create_id(query_info.query)}", verbose=self.verbose)
        self.log(f"BASE_QUESTION: {query_info.query}", verbose=self.verbose)

        quadruplets1 = self.retriever1.get_relevant_quadruplets(query_info)
        quadruplets2 = self.retriever2.get_relevant_quadruplets(query_info)

        self.log(f"Количество квадруплетов, извлечённых с помощью {self.config.retriever1_name}/{self.config.retriever2_name}: {len(quadruplets1)}/{len(quadruplets2)}",
                 verbose=self.verbose)

        # отбираем только уникальные квадруплеты (по их идентификаторам)
        unique_quadruplets = dict()
        for quadruplet in quadruplets1 + quadruplets2:
            unique_quadruplets[quadruplet.id] = deepcopy(quadruplet)

        return list(unique_quadruplets.values())
