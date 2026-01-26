import sys
import joblib
import yaml

# Read YAML file
PARAMS_FILE_PATH = sys.orig_argv[2]
with open(PARAMS_FILE_PATH, 'r') as stream:
    PARAMS = yaml.safe_load(stream)

sys.path.insert(0, PARAMS['WORKSPACE_CONTAINER_DIRS']['base_path'])

from src.kg_model import EmbedderModelConfig
from src.db_drivers.graph_driver import GraphDBConnectionConfig
from src.db_drivers.vector_driver import VectorDBConnectionConfig
from src.pipelines.memorize import MemPipelineConfig, LLMExtractorConfig, LLMUpdatorConfig
from src.kg_model import EmbeddingsModelConfig, GraphModelConfig
from src.db_drivers.graph_driver import GraphDriverConfig, GraphDBConnectionConfig
from src.db_drivers.vector_driver import VectorDriverConfig, VectorDBConnectionConfig, EmbedderModelConfig
from src.db_drivers.kv_driver import KeyValueDriverConfig, KVDBConnectionConfig
from src.db_drivers.tree_driver import TreeDriverConfig, TreeDBConnectionConfig

from src.kg_model.nodestree_model import NodesTreeModelConfig
from src.kg_model.nodestree_model.agent_tasks.nodes_summarization import AgentSummNTaskConfigSelector

from src.pipelines.memorize.extractor.configs import AgentThesisExtrTaskConfigSelector, AgentTripletExtrTaskConfigSelector
from src.pipelines.memorize.updator.configs import AgentReplSimpleTripletTaskConfigSelector, AgentReplThesisTripletTaskConfigSelector
from src.agents import AgentDriverConfig
from src.agents.utils import AgentConnectorConfig

###################################

DATASET_KGS_PATH = f"{PARAMS['WORKSPACE_CONTAINER_DIRS']['base_path']}/{PARAMS['WORKSPACE_CONTAINER_DIRS']['kg']}/{PARAMS['DATASET_NAME']}"
SPEC_KG_PATH = f"{DATASET_KGS_PATH}/{PARAMS['KNOWLEDGE_GRAPH_NAME']}"

GRAPH_MODEL_CONFIG_PATH = f"{SPEC_KG_PATH}/{PARAMS['SAVE_CONFIGS_NAMES']['graph_config']}"
EMBEDDINGS_MODEL_CONFIG_PATH = f"{SPEC_KG_PATH}/{PARAMS['SAVE_CONFIGS_NAMES']['embeddings_config']}"
NODESTREE_MODEL_CONFIG_PATH = f"{SPEC_KG_PATH}/{PARAMS['SAVE_CONFIGS_NAMES']['nodestree_config']}"

MEM_PIPELINE_CONFIG_PATH = f"{SPEC_KG_PATH}/{PARAMS['SAVE_CONFIGS_NAMES']['mem_pipeline_config']}"
CACHE_CONFIG_PATH = f"{SPEC_KG_PATH}/{PARAMS['SAVE_CONFIGS_NAMES']['kvdriver_cache_config']}"


########### Graph model ###########

graphdb_config = GraphDBConnectionConfig(
    host=PARAMS['KG_DB_CONFIGS']['graphdb_config']['host'],
    port=PARAMS['KG_DB_CONFIGS']['graphdb_config']['port'],
    db_info=PARAMS['KG_DB_CONFIGS']['graphdb_config']['db_info'],
    params=PARAMS['KG_DB_CONFIGS']['graphdb_config']['params'],
    need_to_clear=PARAMS['KG_DB_CONFIGS']['need_to_clear'])

gmodel_config = GraphModelConfig(
    driver_config=GraphDriverConfig(
        db_vendor=PARAMS['KG_DB_CONFIGS']['graphdb_config']['vendor'],
        db_config=graphdb_config))

########### Embeddings model ###########

nodesdb_config=VectorDBConnectionConfig(
    db_info=PARAMS['KG_DB_CONFIGS']['nodesdb_config']['db_info'],
    params=PARAMS['KG_DB_CONFIGS']['nodesdb_config']['params'],
    conn=PARAMS['KG_DB_CONFIGS']['nodesdb_config']['conn'],
    need_to_clear=PARAMS['KG_DB_CONFIGS']['need_to_clear'])

