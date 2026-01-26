import sys
import json
import joblib
import gc
from tqdm import tqdm
import numpy as np
from collections import defaultdict
import os
from typing import List, Dict, Tuple
import yaml

# Read YAML file
PARAMS_FILE_PATH = sys.orig_argv[2]
with open(PARAMS_FILE_PATH, 'r') as stream:
    PARAMS = yaml.safe_load(stream)

sys.path.insert(0, PARAMS['WORKSPACE_CONTAINER_DIRS']['base_path'])
from src.kg_model import KnowledgeGraphModel

gc.collect()

###############Loading hyperparams###################

DATASET_KGS_PATH = f"{PARAMS['WORKSPACE_CONTAINER_DIRS']['base_path']}/{PARAMS['WORKSPACE_CONTAINER_DIRS']['kg']}/{PARAMS['DATASET_NAME']}"
SPEC_KG_PATH = f"{DATASET_KGS_PATH}/{PARAMS['KNOWLEDGE_GRAPH_NAME']}"

GRAPH_MODEL_CONFIG_PATH = f"{SPEC_KG_PATH}/{PARAMS['SAVE_CONFIGS_NAMES']['graph_config']}"
EMBEDDINGS_MODEL_CONFIG_PATH = f"{SPEC_KG_PATH}/{PARAMS['SAVE_CONFIGS_NAMES']['embeddings_config']}"

GRAPH_STATS_DIR = f"{SPEC_KG_PATH}/{PARAMS['SAVE_CONFIGS_NAMES']['graph_statistics_dir']}"
GRAPH_STATS_INFO = f"{GRAPH_STATS_DIR}/{PARAMS['SAVE_CONFIGS_NAMES']['kg_stats']}"
GRAPH_HEALTH_CHECKS_PATH = f"{GRAPH_STATS_DIR}/{PARAMS['SAVE_CONFIGS_NAMES']['kg_health_checks']}"

##################################

if not os.path.exists(DATASET_KGS_PATH):
    raise ValueError(f"Директории не существует: {DATASET_KGS_PATH}")
if not os.path.exists(SPEC_KG_PATH):
    raise ValueError(f"Директория не существует: {SPEC_KG_PATH}")

if os.path.exists(GRAPH_STATS_DIR):
    raise ValueError(f"Директория существует: {GRAPH_STATS_DIR}")
if os.path.exists(GRAPH_HEALTH_CHECKS_PATH):
    raise ValueError(f"Файл существует: {GRAPH_HEALTH_CHECKS_PATH}")

os.mkdir(GRAPH_STATS_DIR)

###############Computing KG statistics###################

def graph_nodes_counter(kg_model: KnowledgeGraphModel) -> Dict[str, object]:
    info = dict()
    nodes_count = kg_model.graph_struct.db_conn.execute_query("MATCH (a) RETURN count(a) as count_nodes")[0]['count_nodes']
    info['nodes_amount'] = nodes_count

    for node_tpe in ['object', 'hyper', 'episodic']:
        spec_nodes_count = kg_model.graph_struct.db_conn.execute_query(f"MATCH (a:{node_tpe}) RETURN count(a) as count_nodes")[0]['count_nodes']
        info[f'{node_tpe}_nodes_count'] = spec_nodes_count

    return info

