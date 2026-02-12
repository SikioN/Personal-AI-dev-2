from ......utils import AgentTaskSolverConfig, Logger
from ......db_drivers.kv_driver import KeyValueDriverConfig
from .general_parsers import equadruplets_custom_postprocess, equadruplets_custom_formate
from .v2 import TRIPLET_EXTRACT_SUITE_V2
from .v1 import TRIPLET_EXTRACT_SUITE_V1

TRIPLET_EXTR_LOG_PATH = 'log/memorize/extractor/agent_tasks/triplet_extraction'

AVAILABLE_TRIPLET_EXTRACT_TCONFIGS = {
    'v1': TRIPLET_EXTRACT_SUITE_V1,
    'v2': TRIPLET_EXTRACT_SUITE_V2
}

class AgentTripletExtrTaskConfigSelector:
    @staticmethod
    def get_available_configs():
        return AVAILABLE_TRIPLET_EXTRACT_TCONFIGS

    @staticmethod
    def select(base_config_version: str = 'v1', cache_table_name: str = "mem_agent_tripletextr_task_cache") -> AgentTaskSolverConfig:
        return AgentTaskSolverConfig(
            version=base_config_version,
            suites=AVAILABLE_TRIPLET_EXTRACT_TCONFIGS[base_config_version],
            formate_context_func=equadruplets_custom_formate, postprocess_answer_func=equadruplets_custom_postprocess,
            cache_table_name=cache_table_name,
            log=Logger(TRIPLET_EXTR_LOG_PATH))
