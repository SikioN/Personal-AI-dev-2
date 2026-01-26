from dataclasses import dataclass, field
from typing import Tuple, Union, List
from copy import deepcopy

from .config import AAGG_MAIN_LOG_PATH, DEFAULT_SUBASUMM_TASK_CONFIG
from ..query_preprocessing.utils import QueryPreprocessingInfo
from ....utils import ReturnInfo, Logger, AgentTaskSolverConfig, AgentTaskSolver
from ....agents import AgentDriver, AgentDriverConfig
from ....utils.data_structs import create_id
from ....db_drivers.kv_driver import KeyValueDriverConfig
from ....utils.cache_kv import CacheKV, CacheUtils

@dataclass
class AnswersAggregatorConfig:
    """_summary_

    :param lang: ...
    :type lang: str, optional
    :param adriver_config: ...
    :type adriver_config:AgentDriverConfig, optional
    :param suba_summarisation_agent_task_config: ...
    :type suba_summarisation_agent_task_config: AgentTaskSolverConfig, optional

    :param cache_table_name: ...
    :type cache_table_name: str, optional
    :param log: Отладочный класс для журналирования/мониторинга поведения инициализируемой компоненты. Значение по умолчанию Logger(LOG_PATH).
    :type log: Logger
    :param verbose: Если True, то информация о поведении класса будет сохраняться в stdout и файл-журналирования (log), иначе только в файл. Значение по умолчанию False.
    :type verbose: bool
    """
    lang: str = 'auto'
    adriver_config: AgentDriverConfig = field(default_factory=lambda: AgentDriverConfig())
    suba_summarisation_agent_task_config: AgentTaskSolverConfig = field(default_factory=lambda: DEFAULT_SUBASUMM_TASK_CONFIG)

    cache_table_name = "answers_aggregation_main_stage_cache"
    log: Logger = field(default_factory=lambda: Logger(AAGG_MAIN_LOG_PATH))
    verbose: bool = False

    def to_str(self):
        return f"{self.lang}|{self.adriver_config.to_str()}|{self.suba_summarisation_agent_task_config.version}"

class AnswersAggregator(CacheUtils):
    def __init__(self, config: AnswersAggregatorConfig = AnswersAggregatorConfig(),
                 cache_kvdriver_config: KeyValueDriverConfig = None, cache_llm_inference: bool = True) -> None:
        """_summary_

        :param config: _description_, defaults to AnswersAggregatorConfig()
        :type config: AnswersAggregatorConfig, optional
        :param cache_kvdriver_config: _description_, defaults to None
        :type cache_kvdriver_config: KeyValueDriverConfig, optional
        :param cache_llm_inference: _description_, defaults to True
        :type cache_llm_inference: bool, optional
        """
        self.config = config

        if cache_kvdriver_config is not None and self.config.cache_table_name is not None:
            cache_config = deepcopy(cache_kvdriver_config)
            cache_config.db_config.db_info['table'] = self.config.cache_table_name
            self.cachekv = CacheKV(cache_config)
        else:
            self.cachekv = None

        self.agent = AgentDriver.connect(config.adriver_config)
        agents_cache_config = None
        if cache_llm_inference:
            agents_cache_config = cache_kvdriver_config

        self.subanswers_summarisation_solver = AgentTaskSolver(
            self.agent, self.config.suba_summarisation_agent_task_config, agents_cache_config)

        self.log = self.config.log
        self.verbose = self.config.verbose

    def get_cache_key(self, query_info: QueryPreprocessingInfo, sub_answers: List[str]) -> List[object]:
        """_summary_

        :param query_info: _description_
        :type query_info: QueryPreprocessingInfo
        :param sub_answers: _description_
        :type sub_answers: List[str]
        :return: _description_
        :rtype: List[object]
        """
        str_sub_answers = "|".join(sub_answers)
        return [query_info.to_str(), str_sub_answers, self.config.to_str()]

    @CacheUtils.cache_method_output
    def perform(self, query_info: QueryPreprocessingInfo, sub_answers: List[str]) -> Tuple[str, ReturnInfo]:
        """_summary_

        :param query_info: _description_
        :type query_info: QueryPreprocessingInfo
        :param sub_answers: _description_
        :type sub_answers: List[str]
        :raises ValueError: _description_
        :raises ValueError: _description_
        :raises ValueError: _description_
        :return: _description_
        :rtype: Tuple[str, ReturnInfo]
        """
        self.log("START ANSWERS AGGREGATION...", verbose=self.config.verbose)
        self.log(f"BASE_QUESTION ID: {create_id(query_info.base_query)}", verbose=self.config.verbose)
        self.log(f"QUERY_INFO: {query_info}", verbose=self.config.verbose)
        self.log(f"SUB_ANSWERS: {sub_answers}", verbose=self.config.verbose)
        final_answer, info = None, ReturnInfo()

        if len(sub_answers) < 0:
            raise ValueError
        elif len(sub_answers) == 1:
            final_answer = sub_answers[0]
        else:
            if query_info.enchanced_query is not None:
                query = query_info.enchanced_query
            elif query_info.denoised_query is not None:
                query = query_info.denoised_query
            elif query_info.base_query is not None:
                query = query_info.base_query
            else:
                raise ValueError

            sub_queries = query_info.decomposed_query
            if len(sub_queries) < 2 or len(sub_answers) != len(sub_queries):
                raise ValueError

            self.log("Выполнение суммаризации ответов с помощью LLM-агента...", verbose=self.config.verbose)
            final_answer, status = self.subanswers_summarisation_solver.solve(
                lang=self.config.lang, query=query, sub_queries=sub_queries,
                sub_answers=sub_answers)
            self.log(f"RESULT: {final_answer}", verbose=self.verbose)
            info.status = status

        self.log(f"STATUS: {info.status}", verbose=self.verbose)

        return final_answer, info
