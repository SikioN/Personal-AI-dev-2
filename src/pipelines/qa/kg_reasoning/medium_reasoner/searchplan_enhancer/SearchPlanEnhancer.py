from dataclasses import dataclass, field
from typing import Tuple, Union, List
from copy import deepcopy

from .config import PLANENH_MAIN_LOG_PATH, DEFAULT_PLANINIT_TASK_CONFIG, DEFAULT_PLANENH_TASK_CONFIG, DEFAUL_ENHCLASSIFY_TASK_CONFIG
from ..utils import SearchPlanInfo
from ......utils import ReturnInfo, Logger, AgentTaskSolverConfig, AgentTaskSolver
from ......utils.errors import ReturnStatus
from ......agents import AgentDriver, AgentDriverConfig
from ......utils.data_structs import create_id
from ......db_drivers.kv_driver import KeyValueDriverConfig
from ......utils.cache_kv import CacheKV, CacheUtils

@dataclass
class SearchPlanEnhancerConfig:
    lang: str = 'auto'
    adriver_config: AgentDriverConfig = field(default_factory=lambda: AgentDriverConfig())
    plan_initing_agent_task_config: AgentTaskSolverConfig = field(default_factory=lambda: DEFAULT_PLANINIT_TASK_CONFIG)
    enhance_classifier_agent_task_config: AgentTaskSolverConfig = field(default_factory=lambda: DEFAUL_ENHCLASSIFY_TASK_CONFIG)
    plan_enhancing_agent_task_config: AgentTaskSolverConfig = field(default_factory=lambda: DEFAULT_PLANENH_TASK_CONFIG)

    cache_table_name: str = "medreasn_planenh_main_stage_cache"
    log: Logger = field(default_factory=lambda: Logger(PLANENH_MAIN_LOG_PATH))
    verbose: bool = False

    def to_str(self):
        return f"{self.lang}|{self.adriver_config.to_str()}|{self.plan_initing_agent_task_config.version}|{self.plan_enhancing_agent_task_config.version}"

class SearchPlanEnhancer(CacheUtils):
    def __init__(self, config: SearchPlanEnhancerConfig = SearchPlanEnhancerConfig(), 
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

        self.plan_initialing_solver = AgentTaskSolver(
            self.agent, self.config.plan_initing_agent_task_config, agents_cache_config)
        self.enhance_classify_solver = AgentTaskSolver(
            self.agent, self.config.enhance_classifier_agent_task_config, agents_cache_config)
        self.plan_enhancing_solver = AgentTaskSolver(
            self.agent, self.config.plan_enhancing_agent_task_config, agents_cache_config)
        
        self.log = self.config.log
        self.verbose = self.config.verbose

    def get_cache_key(self, search_step: int, search_plan: SearchPlanInfo) -> List[object]:
        return [str(search_step), search_plan.to_str(), self.config.to_str()]

    @CacheUtils.cache_method_output
    def perform(self, search_step: int, search_plan: SearchPlanInfo) -> Tuple[SearchPlanInfo, ReturnInfo]:
        self.log("START SEARCH-PLAN INITING/ENHANCING...", verbose=self.config.verbose)
        enhanced_search_plan, info = None, ReturnInfo()
        self.log(f"QUERY ID: {create_id(search_plan.base_query)}", verbose=self.config.verbose)
        self.log(f"CURRENT PLAN: {search_plan}", verbose=self.config.verbose)
        
        if search_step < 0:
            raise ValueError

        if search_step == 0:
            self.log("Генерируем план поиска с нуля...",verbose=self.verbose)
            new_search_steps, status = self.plan_initialing_solver.solve(lang=self.config.lang, query=search_plan.base_query)
            str_searchplan = "\n".join([f'{i}. {gen_step}' for i,gen_step in enumerate(new_search_steps)])
            self.log(f"RESULT: {len(new_search_steps)}\n{str_searchplan}", verbose=self.config.verbose)

            if status == ReturnStatus.success:
                enhanced_search_plan = deepcopy(search_plan)
                enhanced_search_plan.search_steps = new_search_steps
                enhanced_search_plan.steps_answers = []
        else:
            self.log("Выполняем проверку на необходимость улучшения следующих шагов поиска в плане...",verbose=self.verbose)
            need_enhance, status = self.enhance_classify_solver.solve(
                lang=self.config.lang, query=search_plan.base_query,
                search_steps=search_plan.search_steps, steps_answers=search_plan.steps_answers[:search_step])
            self.log(f"RESULT: {need_enhance}", verbose=self.config.verbose)
            
            if status == ReturnStatus.success:
                if need_enhance:
                    self.log("Улучшаем следующие шаги поиска в плане...",verbose=self.verbose)
                    enhanced_steps, status = self.plan_enhancing_solver.solve(
                        lang=self.config.lang, query=search_plan.base_query,
                        search_steps=search_plan.search_steps,
                        steps_answers=search_plan.steps_answers[:search_step])
                    str_enhancedsteps = "\n".join([f'{i}. {gen_step}' for i,gen_step in enumerate(enhanced_steps)])
                    self.log(f"RESULT: {len(enhanced_steps)}\n{str_enhancedsteps}", verbose=self.config.verbose)
                    
                    if status == ReturnStatus.success:
                        enhanced_search_plan = deepcopy(search_plan)
                        enhanced_search_plan.search_steps = search_plan.search_steps[:search_step] + enhanced_steps
                        enhanced_search_plan.steps_answers = search_plan.steps_answers[:search_step]

                else:
                    self.log("Улучшение шагов поиска не требуется...",verbose=self.verbose)
                    enhanced_search_plan = deepcopy(search_plan)

        info.status = status
        self.log(f"STATUS: {info.status}", verbose=self.config.verbose)    

        return enhanced_search_plan, info