from ........utils import AgentTaskSolverConfig, Logger
from .general_parsers import simpleag_custom_formate, simpleag_custom_postprocess
from .v2 import SIMPLEAG_SUITE_V2
from .v1 import SIMPLEAG_SUITE_V1
from .v3 import SIMPLEAG_SUITE_V3

SIMPLEAGERATION_LOG_PATH = 'log/qa/kg_reasoner/weak/answer_generation/agent_tasks/ag'

AVAILABLE_SIMPLEAG_TCONFIGS = {
    'v1': SIMPLEAG_SUITE_V1,
    'v2': SIMPLEAG_SUITE_V2,
    'v3': SIMPLEAG_SUITE_V3
}

class AgentSimpleAGTaskConfigSelector:
    @staticmethod
    def get_available_configs():
        return AVAILABLE_SIMPLEAG_TCONFIGS

    @staticmethod
    def select(base_config_version:str = 'v1', cache_table_name:str="qa_agent_ag_task_cache") -> AgentTaskSolverConfig:
        return AgentTaskSolverConfig(
            version=base_config_version,
            suites=AVAILABLE_SIMPLEAG_TCONFIGS[base_config_version],
            formate_context_func=simpleag_custom_formate, postprocess_answer_func=simpleag_custom_postprocess,
            cache_table_name=cache_table_name,
            log=Logger(SIMPLEAGERATION_LOG_PATH))
