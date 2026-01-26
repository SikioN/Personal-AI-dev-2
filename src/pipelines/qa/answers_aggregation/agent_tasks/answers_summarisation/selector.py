from ......utils import AgentTaskSolverConfig, Logger
from .general_parsers import subasumm_custom_formate, subasumm_custom_postprocess
from .v1 import SUBASUMM_SUITE_V1

SUBASUMM_LOG_PATH = "log/qa/answers_aggregation/agent_tasks/answers_summarisation"

AVAILABLE_SUBASUMM_TCONFIGS = {
    'v1': SUBASUMM_SUITE_V1
}

class AgentSubASummTaskConfigSelector:
    @staticmethod
    def get_available_configs():
        return AVAILABLE_SUBASUMM_TCONFIGS

    @staticmethod
    def select(base_config_version:str = 'v1', cache_table_name:str="aagg_subasumm_agent_task_cache") -> AgentTaskSolverConfig:
        return AgentTaskSolverConfig(
            version=base_config_version,
            suites=AVAILABLE_SUBASUMM_TCONFIGS[base_config_version],
            formate_context_func=subasumm_custom_formate, postprocess_answer_func=subasumm_custom_postprocess,
            cache_table_name=cache_table_name,
            log=Logger(SUBASUMM_LOG_PATH))