tripletsdb_config=VectorDBConnectionConfig(
    db_info=PARAMS['KG_DB_CONFIGS']['tripletsdb_config']['db_info'],
    params=PARAMS['KG_DB_CONFIGS']['tripletsdb_config']['params'],
    conn=PARAMS['KG_DB_CONFIGS']['tripletsdb_config']['conn'],
    need_to_clear=PARAMS['KG_DB_CONFIGS']['need_to_clear'])

embedder_config=EmbedderModelConfig(
    model_name_or_path=f"{PARAMS['WORKSPACE_CONTAINER_DIRS']['base_path']}/{PARAMS['WORKSPACE_CONTAINER_DIRS']['models']}/{PARAMS['KG_DB_CONFIGS']['embedder_config']['model_name_or_path']}",
    prompts=PARAMS['KG_DB_CONFIGS']['embedder_config']['prompts'])

emodel_config = EmbeddingsModelConfig(
    nodesdb_driver_config=VectorDriverConfig(
        db_vendor=PARAMS['KG_DB_CONFIGS']['nodesdb_config']['vendor'],
        db_config=nodesdb_config),
    tripletsdb_driver_config=VectorDriverConfig(
        db_vendor=PARAMS['KG_DB_CONFIGS']['tripletsdb_config']['vendor'],
        db_config=tripletsdb_config),
    embedder_config=embedder_config)

########### Memorize-pipeline config ###########

# gigachat key
#GIGACHAT_CREDS = 'OWUwOGUzOWEtMjJiNi00YmMxLThmMmItNzMwNjM2MTI2YmYxOjg2ODdiOTVhLTZkNDctNGFjOC1iMmViLTEyNDA5MmFiN2Q5Mw=='
# openai key
#API_KEY = "'sk-861mINAavom2SSBqgrI82D4thMOfqT37knCof2o0H0T3BlbkFJ2gdVXJuVjNesNNP2aeUwPoBpZP3a3R1gn1kqv97CsA'"

adriver_config = AgentDriverConfig(
    name=PARAMS['MEM_PIPELINE_CONFIG']['agent_config']['vendor'],
    agent_config=AgentConnectorConfig(
        gen_strategy=PARAMS['MEM_PIPELINE_CONFIG']['agent_config']['gen_strategy'],
        credentials=PARAMS['MEM_PIPELINE_CONFIG']['agent_config']['credentials'],
        ext_params=PARAMS['MEM_PIPELINE_CONFIG']['agent_config']['ext_params']))

# cache driver config
if PARAMS['MEM_PIPELINE_CONFIG']['llm_caching']:
    kvdriver_config = KeyValueDriverConfig(
        db_vendor='mixed_kv',
        db_config=KVDBConnectionConfig(
            db_info=PARAMS['MEM_PIPELINE_CONFIG']['cache_db_info'],
            need_to_clear=PARAMS['MEM_PIPELINE_CONFIG']['cache_need_to_clear'],
            params={
                'redis_config': KVDBConnectionConfig(
                    host=PARAMS['MEM_PIPELINE_CONFIG']['ram_cache_config']['host'],
                    port=PARAMS['MEM_PIPELINE_CONFIG']['ram_cache_config']['port'],
                    params=PARAMS['MEM_PIPELINE_CONFIG']['ram_cache_config']['params']),
                'mongo_config': KVDBConnectionConfig(
                    host=PARAMS['MEM_PIPELINE_CONFIG']['persistent_cache_config']['host'],
                    port=PARAMS['MEM_PIPELINE_CONFIG']['persistent_cache_config']['port'],
                    params=PARAMS['MEM_PIPELINE_CONFIG']['persistent_cache_config']['params'])
            }
        )
    )
else:
    kvdriver_config = None

# extractor stage config
extractor_config = LLMExtractorConfig(
    lang=PARAMS['MEM_PIPELINE_CONFIG']['lang'],
    adriver_config=adriver_config,
    triplets_extraction_task_config=AgentTripletExtrTaskConfigSelector.select(
        base_config_version=PARAMS['MEM_PIPELINE_CONFIG']['extractor_stage']['extract_triplets']['prompts_version']),
    thesises_extraction_task_config=AgentThesisExtrTaskConfigSelector.select(
        base_config_version=PARAMS['MEM_PIPELINE_CONFIG']['extractor_stage']['extract_thesises']['prompts_version']),
)

