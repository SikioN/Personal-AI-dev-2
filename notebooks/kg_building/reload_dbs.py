import sys
import json
import joblib
import gc
import copy
from tqdm import tqdm
import yaml
import os
from typing import List, Dict, Tuple
import pandas as pd

# получаю params.yaml
PARAMS_FILE_PATH = sys.orig_argv[2]
with open(PARAMS_FILE_PATH, 'r') as stream:
    PARAMS = yaml.safe_load(stream)

sys.path.insert(0, PARAMS['WORKSPACE_CONTAINER_DIRS']['base_path'])

from src.pipelines.memorize import MemPipeline
from src.kg_model import KnowledgeGraphModel

gc.collect()

######## SETTING HYPERPARAMS ###########

DATASET_KGS_PATH = f"{PARAMS['WORKSPACE_CONTAINER_DIRS']['base_path']}/{PARAMS['WORKSPACE_CONTAINER_DIRS']['kg']}/{PARAMS['DATASET_NAME']}"
SPEC_KG_PATH = f"{DATASET_KGS_PATH}/{PARAMS['KNOWLEDGE_GRAPH_NAME']}"

SAVE_PARAMS_PATH = f"{SPEC_KG_PATH}/{PARAMS['SAVE_CONFIGS_NAMES']['hyperparameters']}"

QA_DATASET_PATH = f"{PARAMS['WORKSPACE_CONTAINER_DIRS']['base_path']}/{PARAMS['WORKSPACE_CONTAINER_DIRS']['qa_datasets']}/{PARAMS['DATASET_NAME']}"

TMP_EXTRACTED_TRIPLETS_PATH = f"{SPEC_KG_PATH}/{PARAMS['SAVE_CONFIGS_NAMES']['tmp_extracted_triplets']}"
EXTRACTED_TRIPLETS_PATH = f"{SPEC_KG_PATH}/{PARAMS['SAVE_CONFIGS_NAMES']['extracted_triplets']}"

GRAPH_MODEL_CONFIG_PATH = f"{SPEC_KG_PATH}/{PARAMS['SAVE_CONFIGS_NAMES']['graph_config']}"
EMBEDDINGS_MODEL_CONFIG_PATH = f"{SPEC_KG_PATH}/{PARAMS['SAVE_CONFIGS_NAMES']['embeddings_config']}"

MEM_PIPELINE_CONFIG_PATH = f"{SPEC_KG_PATH}/{PARAMS['SAVE_CONFIGS_NAMES']['mem_pipeline_config']}"
CACHE_CONFIG_PATH = f"{SPEC_KG_PATH}/{PARAMS['SAVE_CONFIGS_NAMES']['kvdriver_cache_config']}"

######## Setting knowledge graph model ######

gmodel_config = joblib.load(GRAPH_MODEL_CONFIG_PATH)
emodel_config = joblib.load(EMBEDDINGS_MODEL_CONFIG_PATH)

print("GMODEL_CONFIG:\n", gmodel_config)
print("EMODEL_CONFIG:\n", emodel_config)

kg_model = KnowledgeGraphModel(
    graph_config=gmodel_config,
    embeddings_config=emodel_config)

# checking knowledge graph size
print(kg_model.embeddings_struct.vectordbs['nodes'].count_items())
print(kg_model.embeddings_struct.vectordbs['triplets'].count_items())
print(kg_model.graph_struct.db_conn.count_items())

# !!! PAY ATTENTION !!!
# print("CLEARING KG-MODEL...")
# kg_model.clear()

# print(kg_model.embeddings_struct.vectordbs['nodes'].count_items())
# print(kg_model.embeddings_struct.vectordbs['triplets'].count_items())
# print(kg_model.graph_struct.db_conn.count_items())

######## SETTING MEMORIZE PIPELINE ######

mem_config = joblib.load(MEM_PIPELINE_CONFIG_PATH)
kvdriver_config =  joblib.load(CACHE_CONFIG_PATH)

print("MEM_CONFIG:\n", mem_config)
print("KVDRIVER_CONFIG:\n", kvdriver_config)

mem_pipeline = MemPipeline(kg_model, mem_config, kvdriver_config)

# checking caches status
if PARAMS['MEM_PIPELINE_CONFIG']['llm_caching']:
    print("extract_triples cached: ", mem_pipeline.extractor.triplets_extraction_solver.cachekv.kv_conn.count_items())
    print("extract_thesises cached: ", mem_pipeline.extractor.thesises_extraction_solver.cachekv.kv_conn.count_items())
    print("replace_simple cached: ", mem_pipeline.updator.replace_simple_solver.cachekv.kv_conn.count_items())
    print("replace_thesises cached: ", mem_pipeline.updator.replace_hyper_solver.cachekv.kv_conn.count_items())

mem_pipeline.updator.kg_model.embeddings_struct.vectordbs['nodes'].client.release_collection(collection_name='vectorized_nodes')
mem_pipeline.updator.kg_model.embeddings_struct.vectordbs['nodes'].client.load_collection(collection_name='vectorized_nodes',skip_load_dynamic_field=True)
print('vectorized_nodes: ', mem_pipeline.updator.kg_model.embeddings_struct.vectordbs['nodes'].client.get_load_state('vectorized_nodes')['state'])

mem_pipeline.updator.kg_model.embeddings_struct.vectordbs['triplets'].client.release_collection(collection_name='vectorized_triplets')
mem_pipeline.updator.kg_model.embeddings_struct.vectordbs['triplets'].client.load_collection(collection_name='vectorized_triplets',skip_load_dynamic_field=True)
print('vectorized_triplets: ', mem_pipeline.updator.kg_model.embeddings_struct.vectordbs['triplets'].client.get_load_state('vectorized_triplets')['state'])

######## LOADING EXTRACTED TRIPLETS ########

extracted_group_tripelts = joblib.load(EXTRACTED_TRIPLETS_PATH)

######## LOADING TRIPLETS TO VECTOR DB ########

# diaasq qwen25 66 + 92 + 1657 + 1533 | Done
# hotpotqa qwen25 1510 + 1583 | Done
# triviaqa qwen25 1237 | Done | 151 + 764

step = 100
counter = 0
for triplets in tqdm(extracted_group_tripelts[151 + 764:]):
    mem_pipeline.updator.kg_model.graph_struct.create_triplets(triplets, status_bar=False)
    mem_pipeline.updator.kg_model.embeddings_struct.create_triplets(triplets, status_bar=False)
    
    #
    if counter % step == 0:
        print(kg_model.embeddings_struct.vectordbs['nodes'].count_items())
        print(kg_model.embeddings_struct.vectordbs['triplets'].count_items())
        print(kg_model.graph_struct.db_conn.count_items())
    counter += 1

print(kg_model.embeddings_struct.vectordbs['nodes'].count_items())
print(kg_model.embeddings_struct.vectordbs['triplets'].count_items())
print(kg_model.graph_struct.db_conn.count_items())


######## CHECKIN CONSISTENCY ########

mem_pipeline.updator.kg_model.check_consistency()

print("##### DONE #####")