from .....utils import AgentTaskSolverConfig, Logger
from .general_parsers import summn_custom_formate, summn_custom_postprocess
from .v1 import SUMMN_SUITE_V1

SUMM_NODES_LOG_PATH = 'log/kg_model/nodes_tree/agent_tasks/summ_nodes'

AVAILABLE_SUMMN_TCONFIGS = {
    'v1': SUMMN_SUITE_V1,
}

class AgentSummNTaskConfigSelector:
    @staticmethod
    def get_available_configs():
        return AVAILABLE_SUMMN_TCONFIGS

    @staticmethod
    def select(base_config_version:str='v1', cache_table_name:str="qa_agent_summn_task_cache") -> AgentTaskSolverConfig:
        return AgentTaskSolverConfig(
            version=base_config_version,
            suites=AVAILABLE_SUMMN_TCONFIGS[base_config_version],
            formate_context_func=summn_custom_formate, postprocess_answer_func=summn_custom_postprocess,
            cache_table_name=cache_table_name,
            log=Logger(SUMM_NODES_LOG_PATH))
