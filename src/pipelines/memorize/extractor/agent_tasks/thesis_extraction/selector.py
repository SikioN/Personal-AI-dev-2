from ......utils import AgentTaskSolverConfig, Logger
from ......db_drivers.kv_driver import KeyValueDriverConfig
from .general_parsers import equadruplets_thesis_custom_formate, equadruplets_thesis_custom_postprocess
from .v1 import THESIS_EXTRACT_SUITE_V1
from .v2 import THESIS_EXTRACT_SUITE_V2

THESIS_EXTR_LOG_PATH = 'log/memorize/extractor/agent_tasks/thesis_extraction'

AVAILABLE_THESIS_EXTRACT_TCONFIGS = {
    'v1': THESIS_EXTRACT_SUITE_V1,
    'v2': THESIS_EXTRACT_SUITE_V2
}

class AgentThesisExtrTaskConfigSelector:
    @staticmethod
    def get_available_configs():
        return AVAILABLE_THESIS_EXTRACT_TCONFIGS

    @staticmethod
    def select(base_config_version: str = 'v1', cache_table_name: str = "mem_agent_thesisextr_task_cache") -> AgentTaskSolverConfig:
        return AgentTaskSolverConfig(
            version=base_config_version,
            suites=AVAILABLE_THESIS_EXTRACT_TCONFIGS[base_config_version],
            formate_context_func=equadruplets_thesis_custom_formate, postprocess_answer_func=equadruplets_thesis_custom_postprocess,
            cache_table_name=cache_table_name,
            log=Logger(THESIS_EXTR_LOG_PATH))
