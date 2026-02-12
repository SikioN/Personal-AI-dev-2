from dataclasses import dataclass, field
from typing import Tuple, Union, List
from copy import deepcopy
import hashlib

from .config import CAGEN_MAIN_LOG_PATH, DEFAULT_CAGEN_TASK_CONFIG
from ......utils.errors import STATUS_MESSAGE
from ......utils import ReturnInfo, Logger, AgentTaskSolverConfig, AgentTaskSolver
from ......agents import AgentDriver, AgentDriverConfig
from ......utils.data_structs import create_id, Quadruplet, QuadrupletCreator
from ......db_drivers.kv_driver import KeyValueDriverConfig
from ......utils.cache_kv import CacheKV, CacheUtils
from ......utils import ReturnStatus 

@dataclass
class ClueAnswerGeneratorConfig:
    lang: str = 'auto'
    adriver_config: AgentDriverConfig = field(default_factory=lambda: AgentDriverConfig())
    cagen_agent_task_config: AgentTaskSolverConfig = field(default_factory=lambda: DEFAULT_CAGEN_TASK_CONFIG)

    cache_table_name: str = "medreasn_cagen_main_stage_cache"
    log: Logger = field(default_factory=lambda: Logger(CAGEN_MAIN_LOG_PATH))
    verbose: bool = False

    def to_str(self):
        return f"{self.lang}|{self.adriver_config.to_str()}|{self.cagen_agent_task_config.version}"

class ClueAnswerGenerator(CacheUtils):
    def __init__(self, config: ClueAnswerGeneratorConfig = ClueAnswerGeneratorConfig(), 
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

        self.cagen_solver = AgentTaskSolver(
            self.agent, self.config.cagen_agent_task_config, agents_cache_config)
        
        self.log = self.config.log
        self.verbose = self.config.verbose

    def get_cache_key(self, query: str, context_quadruplets: List[Quadruplet]) -> List[object]:
        str_quadruplets = hashlib.sha1("\n".join(sorted([QuadrupletCreator.stringify(quadruplet)[1] for quadruplet in context_quadruplets])).encode()).hexdigest()
        return [self.config.to_str(), query, str_quadruplets]

    @CacheUtils.cache_method_output
    def perform(self, query: str, context_quadruplets: List[Quadruplet]) -> Tuple[List[str], ReturnInfo]:
        """
        :param query: Вопрос к системе, для которого необходимо сгенерировать ответ.
        :type query: str
        :param context_quadruplets: Набор квадруплетов в качестве контекста.
        :type context_quadruplets: List[Quadruplet]
        """
        info = ReturnInfo()
        self.log("START CLUE-ANSWER GENRATION ...", verbose=self.config.verbose)
        self.log(f"BASE_QUESTION ID: {create_id(query)}", verbose=self.config.verbose)
        self.log(f"BASE_QUESTION: {query}", verbose=self.config.verbose)
        self.log(f"CONTEXT_QUADRUPLETS:",verbose=self.config.verbose)
        for quadruplet in context_quadruplets:
            self.log(f"*[{quadruplet.id}] {quadruplet}", verbose=self.config.verbose)

        self.log("Выполнение условной генерации ответа на вопрос с помощью LLM-агента...", verbose=self.config.verbose)
        answer, status = self.cagen_solver.solve(
            lang=self.config.lang, query=query, 
            triplets=context_triplets)

        if status != ReturnStatus.success:
            info.occurred_warning.append(status)

        if answer is None or len(answer) == 0:
            info.status = ReturnStatus.empty_answer
            info.message = STATUS_MESSAGE[info.status]

        self.log(f"RESULT:\n* GENERATED ANSWER - {answer}", verbose=self.config.verbose)
        self.log(f"STATUS: {info.status}", verbose=self.config.verbose)

        return answer, info
