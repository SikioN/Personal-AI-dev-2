import sys
import json
import joblib
import gc
import copy
from tqdm import tqdm
from time import time
import yaml
import os
from typing import List, Dict, Tuple
import pandas as pd

# получаю params.yaml
PARAMS_FILE_PATH = sys.orig_argv[2]
with open(PARAMS_FILE_PATH, 'r') as stream:
    PARAMS = yaml.safe_load(stream)

sys.path.insert(0, PARAMS['WORKSPACE_CONTAINER_DIRS']['base_path'])

from src.kg_model.nodestree_model import NodesTreeModel
from src.kg_model import KnowledgeGraphModel

gc.collect()

########  ###########
print("SETTING HYPERPARAMS")

DATASET_KGS_PATH = f"{PARAMS['WORKSPACE_CONTAINER_DIRS']['base_path']}/{PARAMS['WORKSPACE_CONTAINER_DIRS']['kg']}/{PARAMS['DATASET_NAME']}"
SPEC_KG_PATH = f"{DATASET_KGS_PATH}/{PARAMS['KNOWLEDGE_GRAPH_NAME']}"

SAVE_PARAMS_PATH = f"{SPEC_KG_PATH}/hyperparameters_updated.yaml"

QA_DATASET_PATH = f"{PARAMS['WORKSPACE_CONTAINER_DIRS']['base_path']}/{PARAMS['WORKSPACE_CONTAINER_DIRS']['qa_datasets']}/{PARAMS['DATASET_NAME']}"

TMP_EXTRACTED_TRIPLETS_PATH = f"{SPEC_KG_PATH}/{PARAMS['SAVE_CONFIGS_NAMES']['tmp_extracted_triplets']}"
EXTRACTED_TRIPLETS_PATH = f"{SPEC_KG_PATH}/{PARAMS['SAVE_CONFIGS_NAMES']['extracted_triplets']}"

GRAPH_MODEL_CONFIG_PATH = f"{SPEC_KG_PATH}/{PARAMS['SAVE_CONFIGS_NAMES']['graph_config']}"
EMBEDDINGS_MODEL_CONFIG_PATH = f"{SPEC_KG_PATH}/{PARAMS['SAVE_CONFIGS_NAMES']['embeddings_config']}"
NODESTREE_MODEL_CONFIG_PATH = f"{SPEC_KG_PATH}/{PARAMS['SAVE_CONFIGS_NAMES']['nodestree_config']}"

MEM_PIPELINE_CONFIG_PATH = f"{SPEC_KG_PATH}/{PARAMS['SAVE_CONFIGS_NAMES']['mem_pipeline_config']}"
CACHE_CONFIG_PATH = f"{SPEC_KG_PATH}/{PARAMS['SAVE_CONFIGS_NAMES']['kvdriver_cache_config']}"

######## Setting nodes-tree model ######
print("Setting nodes-tree model...")

gmodel_config = joblib.load(GRAPH_MODEL_CONFIG_PATH)
emodel_config = joblib.load(EMBEDDINGS_MODEL_CONFIG_PATH)
treemodel_config = joblib.load(NODESTREE_MODEL_CONFIG_PATH)
kvdriver_config =  joblib.load(CACHE_CONFIG_PATH)

print("GMODEL_CONFIG:\n", gmodel_config)
print("EMODEL_CONFIG:\n", emodel_config)
print("TMODEL_CONFIG:\n", treemodel_config)
print("KVDRIVER_CONFIG:\n", kvdriver_config)

kg_model = KnowledgeGraphModel(
    graph_config=gmodel_config, embeddings_config=emodel_config,
    nodestree_config=treemodel_config, cache_kvdriver_config=kvdriver_config)

# !!! PAY ATTENTION !!!
# kg_model.nodestree_struct.vectordb_leafnodes_conn.clear()
# kg_model.nodestree_struct.vectordb_summnodes_conn.clear()
# kg_model.nodestree_struct.treedb_conn.clear()
# kg_model.nodestree_struct.nodes_summarization_solver.cachekv.kv_conn.clear()

# checking knowledge graph size
print("tree_struct: ", kg_model.nodestree_struct.count_items())
print("vector_struct (nodes): " ,kg_model.embeddings_struct.vectordbs['nodes'].count_items())
print("vector_struct (triplets): ", kg_model.embeddings_struct.vectordbs['triplets'].count_items())
print("graph struct: ", kg_model.graph_struct.db_conn.count_items())

# checking caches status
if PARAMS['MEM_PIPELINE_CONFIG']['llm_caching']:
    print("summ_nodes cached: ", kg_model.nodestree_struct.nodes_summarization_solver.cachekv.kv_conn.count_items())

############ ############
print("SAVING HYPERPARAMS...")

with open(SAVE_PARAMS_PATH, 'w') as fd:
    yaml.dump(PARAMS, fd, default_flow_style=False)

######## ########
print("LOADING EXTRACTED TRIPLETS...")

extracted_group_tripelts = joblib.load(EXTRACTED_TRIPLETS_PATH)

######## NODES-TREE BUILDING ########
print("NODES-TREE BUILDING...")

# hotpot deepseek 82+103+100+227+74
# hotpot llama8b 590+1091+452+116+2+645+33+97+196+286+77 | Done
# diaasq qwen7b 44+23+122+13+220+29+47+20+254+23+116+801+490

step = 200
counter = 0
s_time = time()
process = enumerate(extracted_group_tripelts[44+23+122+13+220+29+47+20+254+23+116+801+490:])
milestone_time = time()
for i, triplets in process:
    print(f"Triplets group #{i} / {len(extracted_group_tripelts)}")
    operation_info = kg_model.nodestree_struct.expand_tree(triplets, status_bar=True)
    display_info = {
        'existed_nodes': len(operation_info['existed_nodes']),
        'added_nodes': len(operation_info['added_nodes'])}

    #
    if counter % step == 0:
        ntree_count_info = kg_model.nodestree_struct.count_items()
        display_info.update(ntree_count_info)
        print(display_info)

        kg_model.nodestree_struct.check_consistency()
    else:
        print(display_info)

    cur_time = time()
    print(f"process_time: {(cur_time - milestone_time) / 60} min")
    milestone_time = cur_time

    counter += 1

e_time = time()
print(f"ELAPSED TIME: {(e_time - s_time) / 60} min")

######## ########
print("CHECKIN CONSISTENCY...")

kg_model.nodestree_struct.check_consistency()

print("##### DONE #####")
