from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Union
import numpy as np
import heapq
from time import time
import collections
from copy import deepcopy
from collections import Counter

from .utils import AbstractQuadrupletsRetriever, BaseGraphSearchConfig, get_nodes_path

from ......utils.data_structs import QueryInfo, Quadruplet, NodeType
from ......kg_model import KnowledgeGraphModel
from ......utils.data_structs import create_id_for_node_pair, create_id, NODES_TYPES_MAP
from ......db_drivers.kv_driver.utils import KeyValueDBInstance
from ......db_drivers.kv_driver import KeyValueDriverConfig, KeyValueDriver, KVDBConnectionConfig
from ......utils import Logger
from ......utils.cache_kv import CacheKV, CacheUtils

@dataclass
class AStarMetricsConfig:
    h_metric_name: str = 'ip'
    kvdriver_config: KeyValueDriverConfig = None

    def to_str(self):
        return f"{self.h_metric_name}"

class AStarMetrics:
    def __init__(self, kg_model: KnowledgeGraphModel, accepted_node_types: List[NodeType], log: Logger,
                config: AStarMetricsConfig = AStarMetricsConfig(), verbose: bool = False):
        self.config = config
        self.accepted_node_types = accepted_node_types
        self.kg_model = kg_model

        self.log = log
        self.verbose = verbose

        # костыль
        if self.config.kvdriver_config is not None:
            self.cache = dict()
            if self.config.h_metric_name in ['ip', 'weight_with_short_path',  'avg_weighted_with_short_path']:
                ip_config = deepcopy(config.kvdriver_config)
                ip_config.db_config.db_info['table'] = 'astar_retriever_ip'
                self.cache['ip'] = KeyValueDriver.connect(ip_config)
            if self.config.h_metric_name in ['weight_with_short_path',  'avg_weighted_with_short_path']:
                sp_config = deepcopy(config.kvdriver_config)
                sp_config.db_config.db_info['table'] = 'astar_retriever_bfsshortpath'
                self.cache['bfs_short_path'] = KeyValueDriver.connect(sp_config)

                sp_config = deepcopy(config.kvdriver_config)
                sp_config.db_config.db_info['table'] = 'astar_retriever_weightwithshortpath'
                self.cache['weight_with_short_path'] = KeyValueDriver.connect(sp_config)

                sp_config = deepcopy(config.kvdriver_config)
                sp_config.db_config.db_info['table'] = 'astar_retriever_avgweightedwithshortpath'
                self.cache['avg_weighted_with_short_path'] = KeyValueDriver.connect(sp_config)


        self.cache_info = {
            'dist': {'exist': 0, 'calc': 0},
            'bfs_short_path': {'exist': 0, 'calc': 0},
            'weight_with_short_path': {'exist': 0, 'calc': 0},
            'avg_weighted_with_short_path': {'exist': 0, 'calc': 0}
        }

        self.metrics_map = {
            'ip': self.embeddings_dist,
            'weight_with_short_path': self.weighted_short_path,
            'avg_weighted_with_short_path': self.avg_weighted_short_path,
        }

    def compute_h_metric(self, *args, **kwargs) -> float:
        return self.metrics_map[self.config.h_metric_name](*args, **kwargs)

    def calculate_ip_distance(self, node1_id: str, node2_id: str) -> float:
        dist = 0
        if node1_id != node2_id:
            instances = self.kg_model.embeddings_struct.vectordbs['nodes'].read([node1_id, node2_id], includes=['embeddings'])
            # calculation ip distance
            try:
                dist = 1 - np.dot(instances[0].embedding, instances[1].embedding)
            except IndexError:
                print(instances)
                raise IndexError

        return dist

    def embeddings_dist(self, node1_id: str, node2_id: str, *args, **kwargs) -> float:
        if self.config.kvdriver_config is not None:
            pair_id = create_id_for_node_pair(node1_id, node2_id)
            if self.cache['ip'].item_exist(pair_id):
                #print("exists")
                dist = self.cache['ip'].read([pair_id])[0].value
                self.cache_info['dist']['exist'] += 1
            else:
                #print("calculating")
                dist = self.calculate_ip_distance(node1_id, node2_id)
                self.cache['ip'].create([KeyValueDBInstance(id=pair_id, value=dist)])
                self.cache_info['dist']['calc'] += 1
        else:
            dist = self.calculate_ip_distance(node1_id, node2_id)
            self.cache_info['dist']['calc'] += 1

        return dist

    def compute_short_path(self, node1_id: str, node2_id: str) -> float:
        if self.config.kvdriver_config is not None:
            pair_id = create_id_for_node_pair(node1_id, node2_id)
            if self.cache['bfs_short_path'].item_exist(pair_id):
                #print("exists")
                short_path = self.cache['bfs_short_path'].read([pair_id])[0].value
                self.cache_info['bfs_short_path']['exist'] += 1
            else:
                #print("calculating")
                short_path = self.bfs(node1_id, node2_id)
                self.cache['bfs_short_path'].create([KeyValueDBInstance(id=pair_id, value=short_path)])
                self.cache_info['bfs_short_path']['calc'] += 1
        else:
            short_path = self.bfs(node1_id, node2_id)
            self.cache_info['bfs_short_path']['calc'] += 1

        return short_path

    def weighted_short_path(self, node1_id: str, node2_id: str, *args, **kwargs) -> float:
        pair_id = create_id_for_node_pair(node1_id, node2_id)
        if (self.config.kvdriver_config is not None) and (self.cache['weight_with_short_path'].item_exist(pair_id)):
            #print("exists")
            w_short_path = self.cache['weight_with_short_path'].read([pair_id])[0].value
            self.cache_info['weight_with_short_path']['exist'] += 1
        else:
            #print("calculated")
            short_path_len = self.compute_short_path(node1_id, node2_id)
            w = self.embeddings_dist(node1_id, node2_id)
            w_short_path = w * short_path_len
            self.cache['weight_with_short_path'].create([KeyValueDBInstance(id=pair_id, value=w_short_path)])
            self.cache_info['weight_with_short_path']['calc'] += 1

        return w_short_path

    def avg_weighted_short_path(self, node1_id: str, node2_id: str, parent: Dict[str, str]) -> float:
        pair_id = create_id_for_node_pair(node1_id, node2_id)
        if (self.config.kvdriver_config is not None) and (self.cache['avg_weighted_with_short_path'].item_exist(pair_id)):
            #print("exists")
            avg_w_short_path = self.cache['avg_weighted_with_short_path'].read([pair_id])[0].value
            self.cache_info['avg_weighted_with_short_path']['exist'] += 1
        else:
            #print("calculated")
            nodes_path = get_nodes_path(parent, node1_id)
            acc_dist = 0
            for i in range(len(nodes_path)-1):
                acc_dist += self.embeddings_dist(nodes_path[i], nodes_path[i+1])
            acc_dist += self.embeddings_dist(node1_id, node2_id)

            short_path_len = self.compute_short_path(node1_id, node2_id)
            avg_w_short_path = np.mean(acc_dist) * short_path_len

            self.cache['avg_weighted_with_short_path'].create([KeyValueDBInstance(id=pair_id, value=avg_w_short_path)])
            self.cache_info['avg_weighted_with_short_path']['calc'] += 1

        return avg_w_short_path

    def bfs(self, s_node_id: str, e_node_id: str) -> int:
        visited, queue = set(), collections.deque([s_node_id])
        visited.add(s_node_id)
        D = {s_node_id: 0}
        parent = {s_node_id: None}
        neo4j_queries_counter, passed_nodes_counter = 0, 0
        while queue:
            #print(len(queue))
            vertex = queue.popleft()
            neighbours = self.kg_model.graph_struct.db_conn.get_adjecent_nids(vertex, self.accepted_node_types)
            neo4j_queries_counter += 1
            for neighbour in neighbours:

                if neighbour == parent[vertex]:
                    # пропускаем вершину, из которой пришли
                    continue

                if neighbour not in visited:
                    parent[neighbour] = vertex
                    D[neighbour] = D[vertex] + 1
                    visited.add(neighbour)
                    passed_nodes_counter += 1

                    if self.config.kvdriver_config is not None:
                        # кешируем кратчайший bfs-путь от s_node_id-стартовой до текущей вершины
                        pair_id = create_id_for_node_pair(s_node_id, neighbour)
                        if not self.cache['bfs_short_path'].item_exist(pair_id):
                            self.cache['bfs_short_path'].create([KeyValueDBInstance(id=pair_id, value=D[neighbour])])
                            self.cache_info['bfs_short_path']['calc'] += 1

                        # кешируем кратчайший bfs-путь от vertex-вершины до его соседа (путь равен 1)
                        pair_id = create_id_for_node_pair(vertex, neighbour)
                        if not self.cache['bfs_short_path'].item_exist(pair_id):
                            self.cache['bfs_short_path'].create([KeyValueDBInstance(id=pair_id, value=1)])
                            self.cache_info['bfs_short_path']['calc'] += 1

                    if neighbour == e_node_id:
                        self.log(f"bfs end-node found!", verbose=self.verbose)
                        self.log(f"bfs graph-db queries: {neo4j_queries_counter}", verbose=self.verbose)
                        self.log(f"passed nodes: {passed_nodes_counter}", verbose=self.verbose)

                        # костыль
                        self.cache_info['bfs_short_path']['calc'] -= 1

                        # кешируем кратчайшие bfs-пути от e_node_id-вершины до вершин,
                        # которые были в кратчайшем пути между s_node_id- и e_node_id-вершинами
                        reverse_nodes_path = get_nodes_path(parent, neighbour)
                        for i in range(1,len(reverse_nodes_path)-1):
                            pair_id = create_id_for_node_pair(reverse_nodes_path[i], neighbour)
                            if not self.cache['bfs_short_path'].item_exist(pair_id):
                                self.cache['bfs_short_path'].create([KeyValueDBInstance(id=pair_id, value=i)])
                                self.cache_info['bfs_short_path']['calc'] += 1

                        return D[neighbour]

                    queue.append(neighbour)

        # между вершинами нет пути
        self.log(f"bfs not found end-node", verbose=self.verbose)
        self.log(f"bfs graph-db queries: {neo4j_queries_counter}", verbose=self.verbose)
        self.log(f"passed nodes: {passed_nodes_counter}", verbose=self.verbose)

        INF_VALUE = 1000001 # специальное значение, которое говорит, что между вершинами нет пути
        if self.config.kvdriver_config is not None:
            pair_id = create_id_for_node_pair(s_node_id, e_node_id)
            if not self.cache['bfs_short_path'].item_exist(pair_id):
                self.cache['bfs_short_path'].create([KeyValueDBInstance(id=pair_id, value=INF_VALUE)])

        return INF_VALUE

