from ........utils import AgentTaskSolverConfig, Logger
from .general_parsers import answcls_custom_formate, answcls_custom_postprocess
from .v1 import ANSWCLS_SUITE_V1

ANSWCLS_LOG_PATH = "log/qa/kg_reasoner/medium/answer_generation//agent_tasks/answer_classifier"

AVAILABLE_ANSWCLS_TCONFIGS = {
    'v1': ANSWCLS_SUITE_V1
}

class AgentAnswerClassifierTaskConfigSelector:
    @staticmethod
    def get_available_configs():
        return AVAILABLE_ANSWCLS_TCONFIGS

    @staticmethod
    def select(base_config_version:str = 'v1', cache_table_name:str="medreasn_answcls_agent_task_cache") -> AgentTaskSolverConfig:
        return AgentTaskSolverConfig(
            version=base_config_version,
            suites=AVAILABLE_ANSWCLS_TCONFIGS[base_config_version],
            formate_context_func=answcls_custom_formate, postprocess_answer_func=answcls_custom_postprocess,
            cache_table_name=cache_table_name,
            log=Logger(ANSWCLS_LOG_PATH))