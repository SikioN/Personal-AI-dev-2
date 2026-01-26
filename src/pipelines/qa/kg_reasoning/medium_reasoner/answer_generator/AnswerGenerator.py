from dataclasses import dataclass, field
from typing import Tuple, Union, List
from copy import deepcopy

from .config import DEFAULT_ANSWCLS_TASK_CONFIG, DEFAULT_ANSWGEN_TASK_CONFIG, ANSWGEN_MAIN_LOG_PATH
from ..utils import SearchPlanInfo
from ......utils import ReturnInfo, Logger, AgentTaskSolverConfig, AgentTaskSolver
from ......utils.errors import ReturnStatus
from ......agents import AgentDriver, AgentDriverConfig
from ......utils.data_structs import create_id
from ......db_drivers.kv_driver import KeyValueDriverConfig
from ......utils.cache_kv import CacheKV, CacheUtils

@dataclass
class AnswerGeneratorConfig:
    lang: str = 'auto'
    adriver_config: AgentDriverConfig = field(default_factory=lambda: AgentDriverConfig())
    answer_classifier_agent_task_config: AgentTaskSolverConfig = field(default_factory=lambda: DEFAULT_ANSWCLS_TASK_CONFIG)
    answer_generator_agent_task_config: AgentTaskSolverConfig = field(default_factory=lambda: DEFAULT_ANSWGEN_TASK_CONFIG)

    cache_table_name: str = "medreasn_answgen_main_stage_cache"
    log: Logger = field(default_factory=lambda: Logger(ANSWGEN_MAIN_LOG_PATH))
    verbose: bool = False

    def to_str(self):
        return f"{self.lang}|{self.adriver_config.to_str()}|{self.answer_classifier_agent_task_config.version}|{self.answer_generator_agent_task_config.version}"

class AnswerGenerator(CacheUtils):
    def __init__(self, config: AnswerGeneratorConfig = AnswerGeneratorConfig(), 
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

        self.answer_classify_solver = AgentTaskSolver(
            self.agent, self.config.answer_classifier_agent_task_config, agents_cache_config)
        self.answer_gen_solver = AgentTaskSolver(
            self.agent, self.config.answer_generator_agent_task_config, agents_cache_config)
        
        self.log = self.config.log
        self.verbose = self.config.verbose

    def get_cache_key(self, search_plan: SearchPlanInfo) -> List[object]:
        return [search_plan.to_str(), self.config.to_str()]

    @CacheUtils.cache_method_output
    def perform(self, search_plan: SearchPlanInfo) -> Tuple[str, ReturnInfo]:
        self.log("START ANSWER-TRYING...", verbose=self.config.verbose)
        answer, info = None, ReturnInfo()
        self.log(f"QUERY ID: {create_id(search_plan.base_query)}", verbose=self.config.verbose)
        self.log(f"CURRENT PLAN: {search_plan}", verbose=self.config.verbose)
        
        self.log("Выполняем проверку на возможность генерации релевантного ответа...",verbose=self.verbose)
        can_answer, status = self.answer_classify_solver.solve(
            lang=self.config.lang, search_plan=search_plan)
        self.log(f"RESULT: {can_answer}", verbose=self.config.verbose)
        
        if status == ReturnStatus.success:
            if can_answer:
                self.log("Выполняем генерацию ответа...",verbose=self.verbose)
                answer, status = self.answer_gen_solver.solve(
                    lang=self.config.lang, search_plan=search_plan)
                self.log(f"RESULT: {answer}", verbose=self.config.verbose)
                
            else:
                self.log("На основании информации, полученной по текущему плану нельзя сгенерировать релевантный ответ.",verbose=self.verbose)

        info.status = status
        self.log(f"STATUS: {info.status}", verbose=self.config.verbose)    

        return answer, info