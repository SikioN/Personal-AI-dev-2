from dataclasses import dataclass, field
from typing import Union, List, Tuple
from copy import deepcopy

from .configs import KC_MAIN_LOG_PATH
from ......utils import Logger, ReturnStatus, ReturnInfo
from ......utils.errors import STATUS_MESSAGE
from ......utils.data_structs import QueryInfo, create_id
from ......kg_model import KnowledgeGraphModel
from ......db_drivers.vector_driver import VectorDBInstance
from ......utils.cache_kv import CacheKV, CacheUtils
from ......db_drivers.kv_driver import KeyValueDriverConfig

@dataclass
class KnowledgeComparatorConfig:
    """Конфигурация "Knowledge Comparator"-стадии QA-конвейера.

    :param threshold: Нижний порог близости между эмбеддингами сущностей и вершин для их сопоставления (matching). Значение по умолчанию 0.5.
    :type threshold: float
    :param fetch_n: Служебный гиперпараметр. Значение по умолчанию 20.
    :type fetch_n: int
    :param max_k: Максимальное количество вершин из графа знаний, которое может быть сопоставлено одной сущности. Значение по умолчанию 1.
    :type max_k: int
    :param k_compare: Значение по умолчанию 5.
    :type k_compare: int
    :param log: Отладочный класс для журналирования/мониторинга поведения инициализируемой компоненты. Значение по умолчанию Logger(COMPARATOR_LOG_PATH).
    :type log: Logger
    :param verbose: Если True, то информация о поведении класса будет сохраняться в stdout и файл-журналирования (log), иначе только в файл. Значение по умолчанию False.
    :type verbose: bool
    """
    threshold: float = 0.5
    fetch_n: int = 20
    max_k: int = 1
    k_compare: int = 5

    cache_table_name: Union[str, None] = 'qa_kcomparator_stage_cache'

    log: Logger = field(default_factory=lambda: Logger(KC_MAIN_LOG_PATH))
    verbose: bool = False

    def to_str(self):
        return f"{self.threshold};{self.fetch_n};{self.max_k}:{self.k_compare}"

class KnowledgeComparator(CacheUtils):
    """Верхнеуровневый класс второй стадии QA-конвейера для сопоставления информации из user-вопроса
    с имеющейся информацией в памяти (графе знаний) ассистента.

    :param kg_model: Модель памяти (графа знаний) ассистента.
    :type kg_model: KnowledgeGraphModel
    :param config: Конфигурация "Knowledge Comparator"-стадии. Значение по умолчанию KnowledgeComparatorConfig().
    :type config: KnowledgeComparatorConfig
    """
    def __init__(self, kg_model: KnowledgeGraphModel, config: KnowledgeComparatorConfig = KnowledgeComparatorConfig(),
                 cache_kvdriver_config: KeyValueDriverConfig = None) -> None:
        self.config = config
        self.log = self.config.log
        self.verbose = self.config.verbose
        self.kg_model = kg_model

        if cache_kvdriver_config is not None and self.config.cache_table_name is not None:
            cache_config = deepcopy(cache_kvdriver_config)
            cache_config.db_config.db_info['table'] = self.config.cache_table_name
            self.cachekv = CacheKV(cache_config)
        else:
            self.cachekv = None

    def get_cache_key(self, query_info: QueryInfo) -> List[object]:
        return [self.config.to_str(), query_info.to_str()]

    @CacheUtils.cache_method_output
    def link_kgnodes_to_query(self, query_info: QueryInfo) -> Tuple[List[object], List[object], ReturnInfo]:
        """Метод предназначен для сопоставления (матчинга) сущностей, извлечённых из user-вопроса, с вершинами из графа знаний ассистента.

        :param query_structure: Структура данных, которая хранит user-вопрос и извлечённые из него сущности.
        :type query_structure: QueryInfo
        :return: Статс завершения операции с пояснительной информацией.
        :rtype: ReturnInfo
        """

        self.log("START MATCHING KEY WORDS ...", verbose=self.config.verbose)
        self.log(f"BASE_QUESTION ID: {create_id(query_info.query)}", verbose=self.config.verbose)
        self.log(f"BASE_QUESTION: {query_info.query}", verbose=self.config.verbose)
        self.log(f"ENTITIES: {query_info.entities}", verbose=self.config.verbose)

        info = ReturnInfo()
        linked_nodes_by_entities, linked_nodes, linked_scores = [], [], []

        for entity in query_info.entities:
            entity_embedding = self.kg_model.embeddings_struct.embedder.encode_queries([entity])[0]
            entity_instance = VectorDBInstance(embedding=entity_embedding)

            nodes_with_scores = self.kg_model.embeddings_struct.vectordbs['nodes'].retrieve(
                [entity_instance], n_results=self.config.fetch_n)[0]
            filtered_nodes = list(filter(lambda node_item: node_item[0] < self.config.threshold, nodes_with_scores))
            cur_linked_nodes = list(map(lambda node_item: node_item[1], filtered_nodes))
            linked_nodes += cur_linked_nodes[:self.config.max_k]
            linked_scores += list(map(lambda node_item: node_item[0], filtered_nodes))[:self.config.max_k]

            cur_documents = list(map(lambda item: item.document, cur_linked_nodes))
            cur_documents_lower = list(map(lambda document: document.lower(), cur_documents))
            if entity.lower() in cur_documents_lower[:self.config.k_compare]:
                cur_unique_names = [entity]
            else:
                cur_unique_names = [entity] + cur_documents[:self.config.max_k]
            linked_nodes_by_entities.append(cur_unique_names)

        if len(linked_nodes) == 0:
            info.status = ReturnStatus.zero_linked_nodes
            info.message = STATUS_MESSAGE[info.status]

        self.log(f"RESULT: {len(linked_nodes)}", verbose=self.config.verbose)
        for score, node in zip(linked_scores,linked_nodes):
            self.log(f"*[{node.id}] {score} | {node.document}", verbose=self.config.verbose)

        self.log(f"STATUS: {STATUS_MESSAGE[info.status]}", verbose=self.config.verbose)

        return linked_nodes, linked_nodes_by_entities, info
