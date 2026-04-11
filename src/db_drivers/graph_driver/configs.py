from .connectors.Neo4jConnector import Neo4jConnector, DEFAULT_NEO4J_CONFIG
from .connectors.InMemoryGraphConnector import InMemoryGraphConnector, DEFAULT_INMEMORYGRAPH_CONFIG
from .connectors.KuzuConnector import KuzuConnector, DEFAULT_KUZU_CONFIG

DEFAULT_GRAPHDB_CONFIGS = {
    'neo4j': DEFAULT_NEO4J_CONFIG,
    'inmemory_graph': DEFAULT_INMEMORYGRAPH_CONFIG,
    'kuzu': DEFAULT_KUZU_CONFIG
}

AVAILABLE_GRAPHDB_CONNECTORS = {
    'neo4j': Neo4jConnector,
    'inmemory_graph': InMemoryGraphConnector,
    'kuzu': KuzuConnector
}
