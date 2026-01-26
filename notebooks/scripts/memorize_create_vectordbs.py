import sys
import json
from tqdm import tqdm
from openai import OpenAI
import os
from functools import reduce
import joblib
from typing import Dict
import gc

# TO CHANGE
#BASEDIR = "/workspace"
BASEDIR = "/home/dzigen/Desktop/PersonalAI/Personal-AI/"
# TO CHNAGE

sys.path.insert(0, BASEDIR)

from src.utils.data_structs import TripletCreator, NodeCreator, Relation, NODES_TYPES_MAP, RELATIONS_TYPES_MAP
from src.db_models.graph_db.neo4j_functions import Neo4jConnection
from src.db_models.embeddings_db.embedding_functions import EmbeddingsDatabaseConnection, EmbeddingsDatabaseConnectionConfig, VectorDBConnectionConfig, EmbedderModelConfig
from src.knowledge_graph_model import KnowledgeGraphModel

# personalai_mmenschikov_neo4j
NEO4J_URL ="bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PWD = "password"

GRAPH_DB_NAME = 'DiaasqGigachat'
NODES_VECTORDB_PATH = '../../data/graph_structures/vectorized_nodes/v12/densedb'
TRIPLETS_VECTORDB_PATH = '../../data/graph_structures/vectorized_triplets/v8/densedb'
EMBEDDER_MODEL_PATH = '../../models/intfloat/multilingual-e5-small'
gc.collect()

###########

print("connecting to knowledge-graph model")

kg_model = KnowledgeGraphModel(
    graph_db=Neo4jConnection(uri=NEO4J_URL, user=NEO4J_USER, pwd=NEO4J_PWD, db_name=GRAPH_DB_NAME),
    embeddings_db=EmbeddingsDatabaseConnection(EmbeddingsDatabaseConnectionConfig(
        nodes_db_config=VectorDBConnectionConfig(
            NODES_VECTORDB_PATH, 'vectorized_nodes', is_exist=False, need_to_clear=False
        ),
        triplets_db_config=VectorDBConnectionConfig(
            TRIPLETS_VECTORDB_PATH, 'vectorized_triplets', is_exist=False, need_to_clear=False
        ),
        embedder_config=EmbedderModelConfig(
            model_name_or_path=EMBEDDER_MODEL_PATH
        )
    ))
)

###########

print("reading/formating triplets from graphdb...")

raw_triplets = list(kg_model.graph_db.execute_query("MATCH (n1)-[rel]->(n2) RETURN n1, rel, n2"))
formated_triplets = []
for raw_triplet in tqdm(raw_triplets):
    start_node = NodeCreator.create(id=raw_triplet['n1'].element_id, name=str(raw_triplet['n1']['name']),
                                        type=NODES_TYPES_MAP[list(raw_triplet['n1'].labels)[0]],
                                        prop=dict(raw_triplet['n1']))
    end_node = NodeCreator.create(id=raw_triplet['n2'].element_id, name=str(raw_triplet['n2']['name']),
                                        type=NODES_TYPES_MAP[list(raw_triplet['n2'].labels)[0]],
                                        prop=dict(raw_triplet['n2']))
    relation = Relation(id=raw_triplet['rel'].element_id, name=str(raw_triplet['rel']['name']),
                            type=RELATIONS_TYPES_MAP[raw_triplet['rel'].type],
                            prop=dict(raw_triplet['rel']))

    triplet = TripletCreator.create(start_node, relation, end_node, add_stringified_triplet=False)
    formated_triplets.append(triplet)

###########

print("vectorizing triplets/nodes and saving in vectordbs...")

kg_model.embeddings_db.add_triplets(formated_triplets, batch_size=128)
kg_model.graph_db.close()

print("DONE")
