import yaml
import os
import sys

######## SETTING PARAMS ###########

# Read YAML file
PARAMS_FILE_PATH = sys.orig_argv[2]
with open(PARAMS_FILE_PATH, 'r') as stream:
    PARAMS = yaml.safe_load(stream)

DATASET_KGS_PATH = f"{PARAMS['BASE_PERSONALAI_PATH']}/{PARAMS['PERSONALAI_REPO_DIRS']['kg']}/{PARAMS['DATASET_NAME']}"
SPEC_KG_PATH = f"{DATASET_KGS_PATH}/{PARAMS['KNOWLEDGE_GRAPH_NAME']}"

VECTORIZED_DB_PATH = f"{SPEC_KG_PATH}/{PARAMS['KG_DIR_STRUCT']['embeddings_part']}"
GRAPH_DB_PATH = f"{SPEC_KG_PATH}/{PARAMS['KG_DIR_STRUCT']['graph_part']}"
KV_DB_PATH = f"{SPEC_KG_PATH}/{PARAMS['KG_DIR_STRUCT']['cache_dir']['base']}"
PERSISTENT_DB_PATH = f"{KV_DB_PATH}/{PARAMS['KG_DIR_STRUCT']['cache_dir']['persistant']}"
RAM_DB_PATH = f"{KV_DB_PATH}/{PARAMS['KG_DIR_STRUCT']['cache_dir']['ram']}"

TMP_EXTRACTED_TRIPLETS_PATH = f"{SPEC_KG_PATH}/{PARAMS['SAVE_CONFIGS_NAMES']['tmp_extracted_triplets']}"

if PARAMS['INIT_STRUCT']:
    if not os.path.exists(DATASET_KGS_PATH):
        raise ValueError(f"Директории не существует: {DATASET_KGS_PATH}")

    if os.path.exists(SPEC_KG_PATH):
        raise ValueError(f"Директория существует: {SPEC_KG_PATH}")
    if os.path.exists(GRAPH_DB_PATH):
        raise ValueError(f"Директория существует: {GRAPH_DB_PATH}")
    if os.path.exists(VECTORIZED_DB_PATH):
        raise ValueError(f"Директория существует: {VECTORIZED_DB_PATH}")
    if os.path.exists(KV_DB_PATH):
        raise ValueError(f"Директория существует: {KV_DB_PATH}")
    if os.path.exists(PERSISTENT_DB_PATH):
        raise ValueError(f"Директория существует: {PERSISTENT_DB_PATH}")
    if os.path.exists(RAM_DB_PATH):
        raise ValueError(f"Директория существует: {RAM_DB_PATH}")

    if os.path.exists(TMP_EXTRACTED_TRIPLETS_PATH):
        raise ValueError(f"Директория существует: {TMP_EXTRACTED_TRIPLETS_PATH}")

    os.mkdir(SPEC_KG_PATH)

    os.mkdir(VECTORIZED_DB_PATH)
    os.mkdir(GRAPH_DB_PATH)

    os.mkdir(KV_DB_PATH)
    os.mkdir(PERSISTENT_DB_PATH)
    os.mkdir(RAM_DB_PATH)

    os.mkdir(TMP_EXTRACTED_TRIPLETS_PATH)

print("############ DONE ############")
