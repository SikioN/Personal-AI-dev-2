from ......utils import AgentTaskSolverConfig, Logger
from ......db_drivers.kv_driver import KeyValueDriverConfig
from .general_parsers import rt_custom_formate, rt_custom_postprocess
from .v1 import REPLACE_THESIS_SUITE_V1

REPLACE_THESIS_LOG_PATH = 'log/memorize/updator/agent_tasks/replace_thesis_triplets'

AVAILABLE_REPLACE_THESIS_TCONFIGS = {
    'v1': REPLACE_THESIS_SUITE_V1
}

class AgentReplThesisTripletTaskConfigSelector:
    @staticmethod
    def get_available_configs():
        return AVAILABLE_REPLACE_THESIS_TCONFIGS

    @staticmethod
    def select(base_config_version: str = 'v1', cache_table_name: str = "mem_agent_replthesis_task_cache") -> AgentTaskSolverConfig:
        return AgentTaskSolverConfig(
            version=base_config_version,
            suites=AVAILABLE_REPLACE_THESIS_TCONFIGS[base_config_version],
            formate_context_func=rt_custom_formate, postprocess_answer_func=rt_custom_postprocess,
            cache_table_name=cache_table_name,
            log=Logger(REPLACE_THESIS_LOG_PATH))
