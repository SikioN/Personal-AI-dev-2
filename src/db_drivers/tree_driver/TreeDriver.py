from dataclasses import dataclass, field

from .utils import TreeDBConnectionConfig, AbstractTreeDatabaseConnection
from .configs import DEFAULT_TREEDB_CONFIGS, AVAILABLE_TREEDB_CONNECTORS

@dataclass
class TreeDriverConfig:
    db_vendor: str = 'neo4j'
    db_config: TreeDBConnectionConfig = field(default_factory=lambda: DEFAULT_TREEDB_CONFIGS['neo4j'])

class TreeDriver:
    @staticmethod
    def connect(config: TreeDriverConfig = TreeDriverConfig()) -> AbstractTreeDatabaseConnection:
        tree_conn = AVAILABLE_TREEDB_CONNECTORS[config.db_vendor](config.db_config)
        tree_conn.open_connection()
        return tree_conn
