import sys
import yaml

# Read YAML file
PARAMS_FILE_PATH = sys.orig_argv[2]
with open(PARAMS_FILE_PATH, 'r') as stream:
    PARAMS = yaml.safe_load(stream)

DATASET_KGS_PATH = f"{PARAMS['BASE_DATA_PATH']}/{PARAMS['PERSONALAI_REPO_DIRS']['kg']}/{PARAMS['DATASET_NAME']}"
SPEC_KG_PATH = f"{DATASET_KGS_PATH}/{PARAMS['KNOWLEDGE_GRAPH_NAME']}"

# параметры для графовой бд (neo4j)
GRAPH_DB_PATH = f"{SPEC_KG_PATH}/{PARAMS['KG_DIR_STRUCT']['graph_part']}"

neo4j_cnt_variables = {
    'NEO4J_CNTNAME': PARAMS['CONTAINERS_ADDITIONAL_CONFIG']['neo4j_cntname'],
    'NEO4J_HOST': PARAMS['KG_DB_CONFIGS']['graphdb_config']['host'],

    'NEO4J_EXTERNAL_PORT': PARAMS['KG_DB_CONFIGS']['graphdb_config']['port'],
    'NEO4J_UI_EXTERNAL_PORT': PARAMS['CONTAINERS_ADDITIONAL_CONFIG']['neo4j_ui_port'],

    'NEO4j_AUTH_USER': PARAMS['KG_DB_CONFIGS']['graphdb_config']['params']['user'],
    'NEO4j_AUTH_PWD': PARAMS['KG_DB_CONFIGS']['graphdb_config']['params']['pwd'],

    'NEO4J_LOCAL_VOLUME': GRAPH_DB_PATH
}

# параметры для persistent бд (mongo)
KV_DB_PATH = f"{SPEC_KG_PATH}/{PARAMS['KG_DIR_STRUCT']['cache_dir']['base']}"
PERSISTENT_DB_PATH = f"{KV_DB_PATH}/{PARAMS['KG_DIR_STRUCT']['cache_dir']['persistant']}/"

mongo_cnt_variables = {
    'MONGO_CNTNAME': PARAMS['CONTAINERS_ADDITIONAL_CONFIG']['mongo_cntname'],
    'MONGO_HOST': PARAMS['MEM_PIPELINE_CONFIG']['persistent_cache_config']['host'],

    'MONGO_EXTERNAL_PORT': PARAMS['MEM_PIPELINE_CONFIG']['persistent_cache_config']['port'],

    'MONGO_AUTH_USER': PARAMS['MEM_PIPELINE_CONFIG']['persistent_cache_config']['params']['username'],
    'MONGO_AUTH_PASS': PARAMS['MEM_PIPELINE_CONFIG']['persistent_cache_config']['params']['password'],

    'MONGO_LOCAL_VOLUME': PERSISTENT_DB_PATH
}

mongoui_cnt_variables = {
    'MONGO_UI_CNTNAME': PARAMS['CONTAINERS_ADDITIONAL_CONFIG']['mongo_ui_cntname'],
    'MONGO_UI_HOST': PARAMS['CONTAINERS_ADDITIONAL_CONFIG']['mongo_ui_host'],

    'MONGO_UI_EXTERNAL_PORT': PARAMS['CONTAINERS_ADDITIONAL_CONFIG']['mongo_ui_port']
}

# параметры для ram бд (redis)
RAM_DB_PATH = f"{KV_DB_PATH}/{PARAMS['KG_DIR_STRUCT']['cache_dir']['ram']}"

redis_cnt_variables = {
    'REDIS_CNTNAME': PARAMS['CONTAINERS_ADDITIONAL_CONFIG']['redis_cntname'],
    'REDIS_HOST': PARAMS['MEM_PIPELINE_CONFIG']['ram_cache_config']['host'],

    'REDIS_EXTERNAL_PORT': PARAMS['MEM_PIPELINE_CONFIG']['ram_cache_config']['port'],

    'REDIS_AUTH_USER': PARAMS['MEM_PIPELINE_CONFIG']['ram_cache_config']['params']['username'],
    'REDIS_AUTH_PASS': PARAMS['MEM_PIPELINE_CONFIG']['ram_cache_config']['params']['password'],

    'REDIS_LOCAL_VOLUME': RAM_DB_PATH,
    'REDIS_CONFIG': f"{PARAMS['BASE_PERSONALAI_PATH']}/{PARAMS['PERSONALAI_REPO_DIRS']['configs']}/{PARAMS['MEM_PIPELINE_CONFIG']['ram_cache_config']['db_configuration']}"
}

redisui_cnt_variables = {
    'REDIS_UI_CNTNAME': PARAMS['CONTAINERS_ADDITIONAL_CONFIG']['redis_ui_cntname'],
    'REDIS_UI_HOST': PARAMS['CONTAINERS_ADDITIONAL_CONFIG']['redis_ui_host'],
    'REDIS_UI_EXTERNAL_PORT': PARAMS['CONTAINERS_ADDITIONAL_CONFIG']['redis_ui_port']
}

