from ........utils import AgentTaskSolverConfig, Logger
from .general_parsers import enhcls_custom_formate, enhcls_custom_postprocess
from .v1 import ENHCLS_SUITE_V1

ENHCLS_LOG_PATH = "log/qa/kg_reasoner/medium/plan_enhancer/agent_tasks/enhance_classifier"

AVAILABLE_ENHCLS_TCONFIGS = {
    'v1': ENHCLS_SUITE_V1
}

class AgentEnhanceClassifierTaskConfigSelector:
    @staticmethod
    def get_available_configs():
        return AVAILABLE_ENHCLS_TCONFIGS

    @staticmethod
    def select(base_config_version:str = 'v1', cache_table_name:str="medreasn_enhcls_agent_task_cache") -> AgentTaskSolverConfig:
        return AgentTaskSolverConfig(
            version=base_config_version,
            suites=AVAILABLE_ENHCLS_TCONFIGS[base_config_version],
            formate_context_func=enhcls_custom_formate, postprocess_answer_func=enhcls_custom_postprocess,
            cache_table_name=cache_table_name,
            log=Logger(ENHCLS_LOG_PATH))