from dataclasses import dataclass, field
from typing import Tuple, Union

from .query_parser import QueryLLMParser, QueryLLMParserConfig
from .knowledge_comparator import KnowledgeComparator, KnowledgeComparatorConfig
from .knowledge_retriever import KnowledgeRetriever, KnowledgeRetrieverConfig
from .answer_generator import QALLMGenerator, QALLMGeneratorConfig
from ..utils import AbstractKGReasoner, BaseKGReasonerConfig
from .....utils.data_structs import create_id
from .....utils import Logger, ReturnInfo, ReturnStatus
from .....utils.errors import STATUS_MESSAGE
from .....utils.data_structs import QueryInfo
from .....kg_model import KnowledgeGraphModel
from .....db_drivers.kv_driver import KeyValueDriverConfig

WKGR_MAIN_LOG_PATH = 'log/qa/kg_reasoner/weak/main'

@dataclass
class WeakKGReasonerConfig(BaseKGReasonerConfig):
    """

    :param query_parser_config: Конфигурация первой стадии QA-конвейера: извлечение сущностей из user-вопроса. Значение по умолчанию QueryLLMParserConfig().
    :type query_parser_config: QueryLLMParserConfig
    :param knowledge_comparator_config: Конфигурация второй стадии QA-конвейера: сопоставление (match) сущностей из user-вопроса с информацией в графе знаний. Значение по умолчанию KnowledgeComparatorConfig().
    :type knowledge_comparator_config: KnowledgeComparatorConfig
    :param knowledge_retriever_config: Конфигурация третьей стадии QA-конвейера: извлечение релевантной информации из графа знаний для user-вопроса. Значение по умолчанию KnowledgeRetrieverConfig().
    :type knowledge_retriever_config: KnowledgeRetrieverConfig
    :param answer_generator_config: Конфигурация четвёртой стадии QA-конвейера: условная генерация ответа на user-вопрос. Значение по умолчанию QALLMGeneratorConfig().
    :type answer_generator_config: QALLMGeneratorConfig
    :param log: Отладочный класс для журналирования/мониторинга поведения инициализируемой компоненты. Значение по умолчанию Logger(LOG_PATH).
    :type log: Logger
    :param verbose: Если True, то информация о поведении класса будет сохраняться в stdout и файл-журналирования (log), иначе только в файл. Значение по умолчанию False.
    :type verbose: bool
    """
    query_parser_config: QueryLLMParserConfig = field(default_factory=lambda: QueryLLMParserConfig())
    knowledge_comparator_config: KnowledgeComparatorConfig = field(default_factory=lambda: KnowledgeComparatorConfig())
    knowledge_retriever_config: KnowledgeRetrieverConfig = field(default_factory=lambda: KnowledgeRetrieverConfig())
    answer_generator_config: QALLMGeneratorConfig = field(default_factory=lambda: QALLMGeneratorConfig())

    log: Logger = field(default_factory=lambda: Logger(WKGR_MAIN_LOG_PATH))
    verbose: bool = False

class WeakKGReasoner(AbstractKGReasoner):

    def __init__(self, kg_model: KnowledgeGraphModel, config: WeakKGReasonerConfig = WeakKGReasonerConfig(),
                 cache_kvdriver_config: Union[KeyValueDriverConfig, None] = None):
        """_summary_

        :param kg_model: _description_
        :type kg_model: KnowledgeGraphModel
        :param config: _description_, defaults to WeakKGReasonerConfig()
        :type config: WeakKGReasonerConfig, optional
        :param cache_kvdriver_config: _description_, defaults to None
        :type cache_kvdriver_config: Union[KeyValueDriverConfig, None], optional
        """
        self.config = config
        self.kg_model = kg_model
        self.log = config.log
        self.verbose = config.verbose

        if self.config.query_parser_config is None:
            self.query_parser = None
            self.knowledge_comparator = None
        else:
            self.query_parser = QueryLLMParser(
                self.config.query_parser_config,
                cache_kvdriver_config)
            self.knowledge_comparator = KnowledgeComparator(
                self.kg_model, self.config.knowledge_comparator_config,
                cache_kvdriver_config)

        self.knowledge_retriever = KnowledgeRetriever(
            self.kg_model, self.config.knowledge_retriever_config,
            cache_kvdriver_config)
        self.answer_generator = QALLMGenerator(
            self.config.answer_generator_config,
            cache_kvdriver_config)

    def clear_kv_caches(self) -> None:
        if self.query_parser is not None:
            self.query_parser.cachekv.kv_conn.clear()
            self.query_parser.kw_extraction_solver.cachekv.kv_conn.clear()

            self.knowledge_comparator.cachekv.kv_conn.clear()

        self.knowledge_retriever.cachekv.kv_conn.clear()
        self.knowledge_retriever.graph_retriever.cachekv.kv_conn.clear()

        if self.knowledge_retriever.triplets_filter is not None:
            self.knowledge_retriever.triplets_filter.cachekv.kv_conn.clear()

        self.answer_generator.cachekv.kv_conn.clear()
        self.answer_generator.answer_generator_solver.cachekv.kv_conn.clear()

    def perform(self, query: str) -> Tuple[str, ReturnInfo]:
        self.log("START WEAK KG-REASONING...", verbose=self.config.verbose)
        self.log(f"BASE_QUESTION ID: {create_id(query)}", verbose=self.config.verbose)
        self.log(f"BASE_QUESTION: {query}", verbose=self.config.verbose)

        answer = None
        query_info = QueryInfo(query=query)
        self.log("STAGE#1.1 - KEY WORDS EXTRACTION", verbose=self.config.verbose)
        if self.query_parser is None:
            self.log("Stage #1.1 and #1.2 was omited!", verbose=self.config.verbose)
        else:
            query_info.entities, info = self.query_parser.extract_entities(query_info.query)
            self.log(f"RESULT:\n* EXTRACTED ENTITIES AMOUNT - {len(query_info.entities)}\n* EXTRACTED ENTITIES - {query_info.entities}", verbose=self.config.verbose)

        if self.query_parser is not None and info.status == ReturnStatus.success:
            self.log("STAGE#1.2 - MATCHING KEY WORDS TO KG-NODES", verbose=self.config.verbose)
            query_info.linked_nodes, query_info.linked_nodes_by_entities, info = self.knowledge_comparator.link_kgnodes_to_query(query_info)

            self.log(f"RESULT: {len(query_info.linked_nodes)}", verbose=self.config.verbose)
            for node in query_info.linked_nodes:
                self.log(f"*[{node.id}] {node.document}", verbose=self.config.verbose)

        if self.query_parser is None or info.status == ReturnStatus.success:
            self.log("STAGE#3 - RETRIEVING RELEVANT TRIPLETS FROM KG", verbose=self.config.verbose)
            retrieved_triplets, info = self.knowledge_retriever.retrieve(query_info)

            self.log(f"RESULT: {len(retrieved_triplets)}", verbose=self.config.verbose)
            for triplet in retrieved_triplets:
                self.log(f"* {triplet}", verbose=self.config.verbose)

        if info.status == ReturnStatus.success:
            self.log("STAGE#4 - ANSWER GENERATION", verbose=self.config.verbose)
            answer, info = self.answer_generator.generate(query_info.query, retrieved_triplets)
            self.log(f"RESULT:\n* ANSWER - {answer}", verbose=self.config.verbose)

        self.log(f"STATUS: {info.status}", verbose=self.config.verbose)

        return answer, info
