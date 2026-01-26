from .agent_tasks.query_decomposition import AgentQueryDecompTaskConfigSelector
from .agent_tasks.decomposition_classifier import AgentDecompClsTaskConfigSelector

QD_MAIN_LOG_PATH = "log/qa/query_preprocessing/decomposition/main"

DEFAULT_QD_TASK_CONFIG = AgentQueryDecompTaskConfigSelector.select(base_config_version='v1')
DEFAULT_DC_TASK_CONFIG = AgentDecompClsTaskConfigSelector.select(base_config_version='v1')