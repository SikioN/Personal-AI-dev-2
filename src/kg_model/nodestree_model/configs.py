from ...db_drivers.tree_driver import TreeDriverConfig
from ...db_drivers.vector_driver import VectorDriverConfig, VectorDBConnectionConfig
from .agent_tasks.nodes_summarization import AgentSummNTaskConfigSelector

DEFAULT_SUMMN_TASK_CONFIG = AgentSummNTaskConfigSelector.select(base_config_version='v1')

NODESTREE_MODEL_LOG_PATH = 'log/kg_model/nodes_tree'

SUMMNODES_VDB_DEFAULT_DRIVER_CONFIG = VectorDriverConfig(
    db_vendor='chroma', db_config=VectorDBConnectionConfig(
        conn={'path':"../data/graph_structures/vectorized_nodes/default_densedb"},
        db_info={'db': 'default_db', 'table': "vectorized_summarizednodes"}))

LEAFNODES_VDB_DEFAULT_DRIVER_CONFIG = VectorDriverConfig(
    db_vendor='chroma', db_config=VectorDBConnectionConfig(
        conn={'path':"../data/graph_structures/vectorized_nodes/default_densedb"},
        db_info={'db': 'default_db', 'table': "vectorized_leafnodes"}))

TREE_DB_DEFAULT_DRIVER_CONFIG = TreeDriverConfig()
