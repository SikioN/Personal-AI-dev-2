from dataclasses import dataclass, field

from .utils import KVDBConnectionConfig, AbstractKVDatabaseConnection
from .configs import DEFAULT_KVDB_CONFIGS, AVAILABLE_KVDB_CONNECTORS

@dataclass
class KeyValueDriverConfig:
    db_vendor: str = 'inmemory_kv'
    db_config: KVDBConnectionConfig = field(default_factory=lambda: DEFAULT_KVDB_CONFIGS['inmemory_kv'])

class KeyValueDriver:
    @staticmethod
    def connect(config: KeyValueDriverConfig = KeyValueDriverConfig()) -> AbstractKVDatabaseConnection:
        kv_conn = AVAILABLE_KVDB_CONNECTORS[config.db_vendor](config.db_config)
        kv_conn.open_connection()
        return kv_conn