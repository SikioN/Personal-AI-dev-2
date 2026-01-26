from .connectors.Neo4jConnector import Neo4jTreeConnector, DEFAULT_NEO4JTREE_CONFIG

DEFAULT_TREEDB_CONFIGS = {
    'neo4j': DEFAULT_NEO4JTREE_CONFIG
}

AVAILABLE_TREEDB_CONNECTORS = {
    'neo4j': Neo4jTreeConnector
}