def graph_relations_counter(kg_model: KnowledgeGraphModel) -> Dict[str, object]:
    info = dict()
    rels_count = kg_model.graph_struct.db_conn.execute_query("MATCH (a)-[rel]->(b) RETURN count(rel) as count_rels")[0]['count_rels']
    info['relations_amount'] = rels_count

    for rel_tpe in ['simple', 'hyper', 'episodic']:
        spec_rels_count = kg_model.graph_struct.db_conn.execute_query(f"MATCH (a)-[rel:{rel_tpe}]->(b) RETURN count(a) as count_rels")[0]['count_rels']
        info[f'{rel_tpe}_rels_count'] = spec_rels_count

    epi_rels_with_objec_nodes_count = kg_model.graph_struct.db_conn.execute_query("MATCH (a:object)-[rel:episodic]->(b) RETURN count(a) as count_rels")[0]['count_rels']
    epi_rels_with_hyper_nodes_count = kg_model.graph_struct.db_conn.execute_query("MATCH (a:hyper)-[rel:episodic]->(b) RETURN count(a) as count_rels")[0]['count_rels']
    info['episodic_with_object_rels_count'] = epi_rels_with_objec_nodes_count
    info['episodic_with_hyper_rels_count'] = epi_rels_with_hyper_nodes_count

    return info

def graph_nodes_neighbours_counter(kg_model: KnowledgeGraphModel) -> Dict[str, object]:
    info = dict()

    templates = [
        ['object', '-', 'episodic', '->', 'episodic'],
        ['object', '-', 'hyper', '->', 'hyper'],
        ['object', '-', 'simple', '->', 'object'],
        ['hyper', '-', 'episodic', '->', 'episodic'],
        ['hyper', '<-', 'hyper', '-', 'object'],
        ['episodic', '<-', 'episodic', '-', 'object'],
        ['episodic', '<-', 'episodic', '-', 'hyper']
        ]

    for template in templates:
        node_neighbours_to_node_count = kg_model.graph_struct.db_conn.execute_query(
            f"MATCH (a:{template[0]}){template[1]}[rel:{template[2]}]{template[3]}(b:{template[4]}) RETURN count(a), elementId(b)")
        node_neighbours_to_node_count = list(map(lambda item: item['count(a)'], node_neighbours_to_node_count))

        info[f'{template[0]}_neighbours_to_{template[2]}'] = {
            'min': min(node_neighbours_to_node_count),
            'max': max(node_neighbours_to_node_count),
            'mean': np.mean(node_neighbours_to_node_count),
            'median': np.median(node_neighbours_to_node_count),
            'std': np.std(node_neighbours_to_node_count),
            'counts': node_neighbours_to_node_count
        }

    return info

def graph_connectivity_counter(kg_model: KnowledgeGraphModel) -> Dict[str, object]:
    info = dict()

    components_info = kg_model.graph_struct.db_conn.execute_query(
        "CALL algo.unionFind.stream('', '', {}) YIELD nodeId,setId RETURN setId, count(nodeId) as count")

    info['components'] = {item['setId']: item['count'] for item in components_info}

    return info

def get_general_stat(kg_model: KnowledgeGraphModel):

    info = {
        'vector_node': kg_model.embeddings_struct.vectordbs['nodes'].count_items(),
        'vector_triplets': kg_model.embeddings_struct.vectordbs['triplets'].count_items(),
        'graph_counters': kg_model.graph_struct.db_conn.count_items()
    }
    return info

##################################

# статистика по графу

GRAPH_STAT_METRICS = {
    'general': get_general_stat,

    # общее количество вершин
    # - количество вершин типа object
    # - количество вершин типа hyper
    # - количество вершин типа episodic
    "nodes_counter": graph_nodes_counter,

    # общее количество связей
    # - количество связей типа simple
    # - количество связей типа hyper
    # - общее количество связей типа episodic
    #   - количество связей типа episodic c вершинами типа object
    #   - количество связей типа episodic с вершинами типа hyper
    "relations_counter": graph_relations_counter,

    # среднее/медианное/минимальное/максимальное (box-plot) количество object-вершин, которые смежные с episodic-вершинами
    # среднее/медианное/минимальное/максимальное (box-plot) количество hyper-вершин, которые смежные с episodic-вершинами
    # среднее/медианное/минимальное/максимальное (box-plot) количество object-вершин, которые смежные с hyper-вершинами
    # среднее/медианное/минимальное/максимальное (box-plot) количество object-вершин, которые смежные с object-вершинами
    "neighbours_counter": graph_nodes_neighbours_counter,

    # количество компонент связности
    # диаметр каждой компоненты
    # среднее/медианное/минимальное/максимальное (box-plot) значение длины кратчайших путей в каждой компоненте
    #"connectivity_components": graph_connectivity_counter

    # Длина текстовых полей в вершинах
    # - с типом object
    # - с типом hyper
    # - c типом episodic
    # TODO

    # Длина текстовых полей в связях
    # - с типом simple
    # TODO

    # Длина строковых представлений триплетов
    # - c типом связей simple
    # - с типом связей hyper
    # - с типом связей episodic
    #   - с object стартовой вершиной
    #   - с hyper стартовой вершиной
    # TODO
}

