from ......utils import AgentTaskSolverConfig, Logger
from ......db_drivers.kv_driver import KeyValueDriverConfig
from .general_parsers import rs_custom_formate, rs_custom_postprocess
from .v1 import REPLACE_SIMPLE_SUITE_V1

REPLACE_SIMPLE_LOG_PATH = 'log/memorize/updator/agent_tasks/replace_simple_triplets'

AVAILABLE_REPLACE_SIMPLE_TCONFIGS = {
    'v1': REPLACE_SIMPLE_SUITE_V1
}

class AgentReplSimpleTripletTaskConfigSelector:
    @staticmethod
    def get_available_configs():
        return AVAILABLE_REPLACE_SIMPLE_TCONFIGS

    @staticmethod
    def select(base_config_version: str = 'v1', cache_table_name: str = "mem_agent_replsimple_task_cache") -> AgentTaskSolverConfig:
        return AgentTaskSolverConfig(
            version=base_config_version,
            suites=AVAILABLE_REPLACE_SIMPLE_TCONFIGS[base_config_version],
            formate_context_func=rs_custom_formate, postprocess_answer_func=rs_custom_postprocess,
            cache_table_name=cache_table_name,
            log=Logger(REPLACE_SIMPLE_LOG_PATH))
