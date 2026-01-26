from .agent_tasks.kw_extraction import AgentKWETaskConfigSelector

QP_MAIN_LOG_PATH = 'log/qa/kg_reasoner/weak/query_parser/main'
DEFAULT_KWE_TASK_CONFIG =  AgentKWETaskConfigSelector.select(base_config_version='v2')
