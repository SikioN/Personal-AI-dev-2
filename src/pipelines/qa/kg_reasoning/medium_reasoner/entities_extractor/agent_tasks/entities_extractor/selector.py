from ........utils import AgentTaskSolverConfig, Logger
from .general_parsers import entextr_custom_formate, entextr_custom_postprocess
from .v1 import ENTEXTR_SUITE_V1

SUBA_SUMM_LOG_PATH = "log/qa/kg_reasoner/medium/entities_extractor/agent_tasks/entities_extraction"

AVAILABLE_ENTEXTR_TCONFIGS = {
    'v1': ENTEXTR_SUITE_V1
}

class AgentEntitiesExtrTaskConfigSelector:
    @staticmethod
    def get_available_configs():
        return AVAILABLE_ENTEXTR_TCONFIGS

    @staticmethod
    def select(base_config_version:str = 'v1', cache_table_name:str="medreasn_entextr_agent_task_cache") -> AgentTaskSolverConfig:
        return AgentTaskSolverConfig(
            version=base_config_version,
            suites=AVAILABLE_ENTEXTR_TCONFIGS[base_config_version],
            formate_context_func=entextr_custom_formate, postprocess_answer_func=entextr_custom_postprocess,
            cache_table_name=cache_table_name,
            log=Logger(SUBA_SUMM_LOG_PATH))