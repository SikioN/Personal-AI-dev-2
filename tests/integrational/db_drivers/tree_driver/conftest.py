import pytest

import sys
# TO CHANGE
PROJECT_BASE_DIR = '../'
sys.path.insert(0, PROJECT_BASE_DIR)

from src.db_drivers.tree_driver import TreeDriver, TreeDriverConfig, TreeDBConnectionConfig

#!!!AVAILABLE TREE CONNECTIONS!!!#

@pytest.fixture(scope='package')
def neo4j_conn():
    config = TreeDriverConfig(db_vendor='neo4j', db_config=TreeDBConnectionConfig(
        host="localhost", port="7680", db_info={'db': 'testingtree', 'table': 'testingtree'},
        params={'user': "neo4j", 'pwd': 'password'}, need_to_clear=True))
    return TreeDriver.connect(config)

#------------------------------#

@pytest.fixture(scope='package')
def available_tree_connections(
    neo4j_conn
):
    return {
        'neo4j': neo4j_conn
    }

@pytest.fixture(scope='function')
def treedb_conn(available_tree_connections, request):
    return available_tree_connections[request.param]
