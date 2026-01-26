from .agent_tasks.clueanswer_generation import AgentClueAnswerGenTaskConfigSelector

CAGEN_MAIN_LOG_PATH = "log/qa/kg_reasoner/medium/clueansw_generation/main" 
DEFAULT_CAGEN_TASK_CONFIG = AgentClueAnswerGenTaskConfigSelector.select(base_config_version='v1')