import pytest
from tqdm import tqdm
from cases import RAW_TEXTS_EN

import sys
# TO CHANGE
PROJECT_BASE_DIR = '../'
TEST_VOLUME_DIR = './volumes'
sys.path.insert(0, PROJECT_BASE_DIR)

from src.kg_model.graph_model import GraphModelConfig
from src.kg_model.embeddings_model import EmbeddingsModelConfig
from src.db_drivers.vector_driver import VectorDBConnectionConfig, VectorDriverConfig
from src.db_drivers.vector_driver.embedders import EmbedderModelConfig
from src.db_drivers.graph_driver import GraphDriverConfig, GraphDBConnectionConfig
from src.agents.AgentDriver import AgentDriverConfig, AgentConnectorConfig
from src.pipelines.memorize import MemPipelineConfig
from src.kg_model import KnowledgeGraphModel, KnowledgeGraphModelConfig
from src.agents.AgentDriver import AgentDriverConfig, AgentConnectorConfig
from src.pipelines.memorize import MemPipeline, MemPipelineConfig, LLMExtractorConfig, LLMUpdatorConfig
from src.pipelines.memorize.extractor.agent_tasks.thesis_extraction import AgentThesisExtrTaskConfigSelector
from src.pipelines.memorize.extractor.agent_tasks.triplet_extraction import AgentTripletExtrTaskConfigSelector

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

@pytest.fixture(scope='package')
def mem_pipeline_config():
    agent_driver_config = AgentDriverConfig(
        name='ollama',
        agent_config=AgentConnectorConfig(
            gen_strategy={"num_predict": 2048, "seed": 42, "top_k": 1, "temperature": 0.0},
            credentials={"model": 'qwen2.5:7b'},
            ext_params={"host": 'localhost', "port": 11438, "timeout": 560, "keep_alive": -1}))
    
    config = MemPipelineConfig(
        extractor_config=LLMExtractorConfig(
            lang='en', adriver_config=agent_driver_config,
            triplets_extraction_task_config=AgentTripletExtrTaskConfigSelector.select(
                base_config_version='v2'),
            thesises_extraction_task_config=AgentThesisExtrTaskConfigSelector.select(
                base_config_version='v2')),
        updator_config=LLMUpdatorConfig(
            lang='en', adriver_config=agent_driver_config,
            delete_obsolete_info=False))

    return config

#------------------------------#

@pytest.fixture(scope='package')
def kg_model(graph_neo4j_config, embeddings_milvus_config):
    graph_neo4j_config.driver_config.db_config.need_to_clear = False
    embeddings_milvus_config.nodesdb_driver_config.db_config.need_to_clear = False
    embeddings_milvus_config.tripletsdb_driver_config.db_config.need_to_clear = False

    kg_config = KnowledgeGraphModelConfig(graph_config=graph_neo4j_config, embeddings_config=embeddings_milvus_config)
    kg_model = KnowledgeGraphModel(kg_config)
    #kg_model.clear()
    return kg_model

@pytest.fixture(scope='package')
def mem_pipeline(request, kg_model, mem_pipeline_config):
    mem_pipeline = MemPipeline(kg_model, mem_pipeline_config)
    #for text in tqdm(RAW_TEXTS_EN):
    #    _, status = mem_pipeline.remember(text)

    def teardown():
        print("Safely closing kg-model connection...")
        mem_pipeline.updator.kg_model.graph_struct.db_conn.close_connection()
        mem_pipeline.updator.kg_model.embeddings_struct.vectordbs['nodes'].close_connection()
        mem_pipeline.updator.kg_model.embeddings_struct.vectordbs['triplets'].close_connection()
    request.addfinalizer(teardown)

    return mem_pipeline
