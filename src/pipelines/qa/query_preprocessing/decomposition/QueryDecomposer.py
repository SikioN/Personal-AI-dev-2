from dataclasses import dataclass, field
from typing import Tuple, Union, List
from copy import deepcopy

from .config import QD_MAIN_LOG_PATH, DEFAULT_QD_TASK_CONFIG, DEFAULT_DC_TASK_CONFIG
from ..QueryPreprocessor import QueryPreprocessingInfo
from .....utils.cache_kv import CacheKV, CacheUtils
from .....utils.errors import STATUS_MESSAGE
from .....utils.data_structs import create_id
from .....agents import AgentDriverConfig, AgentDriver
from .....utils import ReturnInfo, Logger, ReturnStatus, AgentTaskSolverConfig, AgentTaskSolver
from .....db_drivers.kv_driver import KeyValueDriverConfig

@dataclass
class QueryDecomposerConfig:
    lang: str = "auto"
    adriver_config: AgentDriverConfig = field(default_factory=lambda: AgentDriverConfig())
    classify_agent_task_config: AgentTaskSolverConfig = field(default_factory=lambda: DEFAULT_DC_TASK_CONFIG)
    decompose_agent_task_config: AgentTaskSolverConfig = field(default_factory=lambda: DEFAULT_QD_TASK_CONFIG)
    cache_table_name: Union[str, None] = 'qp_decomposition_stage_cache'
    
    log: Logger = field(default_factory=lambda: Logger(QD_MAIN_LOG_PATH))
    verbose: bool = False

    def to_str(self):
        return f"{self.lang}|{self.adriver_config.to_str()}|{self.classify_agent_task_config.version}|{self.decompose_agent_task_config.version}"

class QueryDecomposer(CacheUtils):
    def __init__(self, config: QueryDecomposerConfig = QueryDecomposerConfig(), 
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
            agents_cache_config = cache_kvdriver_config if cache_llm_inference else None

        self.decompose_classifier_solver = AgentTaskSolver(
            self.agent, self.config.classify_agent_task_config, agents_cache_config)
        self.q_decomposition_solver = AgentTaskSolver(
            self.agent, self.config.decompose_agent_task_config, agents_cache_config)
        
        self.log = self.config.log
        self.verbose = self.config.verbose

    def get_cache_key(self, query_info: QueryPreprocessingInfo) -> List[object]:
        return [query_info.to_str(), self.config.to_str()]

    @CacheUtils.cache_method_output
    def perform(self, query_info: QueryPreprocessingInfo) -> Tuple[str, ReturnInfo]:
        decomposed_query, info = None, ReturnInfo()
        self.log("START QUERY DECOMPOSITION...", verbose=self.config.verbose)
        self.log(f"BASE_QUESTION ID: {create_id(query_info.base_query)}", verbose=self.config.verbose)
        self.log(f"QUERY INFO: {query_info}", verbose=self.config.verbose)

        if query_info.enchanced_query is not None:
            query = query_info.enchanced_query
        elif query_info.denoised_query is not None:
            query = query_info.denoised_query
        elif query_info.base_query is not None:
            query = query_info.base_query
        else:
            raise ValueError
        
        self.log("Выполние проверки на необходимость декомпозии вопроса с помощью LLM-агента...", verbose=self.config.verbose)
        need_to_decompose, status = self.decompose_classifier_solver.solve(lang=self.config.lang, query=query)
        if status != ReturnStatus.success:
            info.occurred_warning.append(status)

        if status == ReturnStatus.success:
            if need_to_decompose:
                self.log("Выполнение разбиения вопроса на независимые под-вопросы с помощью LLM-агента...", verbose=self.config.verbose)
                decomposed_query, status = self.q_decomposition_solver(lang=self.config.lang, query=query)
                if status != ReturnStatus.success:
                    info.occurred_warning.append(status)
            else:
                self.log("Выполнение декомпозиции вопроса не требуется", verbose=self.config.verbose)
                info.occurred_warning.append(ReturnStatus.decompose_noneed)
                decomposed_query = []

        if decomposed_query is None:
            info.status = ReturnStatus.empty_answer
            info.message = STATUS_MESSAGE[info.status]

        self.log(f"RESULT: {decomposed_query}", verbose=self.config.verbose)
        self.log(f"STATUS: {info.status}", verbose=self.config.verbose)

        return decomposed_query, info
