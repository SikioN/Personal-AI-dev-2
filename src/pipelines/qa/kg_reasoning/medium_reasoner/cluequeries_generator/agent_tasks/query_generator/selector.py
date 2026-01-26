from ........utils import AgentTaskSolverConfig, Logger
from .general_parsers import cqgen_custom_formate, cqgen_custom_postprocess
from .v1 import CQGEN_SUITE_V1

CQGEN_LOG_PATH = "log/qa/kg_reasoner/medium/cluequeries_generator/agent_tasks/cquery_generator"

AVAILABLE_CQGEN_TCONFIGS = {
    'v1': CQGEN_SUITE_V1
}

class AgentCQueryGenTaskConfigSelector:
    @staticmethod
    def get_available_configs():
        return AVAILABLE_CQGEN_TCONFIGS

    @staticmethod
    def select(base_config_version:str = 'v1', cache_table_name:str="medreasn_cqgen_agent_task_cache") -> AgentTaskSolverConfig:
        return AgentTaskSolverConfig(
            version=base_config_version,
            suites=AVAILABLE_CQGEN_TCONFIGS[base_config_version],
            formate_context_func=cqgen_custom_formate, postprocess_answer_func=cqgen_custom_postprocess,
            cache_table_name=cache_table_name,
            log=Logger(CQGEN_LOG_PATH))