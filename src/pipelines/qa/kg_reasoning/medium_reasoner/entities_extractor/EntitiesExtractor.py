from dataclasses import dataclass, field
from typing import Tuple, Union, List, Dict
from copy import deepcopy

from .config import ENEXTR_MAIN_LOG_PATH, DEFAULT_ENT_EXTR_TASK_CONFIG, EntitiesExtractorConfig
from ......utils import ReturnInfo, Logger, AgentTaskSolverConfig, AgentTaskSolver
from ......utils import ReturnStatus 
from ......agents import AgentDriver, AgentDriverConfig
from ......utils.data_structs import create_id
from ......db_drivers.kv_driver import KeyValueDriverConfig
from ......utils.cache_kv import CacheKV, CacheUtils

class EntitiesExtractor(CacheUtils):
    def __init__(self, config: EntitiesExtractorConfig = EntitiesExtractorConfig(), 
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

        self.entities_extractor_solver = AgentTaskSolver(
            self.agent, self.config.entities_extraction_agent_task_config, agents_cache_config)
        
        self.log = self.config.log
        self.verbose = self.config.verbose

    def get_cache_key(self, query: str) -> List[object]:
        return [query, self.config.to_str()]

    @CacheUtils.cache_method_output
    def perform(self, query: str) -> Tuple[Dict[str, Union[List[str], Union[str, None]]], ReturnInfo]:
        self.log("START ENTITIES EXTRACTION...", verbose=self.config.verbose)
        info = ReturnInfo()
        self.log(f"QUERY ID: {create_id(query)}", verbose=self.config.verbose)
        self.log(f"QUERY: {query}", verbose=self.config.verbose)
        
        self.log("Выполнение извлечения сущностей из запроса с помощью LLM-агента...", verbose=self.config.verbose)
        # Result is now a dict: {'entities': [], 'time': ...}
        extraction_result, info.status = self.entities_extractor_solver.solve(lang=self.config.lang, query=query)
        self.log(f"RESULT: {extraction_result}", verbose=self.verbose)
        self.log(f"STATUS: {info.status}", verbose=self.verbose)

        # Handle empty result
        if extraction_result is None:
            extraction_result = {"entities": [], "time": None}
            info.status = ReturnStatus.empty_answer
        elif len(extraction_result.get("entities", [])) < 1:
            info.status = ReturnStatus.empty_answer

        return extraction_result, info