# параметры для workspace - окружения
workspace_cnt_variables = {
    'WORKSPACE_CNTNAME': PARAMS['CONTAINERS_ADDITIONAL_CONFIG']['workspace_cntname'],
    'WORKSPACE_HOST': PARAMS['CONTAINERS_ADDITIONAL_CONFIG']['workspace_host'],

    'EXTERNAL_SPEC_KG_PATH': SPEC_KG_PATH,
    'EXTERNAL_SPEC_QADS_PATH': f"{PARAMS['BASE_PERSONALAI_PATH']}/{PARAMS['PERSONALAI_REPO_DIRS']['qa_datasets']}/{PARAMS['DATASET_NAME']}",
    'EXTERNAL_NOTEBOOKS_PATH': f"{PARAMS['BASE_PERSONALAI_PATH']}/{PARAMS['PERSONALAI_REPO_DIRS']['notebooks']}",
    'EXTERNAL_SRC_PATH': f"{PARAMS['BASE_PERSONALAI_PATH']}/{PARAMS['PERSONALAI_REPO_DIRS']['src']}",
    'EXTERNAL_MODELS_PATH': f"{PARAMS['BASE_PERSONALAI_PATH']}/{PARAMS['PERSONALAI_REPO_DIRS']['models']}",

    'INTERNAL_SPEC_KG_PATH': f"{PARAMS['WORKSPACE_CONTAINER_DIRS']['base_path']}/{PARAMS['WORKSPACE_CONTAINER_DIRS']['kg']}/{PARAMS['DATASET_NAME']}/{PARAMS['KNOWLEDGE_GRAPH_NAME']}",
    'INTERNAL_SPEC_QADS_PATH': f"{PARAMS['WORKSPACE_CONTAINER_DIRS']['base_path']}/{PARAMS['WORKSPACE_CONTAINER_DIRS']['qa_datasets']}/{PARAMS['DATASET_NAME']}",
    'INTERNAL_NOTEBOOKS_PATH': f"{PARAMS['WORKSPACE_CONTAINER_DIRS']['base_path']}/{PARAMS['WORKSPACE_CONTAINER_DIRS']['notebooks']}",
    'INTERNAL_SRC_PATH': f"{PARAMS['WORKSPACE_CONTAINER_DIRS']['base_path']}/{PARAMS['WORKSPACE_CONTAINER_DIRS']['src']}",
    'INTERNAL_MODELS_PATH': f"{PARAMS['WORKSPACE_CONTAINER_DIRS']['base_path']}/{PARAMS['WORKSPACE_CONTAINER_DIRS']['models']}"
}

# параметры для milvus бд
VECTOR_DB_PATH = f"{SPEC_KG_PATH}/{PARAMS['KG_DIR_STRUCT']['embeddings_part']}"

milvus_cnt_variables = {
    'MILVUS_CNTNAME': PARAMS['CONTAINERS_ADDITIONAL_CONFIG']['milvus_cntname'],
    'MILVUS_HOST': PARAMS['CONTAINERS_ADDITIONAL_CONFIG']['milvus_host'],

    'MILVUS_EXTERNAL_PORT1': PARAMS['CONTAINERS_ADDITIONAL_CONFIG']['milvus_port1'],
    'MILVUS_EXTERNAL_PORT2': PARAMS['CONTAINERS_ADDITIONAL_CONFIG']['milvus_port2'],
    'MILVUS_UI_EXTERNAL_PORT': PARAMS['CONTAINERS_ADDITIONAL_CONFIG']['milvus_ui_port'],

    'MILVUS_LOCAL_VOLUME': VECTOR_DB_PATH,
    'MILVUS_CONFIG': f"{PARAMS['BASE_PERSONALAI_PATH']}/{PARAMS['PERSONALAI_REPO_DIRS']['configs']}/{PARAMS['CONTAINERS_ADDITIONAL_CONFIG']['milvus_config']}"
}

# параметры для контейнера с llm-моделями
llmagents_cnt_variables = {
    'OLLAMA_CNTNAME': PARAMS['CONTAINERS_ADDITIONAL_CONFIG']['ollama_cntname'],
    'OLLAMA_HOST': PARAMS['CONTAINERS_ADDITIONAL_CONFIG']['ollama_host'],

    'OLLAMA_EXTERNAL_PORT': PARAMS['MEM_PIPELINE_CONFIG']['agent_config']['credentials'].get('port', 11434),

    'OLLAMA_LOCAL_VOLUME': PARAMS['OLLAMA_MODELS_PATH']
}

compose_variables = {
    'COMPOSE_PROJECT_NAME': f"{PARAMS['DATASET_NAME']}_{PARAMS['KNOWLEDGE_GRAPH_NAME']}"
}

#
def dictvar_to_string(dict_variables) -> str:
    return '\n'.join(list(map(lambda item: f'{item[0]}="{item[1]}"', dict_variables.items())))

def add_prefixes(dict_variables) -> None:
    for k in dict_variables.keys():
        if k.endswith("_CNTNAME"):
            dict_variables[k] = f"{dict_variables[k]}_{PARAMS['DATASET_NAME']}_{PARAMS['KNOWLEDGE_GRAPH_NAME']}"

env_variables = [
    neo4j_cnt_variables, milvus_cnt_variables, mongo_cnt_variables, mongoui_cnt_variables,
    redis_cnt_variables, redisui_cnt_variables, workspace_cnt_variables]
for variables in env_variables:
    add_prefixes(variables)
env_variables += [llmagents_cnt_variables, compose_variables]

env_variables = '\n'.join(list(map(lambda vars: dictvar_to_string(vars), env_variables)))

DC_ENV_PATH = f"{PARAMS['BASE_PERSONALAI_PATH']}/{PARAMS['PERSONALAI_REPO_DIRS']['kg']}/{PARAMS['DATASET_NAME']}/{PARAMS['KNOWLEDGE_GRAPH_NAME']}/{PARAMS['SAVE_CONFIGS_NAMES']['docker_compose_env']}"
with open(DC_ENV_PATH, 'w', encoding='utf-8') as fd:
    fd.write(env_variables)

print("############ DONE ############")