@dataclass
class AStarGraphSearchConfig(BaseGraphSearchConfig):
    metrics_config: AStarMetricsConfig = field(default_factory=lambda: AStarMetricsConfig())
    max_depth: int = 10
    max_passed_nodes: int = 500
    accepted_node_types: List[NodeType] = field(default_factory=lambda:[NodeType.object, NodeType.hyper, NodeType.episodic, NodeType.time])
    cache_table_name: str = 'qa_astar_q_retriever_cache'

    def to_str(self):
        str_accepted_nodes = ";".join(sorted(list(map(lambda v: v.value, self.accepted_node_types))))
        return f"{self.metrics_config.to_str()}|{self.max_depth}|{self.max_passed_nodes}|{str_accepted_nodes}"

class AStarGraphSearch:
    def __init__(self, kg_model: KnowledgeGraphModel, log: Logger, search_config: AStarGraphSearchConfig = AStarGraphSearchConfig(),
                 verbose: bool = False) -> None:
        self.log = log
        self.verbose = verbose
        self.config = search_config
        self.kg_model = kg_model
        self.metrics = AStarMetrics(
            kg_model=kg_model, accepted_node_types=self.config.accepted_node_types,
            log=self.log, config=self.config.metrics_config, verbose=verbose)

    def search_path(self, start_node_id: str, end_node_id: str) -> Tuple[List[str], List[str], Dict[str, int], Dict[str, str], str]:
        """Реализация A*-алгоритма. Источник: https://www.redblobgames.com/pathfinding/a-star/implementation.html."""
        frontier = []
        heapq.heappush(frontier, (0, start_node_id))
        parent = {start_node_id: None}
        cost_so_far = {start_node_id: 0}
        D = {start_node_id: 0}

        spare_closest_node_id = start_node_id
        passed_nodes_counter = 0
        while len(frontier):
            current_node_id = heapq.heappop(frontier)[1]
            passed_nodes_counter += 1

            if (self.config.max_passed_nodes >= 0) and (passed_nodes_counter >= self.config.max_passed_nodes):
                self.log("PASSED LIMIT OF MAX NODES", verbose=self.verbose)
                break

            if (self.config.max_depth >= 0) and (D[current_node_id] >= self.config.max_depth):
                self.log("PASSED MAX DEPTH LIMIT", verbose=self.verbose)
                continue

            # Сохраняем промежуточную вершину, до которой есть путь.
            # Если не будет найден путь до end_node, то будет использован путь до spare_closest_node
            spare_closest_node_id = current_node_id

            #
            if current_node_id == end_node_id:
                self.log("FOUND END-NODE", verbose=self.verbose)
                break

            adj_nodes = self.kg_model.graph_struct.db_conn.get_adjecent_nids(current_node_id, self.config.accepted_node_types)

            for adj_n_id in adj_nodes:

                if adj_n_id == parent[current_node_id]:
                    # пропускаем вершину, из которой пришли
                    continue

                new_cost = cost_so_far[current_node_id] + 1 # работаем с невзвешенным графом
                if (adj_n_id not in cost_so_far) or (new_cost < cost_so_far[adj_n_id]):
                    parent[adj_n_id] = current_node_id
                    D[adj_n_id] = D[current_node_id] + 1

                    cost_so_far[adj_n_id] = new_cost
                    priority = new_cost + self.metrics.compute_h_metric(adj_n_id, end_node_id, parent)
                    heapq.heappush(frontier, (priority, adj_n_id))

        self.log(f"start-spare node path len: {D[spare_closest_node_id]}" if end_node_id not in parent else f"start-end node path len: {D[end_node_id]}", verbose=self.verbose)
        self.log(f"astar queries: {passed_nodes_counter}", verbose=self.verbose)
        return cost_so_far, frontier, D, parent, spare_closest_node_id

