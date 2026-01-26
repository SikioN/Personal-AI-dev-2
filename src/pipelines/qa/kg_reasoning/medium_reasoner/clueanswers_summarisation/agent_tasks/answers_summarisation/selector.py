from ........utils import AgentTaskSolverConfig, Logger
from .general_parsers import casumm_custom_formate, casumm_custom_postprocess
from .v1 import CASUMM_SUITE_V1

CASUMM_LOG_PATH = "log/qa/kg_reasoner/medium/clueanswers_summarisation/agent_tasks/answers_summarisation"

AVAILABLE_CASUMM_TCONFIGS = {
    'v1': CASUMM_SUITE_V1
}

class AgentClueAnswersSummTaskConfigSelector:
    @staticmethod
    def get_available_configs():
        return AVAILABLE_CASUMM_TCONFIGS

    @staticmethod
    def select(base_config_version:str = 'v1', cache_table_name:str="medreasn_casumm_agent_task_cache") -> AgentTaskSolverConfig:
        return AgentTaskSolverConfig(
            version=base_config_version,
            suites=AVAILABLE_CASUMM_TCONFIGS[base_config_version],
            formate_context_func=casumm_custom_formate, postprocess_answer_func=casumm_custom_postprocess,
            cache_table_name=cache_table_name,
            log=Logger(CASUMM_LOG_PATH))