##################################

graph_config = joblib.load(GRAPH_MODEL_CONFIG_PATH)
embed_config = joblib.load(EMBEDDINGS_MODEL_CONFIG_PATH)

# !!! IMPORTANT !!!
graph_config.driver_config.db_config.need_to_clear = False
embed_config.nodesdb_driver_config.db_config.need_to_clear = False
embed_config.tripletsdb_driver_config.db_config.need_to_clear = False
# !!! IMPORTANT !!!

##################################

print("graph config: ", graph_config)
print("embeddings config: ",embed_config)

kg_model = KnowledgeGraphModel(
    graph_config=graph_config,
    embeddings_config=embed_config)

print(kg_model.embeddings_struct.vectordbs['nodes'].count_items())
print(kg_model.embeddings_struct.vectordbs['triplets'].count_items())
print(kg_model.graph_struct.db_conn.count_items())

##################################

GRAPH_INFO = dict()
for stat_name, method in tqdm(GRAPH_STAT_METRICS.items()):
    GRAPH_INFO[stat_name] = method(kg_model)

with open(GRAPH_STATS_INFO, 'w', encoding='utf-8') as fd:
    fd.write(json.dumps(GRAPH_INFO, ensure_ascii=False, indent=1))

##################Computing KG health-checks###################

def get_relations_count_per_node(kg_model: KnowledgeGraphModel):
    node_neighbours_to_node_count = kg_model.graph_struct.db_conn.execute_query("MATCH (a)-[rel]-(b) RETURN count(a), elementId(b)")

    values = list(map(lambda item: item['count(a)'], node_neighbours_to_node_count))
    items = list(map(lambda item: (item['count(a)'], item['elementId(b)']), node_neighbours_to_node_count))

    info = {
        'min': min(values),
        'max': max(values),
        'mean': np.mean(values),
        'median': np.median(values),
        'items': items
    }

    return info

def get_episodic_nodes_per_hyper_node(kg_model: KnowledgeGraphModel):
    node_neighbours_to_node_count = kg_model.graph_struct.db_conn.execute_query(
    "MATCH (a:hyper)-[rel:episodic]->(b:episodic) RETURN count(b), elementId(a)")

    values = list(map(lambda item: item['count(b)'], node_neighbours_to_node_count))
    items = list(map(lambda item: (item['count(b)'], item['elementId(a)']), node_neighbours_to_node_count))

    info = {
        'min': min(values),
        'max': max(values),
        'mean': np.mean(values),
        'median': np.median(values),
        'counts': items
    }

    return info


def get_object_nodes_per_episodic_node(kg_model: KnowledgeGraphModel):
    node_neighbours_to_node_count = kg_model.graph_struct.db_conn.execute_query(
    "MATCH (a:object)-[rel:episodic]->(b:episodic) RETURN count(a), elementId(b)")

    values = list(map(lambda item: item['count(a)'], node_neighbours_to_node_count))
    items = list(map(lambda item: (item['count(a)'], item['elementId(b)']), node_neighbours_to_node_count))

    info= {
        'min': min(values),
        'max': max(values),
        'mean': np.mean(values),
        'median': np.median(values),
        'counts': items
    }

    return info

