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

#!!!AVAILABLE GRAPH MODELS!!!#

@pytest.fixture(scope='package')
def graph_neo4j_config():
    config = GraphModelConfig(
        driver_config=GraphDriverConfig(
            db_vendor='neo4j',
            db_config=GraphDBConnectionConfig(
                host="localhost", port="7680", db_info={'db': 'testing', 'table': 'testing'},
                params={'user': "neo4j", 'pwd': 'password'}, need_to_clear=True)))
    return config

@pytest.fixture(scope='package')
def graph_inmemory_config():
    config = GraphModelConfig(
        driver_config=GraphDriverConfig(
            db_vendor='inmemory_graph',
            db_config=GraphDBConnectionConfig(
                db_info={'db': 'testing', 'table': 'testing'},
                params=dict(), need_to_clear=True)))
    return config

@pytest.fixture(scope='package')
def graph_kuzu_config():
    config = GraphModelConfig(
        driver_config=GraphDriverConfig(
            db_vendor='kuzu',
            db_config=GraphDBConnectionConfig(
                db_info={'db': 'testing', 'table': 'testing'},
                params={'path': f'{TEST_VOLUME_DIR}/kuzu', 'buffer_pool_size': 1024**3,
                    'schema': [
                        "CREATE NODE TABLE IF NOT EXISTS object (id SERIAL, name STRING, prop MAP(STRING, STRING), str_id STRING, PRIMARY KEY(id));",
                        "CREATE NODE TABLE IF NOT EXISTS hyper (id SERIAL, name STRING, prop MAP(STRING, STRING), str_id STRING, PRIMARY KEY(id));",
                        "CREATE NODE TABLE IF NOT EXISTS episodic (id SERIAL, name STRING, prop MAP(STRING, STRING), str_id STRING, PRIMARY KEY(id));",
                        "CREATE REL TABLE IF NOT EXISTS simple (FROM object TO object, name STRING, t_id STRING, str_id STRING, prop MAP(STRING, STRING));",
                        "CREATE REL TABLE IF NOT EXISTS hyper_rel (FROM object TO hyper, name STRING, t_id STRING, str_id STRING, prop MAP(STRING, STRING));",
                        "CREATE REL TABLE GROUP IF NOT EXISTS episodic_rel (FROM object TO episodic, FROM hyper TO episodic, name STRING, t_id STRING, str_id STRING, prop MAP(STRING, STRING));"
                    ],
                    'table_type_map': {
                        'relations': {'forward': {RelationType.simple.value: 'simple', RelationType.hyper.value: 'hyper_rel', RelationType.episodic.value: 'episodic_rel'},},
                        'nodes': {'forward': {NodeType.object.value: 'object', NodeType.hyper.value: 'hyper', NodeType.episodic.value: 'episodic'}}
                    }
                },
                need_to_clear=True
            )
        )
    )
    return config


#------------------------------#

@pytest.fixture(scope='package')
def available_graph_configs(
    graph_neo4j_config,
    graph_inmemory_config,
    graph_kuzu_config
):
    return {
        'neo4j': graph_neo4j_config,
        'inmemory_graph': graph_inmemory_config,
        'kuzu': graph_kuzu_config
    }

@pytest.fixture(scope='package')
def available_graph_models(available_graph_configs):
    return {graph_vendor: GraphModel(config) for graph_vendor, config in available_graph_configs.items()}

@pytest.fixture(scope='function')
def graph_model(available_graph_models, request):
    return available_graph_models[request.param]

#!!!AVAILABLE VECTOR MODELS!!!#

@pytest.fixture(scope='package')
def embeddings_chroma_config():
    config = EmbeddingsModelConfig(
        nodesdb_driver_config=VectorDriverConfig(db_vendor='chroma', db_config=VectorDBConnectionConfig(
            conn={'path': f'{TEST_VOLUME_DIR}/chroma'}, db_info={'db': 'testing', 'table': 'vectorized_nodes'}, params={"hnsw:space": "ip","hnsw:M": 4096}, need_to_clear=True)),
        tripletsdb_driver_config=VectorDriverConfig(db_vendor='chroma', db_config=VectorDBConnectionConfig(
            conn={'path': f'{TEST_VOLUME_DIR}/chroma'}, db_info={'db': 'testing', 'table': 'vectorized_triplets'}, params={"hnsw:space": "ip","hnsw:M": 4096}, need_to_clear=True)),
        embedder_config=EmbedderModelConfig(model_name_or_path=f'{PROJECT_BASE_DIR}models/intfloat/multilingual-e5-small', device='cuda'))
    return config

@pytest.fixture(scope='package')
def embeddings_milvus_config():
    config = EmbeddingsModelConfig(
        nodesdb_driver_config=VectorDriverConfig(db_vendor='milvus', db_config=VectorDBConnectionConfig(
            conn={'host': 'localhost', 'port': 19520, 'user': 'root', 'pass': 'Milvus'}, db_info={'db': 'testing', 'table': 'vectorized_nodes'}, need_to_clear=True,
            params={'id_length': 32, 'vector_dim': 384, 'document_max_length': 51200, 'load': True, 'flush': True, 'create_sleep': 1, 'search_metric': 'IP'})),
        tripletsdb_driver_config=VectorDriverConfig(db_vendor='milvus', db_config=VectorDBConnectionConfig(
            conn={'host': 'localhost', 'port': 19520, 'user': 'root', 'pass': 'Milvus'}, db_info={'db': 'testing', 'table': 'vectorized_triplets'}, need_to_clear=True,
            params={'id_length': 32, 'vector_dim': 384, 'document_max_length': 51200, 'load': True, 'flush': True, 'create_sleep': 1, 'search_metric': 'IP'})),
        embedder_config=EmbedderModelConfig(model_name_or_path=f'{PROJECT_BASE_DIR}models/intfloat/multilingual-e5-small', device='cuda'))
    return config

#------------------------------#

@pytest.fixture(scope='package')
def available_embedding_configs(
    embeddings_chroma_config, embeddings_milvus_config
):
    return {
        'chroma': embeddings_chroma_config,
        'milvus': embeddings_milvus_config
    }

@pytest.fixture(scope='package')
def available_embedding_models(available_embedding_configs):
    return {embedding_vendor: EmbeddingsModel(config) for embedding_vendor, config in available_embedding_configs.items()}

@pytest.fixture(scope='function')
def embeddings_model(available_embedding_models, request):
    return available_embedding_models[request.param]

#------------------------------#

@pytest.fixture(scope='package')
def available_kg_models(available_embedding_configs, available_graph_configs):
    kg_configs = {}
    for vector_name, vector_config in available_embedding_configs.items():
        for graph_name, graph_config in available_graph_configs.items():
            cur_config = KnowledgeGraphModelConfig(graph_config=graph_config, embeddings_config=vector_config, nodestree_config=None)
            kg_configs[f"{vector_name}/{graph_name}"] = KnowledgeGraphModel(cur_config)
    return kg_configs

@pytest.fixture(scope='function')
def kg_model(available_kg_models, request):
    return available_kg_models[request.param]
