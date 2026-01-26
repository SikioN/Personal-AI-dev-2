from .......utils import AgentTaskSolverConfig, Logger
from .general_parsers import dc_custom_formate, dc_custom_postprocess
from .v1 import DC_SUITE_V1

DC_LOG_PATH = "log/qa/query_preprocessing/decomposition/agent_tasks/decompose_classification"

AVAILABLE_DC_TCONFIGS = {
    'v1': DC_SUITE_V1
}

class AgentDecompClsTaskConfigSelector:
    @staticmethod
    def get_available_configs():
        return AVAILABLE_DC_TCONFIGS

    @staticmethod
    def select(base_config_version:str = 'v1', cache_table_name:str="qp_decompcls_agent_task_cache") -> AgentTaskSolverConfig:
        return AgentTaskSolverConfig(
            version=base_config_version,
            suites=AVAILABLE_DC_TCONFIGS[base_config_version],
            formate_context_func=dc_custom_formate, postprocess_answer_func=dc_custom_postprocess,
            cache_table_name=cache_table_name,
            log=Logger(DC_LOG_PATH))