def get_object_nodes_per_hyper_node(kg_model: KnowledgeGraphModel):
    node_neighbours_to_node_count = kg_model.graph_struct.db_conn.execute_query(
    "MATCH (a:object)-[rel:hyper]->(b:hyper) RETURN count(a), elementId(b)")

    values = list(map(lambda item: item['count(a)'], node_neighbours_to_node_count))
    items = list(map(lambda item: (item['count(a)'], item['elementId(b)']), node_neighbours_to_node_count))

    info = {
        'min': min(values),
        'max': max(values),
        'mean': np.mean(values),
        'median': np.median(values),
        'counts': items
    }

    return info

def get_triplet_embds_match(kg_model: KnowledgeGraphModel):
    graph_t_items = kg_model.graph_struct.db_conn.execute_query("MATCH (a)-[rel]->(b) RETURN rel.str_id as str_id, rel")
    graph_t_items = list(map(lambda item: (item['str_id'], item['rel'].type), graph_t_items))

    uniques_graph_t_items = list(set(graph_t_items))

    embds_exist_t_ids = []
    not_matched_embds = defaultdict(lambda: 0)
    for item in tqdm(uniques_graph_t_items):
        str_id, t_type = item
        is_t_exists = kg_model.embeddings_struct.vectordbs['triplets'].item_exist(str_id)

        embds_exist_t_ids.append(is_t_exists)
        if not is_t_exists:
            not_matched_embds[t_type] += 1

    info = {
        'all': len(graph_t_items),
        'unique': len(uniques_graph_t_items),
        'matched_embds': sum(embds_exist_t_ids),
        'not_matched_embds': not_matched_embds
    }

    return info

def get_node_embds_match(kg_model: KnowledgeGraphModel):
    graph_n_items = kg_model.graph_struct.db_conn.execute_query("MATCH (a) RETURN a.str_id as str_id, a")
    graph_n_items = list(map(lambda item: (item['str_id'], list(item['a'].labels)[0]), graph_n_items))
    uniques_graph_n_items = list(set(graph_n_items))

    embds_exist_n_ids = []
    not_matched_embds = defaultdict(lambda: 0)
    for item in tqdm(uniques_graph_n_items):
        str_id, n_tpe = item
        is_n_exists = kg_model.embeddings_struct.vectordbs['nodes'].item_exist(str_id)

        embds_exist_n_ids.append(is_n_exists)
        if not is_n_exists:
            not_matched_embds[n_tpe] += 1

    info = {
        'all': len(graph_n_items),
        'unique': len(uniques_graph_n_items),
        'matched_embds': sum(embds_exist_n_ids),
        'not_matched_embds': not_matched_embds
    }

    return info

##################################

# проверка наличия заданных свойств у графа
GRAPH_HEALTH_CHECKS = {
    # у всех вершин >= 1 инцидентных рёбер
    'nodes_per_node': get_relations_count_per_node,
    # c hyper вершиной связано >= 1 episodic-вершин
    'episodics_per_hyper': get_episodic_nodes_per_hyper_node,
    # c episodic вершиной связано >= 1 object-вершин
    'objects_per_episodic': get_object_nodes_per_episodic_node,
    # c hyper вершиной связано >= 1 object-вершин
    'objects_per_hyper': get_object_nodes_per_hyper_node,
    # для всех трипетов в графе есть векторное представление
    'triplet_embds_count': get_triplet_embds_match,
    # для всех вершин в графе есть векторное представление
    'node_embds_count': get_node_embds_match
}

##################################

HEALTH_CHECKS_INFO = {}
for check_name, method in tqdm(GRAPH_HEALTH_CHECKS.items()):
    HEALTH_CHECKS_INFO[check_name] = method(kg_model)

with open(GRAPH_HEALTH_CHECKS_PATH, 'w', encoding='utf-8') as fd:
    fd.write(json.dumps(HEALTH_CHECKS_INFO, ensure_ascii=False, indent=1))
