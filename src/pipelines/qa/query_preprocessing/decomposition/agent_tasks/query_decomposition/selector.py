from .......utils import AgentTaskSolverConfig, Logger
from .general_parsers import qd_custom_formate, qd_custom_postprocess
from .v1 import QD_SUITE_V1

QD_LOG_PATH = "log/qa/query_preprocessing/decomposition/agent_tasks/query_decompsition"

AVAILABLE_QD_TCONFIGS = {
    'v1': QD_SUITE_V1
}

class AgentQueryDecompTaskConfigSelector:
    @staticmethod
    def get_available_configs():
        return AVAILABLE_QD_TCONFIGS

    @staticmethod
    def select(base_config_version:str = 'v1', cache_table_name:str="qp_qdecomp_agent_task_cache") -> AgentTaskSolverConfig:
        return AgentTaskSolverConfig(
            version=base_config_version,
            suites=AVAILABLE_QD_TCONFIGS[base_config_version],
            formate_context_func=qd_custom_formate, postprocess_answer_func=qd_custom_postprocess,
            cache_table_name=cache_table_name,
            log=Logger(QD_LOG_PATH))