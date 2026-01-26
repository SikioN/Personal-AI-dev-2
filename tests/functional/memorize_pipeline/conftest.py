import pytest

import sys
# TO CHANGE
PROJECT_BASE_DIR = '../'
TEST_VOLUME_DIR = './volumes'
sys.path.insert(0, PROJECT_BASE_DIR)

from src.kg_model import EmbeddingsModel, EmbeddingsModelConfig, GraphModel, GraphModelConfig, KnowledgeGraphModel, KnowledgeGraphModelConfig
from src.db_drivers.vector_driver import VectorDBConnectionConfig, VectorDriverConfig
from src.db_drivers.vector_driver.embedders import EmbedderModelConfig
from src.db_drivers.graph_driver import GraphDriverConfig, GraphDBConnectionConfig
from src.utils.data_structs import NodeType, RelationType


@pytest.fixture(scope='package')
def graph_neo4j_config():
    config = GraphModelConfig(
        driver_config=GraphDriverConfig(
            db_vendor='neo4j',
            db_config=GraphDBConnectionConfig(
                host="localhost", port="7688", db_info={'db': 'testing', 'table': 'testing'},
                params={'user': "neo4j", 'pwd': 'password'}, need_to_clear=True)))
    return config

@pytest.fixture(scope='package')
def embeddings_chroma_config():
    config = EmbeddingsModelConfig(
        nodesdb_driver_config=VectorDriverConfig(db_config=VectorDBConnectionConfig(
            path=f'{TEST_VOLUME_DIR}/chroma', db_info={'db': 'testing', 'table': 'vectorized_nodes'}, need_to_clear=True)),
        tripletsdb_driver_config=VectorDriverConfig(db_config=VectorDBConnectionConfig(
            path=f'{TEST_VOLUME_DIR}/chroma', db_info={'db': 'testing', 'table': 'vectorized_triplets'}, need_to_clear=True)),
        embedder_config=EmbedderModelConfig(model_name_or_path=f'{PROJECT_BASE_DIR}/models/intfloat/multilingual-e5-small', device='cuda'))
    return config

#------------------------------#

@pytest.fixture(scope='function')
def kg_model(graph_neo4j_config, embeddings_chroma_config):
    config = KnowledgeGraphModelConfig(graph_config=graph_neo4j_config, embeddings_config=embeddings_chroma_config)
    return KnowledgeGraphModel(config)