# updator stage config
updator_config = LLMUpdatorConfig(
    lang=PARAMS['MEM_PIPELINE_CONFIG']['lang'],
    adriver_config=adriver_config,
    replace_simple_task_config=AgentReplSimpleTripletTaskConfigSelector.select(
        base_config_version=PARAMS['MEM_PIPELINE_CONFIG']['updator_stage']['replace_simple_triplets']['prompts_version']),
    replace_thesis_task_config= AgentReplThesisTripletTaskConfigSelector.select(
        base_config_version=PARAMS['MEM_PIPELINE_CONFIG']['updator_stage']['replace_thesis_triplets']['prompts_version']),
    delete_obsolete_info=PARAMS['MEM_PIPELINE_CONFIG']['updator_stage']['delete_obsolete_info']
)

# Setting Memorization Pipeline
mem_config = MemPipelineConfig(
    extractor_config=extractor_config,
    updator_config=updator_config)

########### NodesTree model ###########

leafs_vectordb_config=VectorDBConnectionConfig(
    db_info=PARAMS['KG_DB_CONFIGS']['nodestree_config']['vectordb_leafnodes_config']['db_info'],
    params=PARAMS['KG_DB_CONFIGS']['nodestree_config']['vectordb_leafnodes_config']['params'],
    conn=PARAMS['KG_DB_CONFIGS']['nodestree_config']['vectordb_leafnodes_config']['conn'],
    need_to_clear=PARAMS['KG_DB_CONFIGS']['need_to_clear'])

summ_vectordb_config=VectorDBConnectionConfig(
    db_info=PARAMS['KG_DB_CONFIGS']['nodestree_config']['vectordb_summnodes_config']['db_info'],
    params=PARAMS['KG_DB_CONFIGS']['nodestree_config']['vectordb_summnodes_config']['params'],
    conn=PARAMS['KG_DB_CONFIGS']['nodestree_config']['vectordb_summnodes_config']['conn'],
    need_to_clear=PARAMS['KG_DB_CONFIGS']['need_to_clear'])

tree_graphdb_config = TreeDBConnectionConfig(
    host=PARAMS['KG_DB_CONFIGS']['nodestree_config']['treedb_config']['host'],
    port=PARAMS['KG_DB_CONFIGS']['nodestree_config']['treedb_config']['port'],
    db_info=PARAMS['KG_DB_CONFIGS']['nodestree_config']['treedb_config']['db_info'],
    params=PARAMS['KG_DB_CONFIGS']['nodestree_config']['treedb_config']['params'],
    need_to_clear=PARAMS['KG_DB_CONFIGS']['need_to_clear'])

treemoddel_config = NodesTreeModelConfig(
    vectordb_leafnodes_config=VectorDriverConfig(
        db_vendor=PARAMS['KG_DB_CONFIGS']['nodestree_config']['vectordb_leafnodes_config']['vendor'],
        db_config=leafs_vectordb_config),
    vectordb_summnodes_config=VectorDriverConfig(
        db_vendor=PARAMS['KG_DB_CONFIGS']['nodestree_config']['vectordb_summnodes_config']['vendor'],
        db_config=summ_vectordb_config),
    embedder_config=embedder_config,

    treedb_config=TreeDriverConfig(
        db_vendor=PARAMS['KG_DB_CONFIGS']['nodestree_config']['treedb_config']['vendor'],
        db_config=tree_graphdb_config),

    adriver_config=adriver_config,
    nodes_summarization_task_config=AgentSummNTaskConfigSelector.select(
        PARAMS['KG_DB_CONFIGS']['nodestree_config']['nodes_summarization_task_config']['prompts_version']),

    e2n_sim_threshold=PARAMS['KG_DB_CONFIGS']['nodestree_config']['e2n_sim_threshold'],
    depth_rate=PARAMS['KG_DB_CONFIGS']['nodestree_config']['depth_rate'],
    nodes_aggregation_mechanism=PARAMS['KG_DB_CONFIGS']['nodestree_config']['nodes_aggregation_mechanism']
)

############### SAVING CONFIGS ###############

print("gmodle: ", gmodel_config)
print("emodel: ", emodel_config)
print("tmodel: ", treemoddel_config)
print("mem: ", mem_config)
print("kv_driver: ", kvdriver_config)

joblib.dump(gmodel_config, GRAPH_MODEL_CONFIG_PATH)
joblib.dump(emodel_config, EMBEDDINGS_MODEL_CONFIG_PATH)
joblib.dump(treemoddel_config, NODESTREE_MODEL_CONFIG_PATH)
joblib.dump(mem_config, MEM_PIPELINE_CONFIG_PATH)
joblib.dump(kvdriver_config, CACHE_CONFIG_PATH)

print("############ DONE ############")
