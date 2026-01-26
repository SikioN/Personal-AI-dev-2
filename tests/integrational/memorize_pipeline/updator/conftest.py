import pytest

import sys
# TO CHANGE
PROJECT_BASE_DIR = '../'
sys.path.insert(0, PROJECT_BASE_DIR)

from src.pipelines.memorize.updator import LLMUpdator, LLMUpdatorConfig
from src.agents import AgentDriverConfig
from src.agents.configs import DEFAULT_STUBAGENT_CONFIG

from src.kg_model import KnowledgeGraphModel, GraphModelConfig, EmbeddingsModelConfig
from src.db_drivers.graph_driver import GraphDriverConfig, DEFAULT_INMEMORYGRAPH_CONFIG
from src.db_drivers.vector_driver import VectorDriverConfig, VectorDBConnectionConfig, EmbedderModelConfig

@pytest.fixture(scope='package')
def kg_model():
    graph_driver_config = GraphDriverConfig(
        db_vendor='inmemory_graph',
        db_config=DEFAULT_INMEMORYGRAPH_CONFIG)

    nodes_driver_config = VectorDriverConfig(
        db_vendor='chroma',
        db_config=VectorDBConnectionConfig(
            path='./volumes/chroma', db_info={'db': 'test_db', 'table': "v_nodes"}))

    triplets_driver_config = VectorDriverConfig(
        db_vendor='chroma',
        db_config=VectorDBConnectionConfig(
            path='./volumes/chroma', db_info={'db': 'test_db', 'table': "v_triplets"}))

    embedder_config = EmbedderModelConfig()

    return KnowledgeGraphModel(
        graph_config=GraphModelConfig(driver_config=graph_driver_config),
        embeddings_config=EmbeddingsModelConfig(
            nodesdb_driver_config=nodes_driver_config,
            tripletsdb_driver_config=triplets_driver_config,
            embedder_config=embedder_config)
    )

@pytest.fixture(scope='function')
def llm_updator(kg_model):
    updator_config = LLMUpdatorConfig(
        lang='en',
        agent_config=AgentDriverConfig(name='stub', agent_config=DEFAULT_STUBAGENT_CONFIG)
    )
    return LLMUpdator(kg_model, updator_config)
