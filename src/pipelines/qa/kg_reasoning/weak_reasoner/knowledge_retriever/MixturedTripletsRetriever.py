from dataclasses import dataclass, field
from typing import List, Union, Dict
from copy import deepcopy

from .utils import AbstractTripletsRetriever, BaseGraphSearchConfig
from .AStarTripletsRetriever import AStarGraphSearchConfig, AStarTripletsRetriever
from .WaterCirclesTripletsRetriever import WaterCirclesSearchConfig, WaterCirclesRetriever
from .NaiveBFSTripletsRetriever import NaiveBFSTripletsRetriever
from .BeamSearchTripletsRetriever import BeamSearchTripletsRetriever
from ......utils.data_structs import QueryInfo, Triplet, create_id, NodeType, NODES_TYPES_MAP
from ......kg_model import KnowledgeGraphModel
from ......utils import Logger
from ......utils.cache_kv import CacheKV, CacheUtils
from ......db_drivers.kv_driver import KeyValueDriverConfig, KVDBConnectionConfig

@dataclass
class MixturedGraphSearchConfig(BaseGraphSearchConfig):
    """Конфигурация комбинированного алгоритма извлечения триплетов из графа знаний.

    :param astar_config: Конфигурация A*-алгоритма поиска. Значение по умолчанию AStarGraphSearchConfig().
    :type astar_config: AStarGraphSearchConfig
    :param bfs_config: Конфигурация BFS-алгоритма поиска. Значение по умолчанию BFSSearchConfig().
    :type bfs_config: BFSSearchConfig
    """
    retriever1_name: str = 'astar'
    retriever1_config: Union[BaseGraphSearchConfig, Dict] = field(default_factory=lambda: AStarGraphSearchConfig())
    retriever2_name: str = 'watercircles'
    retriever2_config: Union[BaseGraphSearchConfig, Dict] = field(default_factory=lambda: WaterCirclesSearchConfig())
    accepted_node_types: List[NodeType] = field(default_factory=lambda:[NodeType.object, NodeType.hyper, NodeType.episodic, NodeType.time])
    cache_table_name: str = 'qa_mixture_t_retriever_cache'

    def to_str(self):
        retriever1_pair = (self.retriever1_name, self.retriever1_config.to_str())
        retriever2_pair = (self.retriever2_name, self.retriever2_config.to_str())
        sorted_pretr = sorted([retriever1_pair, retriever2_pair], key=lambda p: p[0])

        str_accepted_nodes = ";".join(sorted(list(map(lambda v: v.value, self.accepted_node_types))))
        return f"{sorted_pretr[0][0]};{sorted_pretr[0][1]};{sorted_pretr[1][0]};{sorted_pretr[1][1]};{str_accepted_nodes}"

class MixturedTripletsRetriever(AbstractTripletsRetriever):
    """Класс предназначен для извлечения триплетов из графа знаний с помощью комбинации BFS- и A*-алгоритмов поиска.

    :param kg_model: Модель памяти (графа знаний) ассистента.
    :type kg_model: KnowledgeGraphModel
    :param config: Конфигурация комбинированного алгоритма поиска. Значение по умолчанию MixturedGraphSearchConfig().
    :type config: MixturedGraphSearchConfig
    :param log: Отладочный класс для журналирования/мониторинга поведения инициализируемой компоненты. Значение по умолчанию Logger(LOG_PATH).
    :type log: Logger
    :param verbose: Если True, то информация о поведении класса будет сохраняться в stdout и файл-журналирования (log), иначе только в файл. Значение по умолчанию False.
    :type verbose: bool
    """
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
            'watercircles': WaterCirclesRetriever,
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

    def get_relevant_triplets(self, query_info: QueryInfo) -> List[Triplet]:
        self.log("START KNOWLEDGE RETRIEVING ...", verbose=self.verbose)
        self.log(f"RETRIEVER: MixturedTripletsRetriever ({self.config.retriever1_name} + {self.config.retriever2_name})", verbose=self.verbose)
        self.log(f"BASE_QUESTION ID: {create_id(query_info.query)}", verbose=self.verbose)
        self.log(f"BASE_QUESTION: {query_info.query}", verbose=self.verbose)

        triplets1 = self.retriever1.get_relevant_triplets(query_info)
        triplets2 = self.retriever2.get_relevant_triplets(query_info)

        self.log(f"Количество триплетов, извлечённых с помощью {self.config.retriever1_name}/{self.config.retriever2_name}: {len(triplets1)}/{len(triplets2)}",
                 verbose=self.verbose)

        # отбираем только уникальные триплеты (по их идентификаторам)
        unique_triplets = dict()
        for triplet in triplets1 + triplets2:
            unique_triplets[triplet.id] = deepcopy(triplet)

        return list(unique_triplets.values())
