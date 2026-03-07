from ...db_drivers.tree_driver import TreeDriverConfig
from ...db_drivers.vector_driver import VectorDriverConfig, VectorDBConnectionConfig

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
