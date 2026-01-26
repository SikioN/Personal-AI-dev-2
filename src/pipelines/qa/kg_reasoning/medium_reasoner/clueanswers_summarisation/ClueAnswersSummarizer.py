from dataclasses import dataclass, field
from typing import Tuple, Union, List, Dict
from copy import deepcopy
import json

from .config import DEFAULT_CASUMM_TASK_CONFIG, CQSUMM_MAIN_LOG_PATH
from ......utils.data_structs import QueryInfo
from ......utils import ReturnInfo, Logger, AgentTaskSolverConfig, AgentTaskSolver
from ......agents import AgentDriver, AgentDriverConfig
from ......utils.data_structs import create_id
from ......db_drivers.kv_driver import KeyValueDriverConfig
from ......db_drivers.vector_driver import VectorDBInstance
from ......utils.cache_kv import CacheKV, CacheUtils

@dataclass
class ClueAnswersSummarizerConfig:
    lang: str = 'auto'
    adriver_config: AgentDriverConfig = field(default_factory=lambda: AgentDriverConfig())
    canswers_summarisation_agent_task_config: AgentTaskSolverConfig = field(default_factory=lambda: DEFAULT_CASUMM_TASK_CONFIG)

    cache_table_name: str = "medreasn_cquerysumm_main_stage_cache"
    log: Logger = field(default_factory=lambda: Logger(CQSUMM_MAIN_LOG_PATH))
    verbose: bool = False

    def to_str(self):
        return f"{self.lang}|{self.adriver_config.to_str()}|{self.canswers_summarisation_agent_task_config.version}"

class ClueAnswersSummarizer(CacheUtils):
    def __init__(self, config: ClueAnswersSummarizerConfig = ClueAnswersSummarizerConfig(), 
                 cache_kvdriver_config: KeyValueDriverConfig = None, cache_llm_inference: bool = True):
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

        self.clueanswers_summ_solver = AgentTaskSolver(
            self.agent, self.config.canswers_summarisation_agent_task_config, agents_cache_config)
        
        self.log = self.config.log
        self.verbose = self.config.verbose

    def get_cache_key(self, search_query: str, clue_queries: List[str], clue_answers: List[str]) -> List[str]:
        str_cluequeries = ';'.join(clue_queries)
        str_clueanswers = ';'.join(clue_answers)
        return [search_query, str_cluequeries, str_clueanswers]

    @CacheUtils.cache_method_output
    def perform(self, search_query: str, clue_queries: List[str], clue_answers: List[str]) -> Tuple[str, ReturnInfo]:
        self.log("START CLUE-QUERIES SUMMARISATION...", verbose=self.config.verbose)
        self.log(f"SEARCH_QUERY ID: {create_id(search_query)}", verbose=self.config.verbose)
        self.log(f"SEARCH_QUERY: {search_query}", verbose=self.config.verbose)
        self.log(f"CLUE-QUERIES: {clue_queries}", verbose=self.config.verbose)
        self.log(f"CLUE-ANSWERS: {clue_answers}", verbose=self.config.verbose)
        summ_answer, info = None, ReturnInfo()

        if len(search_query) < 1 or len(clue_queries) < 1 or len(clue_answers) != len(clue_queries):
            raise ValueError

        self.log("Выполненяем суммаризацию clue-answers с помощью LLM-агента...", verbose=self.config.verbose)
        summ_answer, status = self.clueanswers_summ_solver.solve(
            lang=self.config.lang, search_query=search_query, 
            clues_queries=clue_queries, clue_answers=clue_answers)
        self.log(f"RESULT: {summ_answer}", verbose=self.verbose)

        info.status = status
        self.log(f"STATUS: {info.status}", verbose=self.verbose)

        return summ_answer, info
