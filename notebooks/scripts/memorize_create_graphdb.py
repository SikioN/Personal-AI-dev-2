import sys
import json
from tqdm import tqdm
from openai import OpenAI
import os
import joblib
from functools import reduce
import joblib
from typing import Dict
import gc

# TO CHANGE
# "/workspace"
BASEDIR = "/home/dzigen/Desktop/PersonalAI/Personal-AI/"
# TO CHNAGE

sys.path.insert(0, BASEDIR)

from src.utils.data_structs import RelationType, NodeType
from src.utils.data_structs import TripletCreator, NodeCreator, Relation, NODES_TYPES_MAP, RELATIONS_TYPES_MAP
from src.db_models.graph_db.neo4j_functions import Neo4jConnection
from src.db_models.embeddings_db.embedding_functions import EmbeddingsDatabaseConnection, EmbeddingsDatabaseConnectionConfig, VectorDBConnectionConfig
from src.knowledge_graph_model import KnowledgeGraphModel

# personalai_mmenschikov_neo4j
NEO4J_URL ="bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PWD = "password"

GRAPH_DB_NAME = 'DiaasqGigachat'
DATASET_PATH = '../../data/Augment_DiaASQ.json'
LOAD_EXTRACTED_TRIPLETS_FILE = "../../data/tmp_new_graph_extracted/tmp_extracted_gigachat_triplets.dump"
gc.collect()

###########

graph_db = graph_db=Neo4jConnection(uri=NEO4J_URL, user=NEO4J_USER, pwd=NEO4J_PWD, db_name=GRAPH_DB_NAME)

###########

print("loading structures..")
#base_dialogs = json.loads(open(DATASET_PATH, 'r', encoding='utf-8').read())
#raw_time = [dialogue['time'].split(', ')[0].strip() for dialogue in base_dialogs['data']]
#print(len(raw_time))

#extracted_triplets = json.loads(open(LOAD_EXTRACTED_TRIPLETS_FILE, 'r', encoding='utf-8').read())
extracted_triplets = joblib.load(LOAD_EXTRACTED_TRIPLETS_FILE)
print(len(extracted_triplets))

#print("adding time...")
#not_str_counter = 0
#all_items_counter = 0
#for group_idx in tqdm(range(len(extracted_triplets))):
#    cur_time = raw_time[group_idx]
#    for triplet_idx in range(len(extracted_triplets[group_idx])):
#        for item_idx in range(len(extracted_triplets[group_idx][triplet_idx])):
#            if type(extracted_triplets[group_idx][triplet_idx][item_idx]['name']) is not str:
#                not_str_counter += 1
#
#            all_items_counter += 1
#            extracted_triplets[group_idx][triplet_idx][item_idx]['name'] = str(extracted_triplets[group_idx][triplet_idx][item_idx]['name']).strip()
#
#        if extracted_triplets[group_idx][triplet_idx][1]['prop']['type'] == 'simple':
#            extracted_triplets[group_idx][triplet_idx][1]['prop']['time'] = cur_time
#        else:
#            extracted_triplets[group_idx][triplet_idx][2]['prop']['time'] = cur_time#
#
#print(f"not-str values in 'name'-field: {not_str_counter}/{all_items_counter}")

print("flat...")
extracted_triplets = reduce(lambda acc, v: acc + v, extracted_triplets, [])
print(len(extracted_triplets))

# костыль
for triplet in tqdm(extracted_triplets):
    if type(triplet.relation.name) is not str:
        triplet.relation.name = triplet.relation.name.value

#print("foramting triplets...")
#formated_triplets = []
#for raw_triplet in tqdm(extracted_triplets):
#    formated_triplets.append(TripletCreator.create(
#        NodeCreator.create(
#            name=raw_triplet[0]['name'], type=NODES_TYPES_MAP[raw_triplet[0]['type']],
#            prop=raw_triplet[0]['prop'], add_stringified_node=False),
#        Relation(name=raw_triplet[1]['name'], type=RELATIONS_TYPES_MAP[raw_triplet[1]['prop']['type']],
#                 prop={k: v for k, v in raw_triplet[1]['prop'].items() if k != 'type'}),
#        NodeCreator.create(name=raw_triplet[2]['name'], type=NODES_TYPES_MAP[raw_triplet[2]['type']],
#                           prop=raw_triplet[2]['prop'], add_stringified_node=False)
#    ))

print("clearing database...")
graph_db.execute_query("match (a) -[r] -> () delete a, r")
graph_db.execute_query("match (a) delete a")

# 89964
print("adding triplets to grapgdb...")
graph_db.create_triplets(extracted_triplets)

print("DONE!")