class AStarTripletsRetriever(AbstractQuadrupletsRetriever, CacheUtils): # Keeping class name for configs.py compatibility
    def __init__(self, kg_model: KnowledgeGraphModel, log: Logger, search_config: Union[AStarGraphSearchConfig, Dict] = AStarGraphSearchConfig(),
                 cache_kvdriver_config: KeyValueDriverConfig = None, verbose: bool = False) -> None:
        self.log = log
        self.verbose = verbose
        self.kg_model = kg_model

        if type(search_config) is dict:
            if 'accepted_node_types' in search_config:
                search_config['accepted_node_types'] = list(map(lambda k: NODES_TYPES_MAP[k], search_config['accepted_node_types']))

            if 'metrics_config' in search_config:
                search_config['metrics_config'] = AStarMetricsConfig(**search_config['metrics_config'])
                search_config['metrics_config'].kvdriver_config = KeyValueDriverConfig(
                    **search_config['metrics_config'].kvdriver_config)
                search_config['metrics_config'].kvdriver_config.db_config = KVDBConnectionConfig(
                    **search_config['metrics_config'].kvdriver_config.db_config)

                if search_config['metrics_config'].kvdriver_config.db_vendor == 'mixed_kv':
                    search_config['metrics_config'].kvdriver_config.db_config.params['redis_config'] = KVDBConnectionConfig(
                        **search_config['metrics_config'].kvdriver_config.db_config.params['redis_config'])
                    search_config['metrics_config'].kvdriver_config.db_config.params['mongo_config'] = KVDBConnectionConfig(
                        **search_config['metrics_config'].kvdriver_config.db_config.params['mongo_config'])

            search_config = AStarGraphSearchConfig(**search_config)
        self.config = search_config

        self.graph_searcher = AStarGraphSearch(kg_model, log, search_config, verbose)

        if cache_kvdriver_config is not None and self.config.cache_table_name is not None:
            cache_config = deepcopy(cache_kvdriver_config)
            cache_config.db_config.db_info['table'] = self.config.cache_table_name
            self.cachekv = CacheKV(cache_config)
        else:
            self.cachekv = None

    def get_cache_key(self, query_info: QueryInfo) -> List[object]:
        return [self.config.to_str(), query_info.to_str()]

    @CacheUtils.cache_method_output
    def get_relevant_quadruplets(self, query_info: QueryInfo) -> List[Quadruplet]:
        self.log("START KNOWLEDGE RETRIEVING ...", verbose=self.verbose)
        self.log("RETRIEVER: AStarTripletsRetriever", verbose=self.verbose)
        self.log(f"BASE_QUESTION ID: {create_id(query_info.query)}", verbose=self.verbose)
        self.log(f"BASE_QUESTION: {query_info.query}", verbose=self.verbose)

        nodes_ids = []
        for node in query_info.linked_nodes:
            if node.id not in nodes_ids:
                nodes_ids.append(node.id)
        unique_nodes_pairs = set()

        all_pair_nodes_counter = sum(list(range(len(nodes_ids))))
        pair_nodes_counter = 0
        if len(nodes_ids) > 1:
            self.log("pair nodes calculation...", verbose=self.verbose)
            for i in range(len(nodes_ids)-1):
                start_node = nodes_ids[i]
                for j in range(i+1, len(nodes_ids)):
                    pair_nodes_counter += 1
                    self.log(f"{all_pair_nodes_counter} / {pair_nodes_counter}", verbose=self.verbose)
                    end_node = nodes_ids[j]

                    s_time = time()
                    _, _, _, parent, spare_closest_node = self.graph_searcher.search_path(start_node, end_node)
                    self.log(f"search elapsed_time: {time() - s_time}", verbose=self.verbose)

                    s_time = time()
                    nodes_path = get_nodes_path(
                        parent, spare_closest_node if end_node not in parent else end_node)
                    self.log(f"get_path elapsed_time: {time() - s_time}", verbose=self.verbose)

                    # Сохраняем только уникальные пары вершин
                    s_time = time()
                    unique_nodes_pairs.update([(nodes_path[i], nodes_path[i+1]) for i in range(len(nodes_path)-1)] if len(nodes_path) > 1 else [])
                    self.log(f"saving_nodes elapsed_time: {time() - s_time}", verbose=self.verbose)

                    self.log(self.graph_searcher.metrics.cache_info, verbose=self.verbose)

        # Сохраняем только уникальные квадруплеты
        self.log("pair nodes formating...", verbose=self.verbose)
        s_time = time()
        unique_quadruplets = dict()
        for nodes_pair in unique_nodes_pairs:
            # Updating method call
            quadruplets = self.kg_model.graph_struct.db_conn.get_quadruplets(*nodes_pair)
            for quadruplet in quadruplets:
                unique_quadruplets[quadruplet.id] = quadruplet # Key by Quadruplet ID? Or Relation ID like before?
                # Before: unique_triplets[triplet.relation.id]
                # With Quadruplets, ID should be on the Quadruplet itself ideally.
                # Assuming Quadruplet has 'id'. Default to 'id'. 
                # If Quadruplet inherits or is similar to Triplet, I should check internal structure.
                # In data_structs.py, I updated Quadruplet to have an ID.

        unique_quadruplets = list(unique_quadruplets.values())

        self.log(f"Распределение типов связей в наборе извлечённых квадруплетов: {Counter([quadruplet.relation.type for quadruplet in unique_quadruplets])}", verbose=self.verbose)
        self.log(f"foramting queries: {len(unique_nodes_pairs)}", verbose=self.verbose)
        self.log(f"formating elapsed_time: {time() - s_time}", verbose=self.verbose)

        return unique_quadruplets
