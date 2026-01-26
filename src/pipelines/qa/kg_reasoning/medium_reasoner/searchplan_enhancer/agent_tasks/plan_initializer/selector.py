from ........utils import AgentTaskSolverConfig, Logger
from .general_parsers import planinit_custom_formate, planinit_custom_postprocess
from .v1 import PLANINIT_SUITE_V1

PLANINIT_LOG_PATH = "log/qa/kg_reasoner/medium/plan_enhancer/agent_tasks/plan_initialisation"

AVAILABLE_PLANINIT_TCONFIGS = {
    'v1': PLANINIT_SUITE_V1
}

class AgentPlanInitTaskConfigSelector:
    @staticmethod
    def get_available_configs():
        return AVAILABLE_PLANINIT_TCONFIGS

    @staticmethod
    def select(base_config_version:str = 'v1', cache_table_name:str="medreasn_planinit_agent_task_cache") -> AgentTaskSolverConfig:
        return AgentTaskSolverConfig(
            version=base_config_version,
            suites=AVAILABLE_PLANINIT_TCONFIGS[base_config_version],
            formate_context_func=planinit_custom_formate, postprocess_answer_func=planinit_custom_postprocess,
            cache_table_name=cache_table_name,
            log=Logger(PLANINIT_LOG_PATH))