from dataclasses import dataclass, field
from typing import Tuple, Union

from .configs import QA_MAIN_LOG_PATH
from .kg_reasoning import KnowledgeGraphReasonerConfig, KnowledgeGraphReasoner
from .query_preprocessing import QueryPreprocessor, QueryPreprocessorConfig
from .query_preprocessing.utils import QueryPreprocessingInfo
from .answers_aggregation import AnswersAggregator, AnswersAggregatorConfig
from ...kg_model import KnowledgeGraphModel
from ...utils import Logger, ReturnStatus, ReturnInfo
from ...utils.data_structs import create_id
from ...db_drivers.kv_driver import KeyValueDriverConfig

@dataclass
class QAPipelineConfig:
    """
    _summary_

    :param preprocessor_config: ... Значение по умолчанию None.
    :type preprocessor_config: Union[QueryPreprocessorConfig, None], optional
    :param reasoner_config: ... Значение по умолчанию KnowledgeGraphReasonerConfig().
    :type reasoner_config: KnowledgeGraphReasonerConfig, optional
    :param aggregator_config: ... Значение по умолчанию AnswersAggregatorConfig().
    :type aggregator_config: AnswersAggregatorConfig, optional
    :param log: Отладочный класс для журналирования/мониторинга поведения инициализируемой компоненты. Значение по умолчанию Logger(LOG_PATH).
    :type log: Logger
    :param verbose: Если True, то информация о поведении класса будет сохраняться в stdout и файл-журналирования (log), иначе только в файл. Значение по умолчанию False.
    :type verbose: bool
    """
    preprocessor_config: Union[QueryPreprocessorConfig, None] = None
    reasoner_config: KnowledgeGraphReasonerConfig = field(default_factory=lambda: KnowledgeGraphReasonerConfig())
    aggregator_config: AnswersAggregatorConfig = field(default_factory=lambda: AnswersAggregatorConfig())

    log: Logger = field(default_factory=lambda: Logger(QA_MAIN_LOG_PATH))
    verbose: bool = False

class QAPipeline:
    """Верхнеуровневый класс QA-конвейера, отвечающий за генерацию ответов на вопросы.

    :param kg_model: Модель памяти (графа знаний) ассистента.
    :type kg_model: KnowledgeGraphModel
    :param config: Конфигурация QA-конвейера. Значение по умолчанию QAPipelineConfig().
    :type config: QAPipelineConfig, optional
    :param cache_kvdriver_config: Конфигурация структуры данных для кеширования промежутчных результатов в рамках компонент данного класса. Значение по умолчению None.
    :type cache_kvdriver_config: Union[KeyValueDriverConfig, None], optional
    """

    def __init__(self, kg_model: KnowledgeGraphModel, config: QAPipelineConfig = QAPipelineConfig(),
                 cache_kvdriver_config: Union[KeyValueDriverConfig, None] = None) -> None:
        self.config = config
        self.kg_model = kg_model
        self.log = config.log

        if self.config.preprocessor_config is not None:
            self.query_preprocessor = QueryPreprocessor(self.config.preprocessor_config, cache_kvdriver_config)
        else:
            self.query_preprocessor = None

        self.kg_reasoner = KnowledgeGraphReasoner(kg_model, self.config.reasoner_config, cache_kvdriver_config)
        self.answers_aggregator = AnswersAggregator(self.config.aggregator_config, cache_kvdriver_config)

        self.log = self.config.log
        self.verbose = self.config.verbose

    def clear_kv_caches(self) -> None:
        """_summary_
        """
        if self.config.preprocessor_config is not None:
            self.query_preprocessor.clear_kv_caches()
        self.kg_reasoner.clear_kv_caches()
        self.answers_aggregator.clear_kv_caches()

    def answer(self, query: str) -> Tuple[str, ReturnInfo]:
        """Метод предназначен для генерации ответа на user-вопрос. Ответ обуславливается на информацию из имеющегося графа знаний.

        :param query: User-вопрос на естественном языке.
        :type query: str
        :return: Кортеж из двух объектов: (1) cгенерированный ответ; (2) статус завершения операции с пояснительной информацией.
        :rtype: Tuple[str, ReturnInfo]
        """
        self.log("START QA-PIPELINE...", verbose=self.config.verbose)
        self.log(f"BASE_QUESTION ID: {create_id(query)}", verbose=self.config.verbose)
        self.log(f"BASE_QUESTION: {query}", verbose=self.config.verbose)

        final_answer, sub_answers, info = None, [], ReturnInfo()

        # Preprocessing stage
        if self.query_preprocessor is not None:
            self.log("Query Preprocesing...", verbose=self.config.verbose)
            query_info, prepr_info = self.query_preprocessor.perform(query)
            self.log(f"RESULT: {query_info}", verbose=self.config.verbose)
            if prepr_info.status != ReturnStatus.success:
                self.log("Operation ended with error!", verbose=self.verbose)
                info = prepr_info
            else:
                self.log("Operation ended successfully", verbose=self.verbose)
                info.occurred_warning.append(prepr_info.occurred_warning)
        else:
            self.log("Query Preprocesing-stage omited. Continue...", verbose=self.config.verbose)
            query_info = QueryPreprocessingInfo(base_query=query)

        self.log("Reasoning...", verbose=self.verbose)
        if info.status == ReturnStatus.success:
            sub_queries = []
            if query_info.decomposed_query is not None and len(query_info.decomposed_query) > 1:
                sub_queries = query_info.decomposed_query
            elif query_info.enchanced_query is not None:
                sub_queries = [query_info.enchanced_query]
            elif query_info.denoised_query is not None:
                sub_queries = [query_info.denoised_query]
            elif query_info.base_query is not None:
                sub_queries = [query_info.base_query]
            else:
                raise ValueError

            for i, cur_sub_query in enumerate(sub_queries):
                self.log(f"Processing sub_query #{i}: {cur_sub_query}", verbose=self.config.verbose)
                cur_sub_answer, reasoner_info = self.kg_reasoner.perform(cur_sub_query)
                self.log(f"RESULT: {cur_sub_answer}", verbose=self.config.verbose)
                if reasoner_info.status != ReturnStatus.success:
                    self.log("Operation ended with error!", verbose=self.verbose)
                    info = reasoner_info
                    break
                else:
                    self.log("Operation ended successfully", verbose=self.verbose)
                    info.occurred_warning.append(reasoner_info.occurred_warning)
                    sub_answers.append(cur_sub_answer)

            str_subqueriesanswers = "\n".join([f"- [{q}] {a}" for q, a in zip(sub_queries, sub_answers)])
            self.log(f"RESULT:\n{str_subqueriesanswers}", verbose=self.verbose)
        else:
            self.log("During previous steps error occurs.", verbose=self.verbose)

        self.log("Answers Aggregation...", verbose=self.verbose)
        if info.status == ReturnStatus.success:
            final_answer, aagg_info = self.answers_aggregator.perform(query_info, sub_answers)
            self.log(f"RESULT: {final_answer}", verbose=self.verbose)
            if aagg_info.status != ReturnStatus.success:
                self.log("Operation ended with error!", verbose=self.verbose)
                info = aagg_info
            else:
                self.log("Operation ended successfully", verbose=self.verbose)
        else:
            self.log("During previous steps error occurs.", verbose=self.verbose)

        self.log(f"STATUS: {info.status}", verbose=self.verbose)

        return final_answer, info
