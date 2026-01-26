from .agent_tasks.entities_extractor import AgentEntitiesExtrTaskConfigSelector

ENEXTR_MAIN_LOG_PATH = "log/qa/kg_reasoner/medium/entities_extractor/main"
DEFAULT_ENT_EXTR_TASK_CONFIG = AgentEntitiesExtrTaskConfigSelector.select(base_config_version='v1')