####
# Author:   Mikhail Menschikov
# Email:    menshikov.mikhail.2001@gmail.com
# Created:  11.02.2025
####

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Set, Union
from collections import defaultdict
from collections import Counter
from time import time
from copy import deepcopy, copy
import numpy as np

from .utils import AbstractQuadrupletsRetriever, BaseGraphSearchConfig

from ......utils.data_structs import QueryInfo, Quadruplet, NodeType
from ......kg_model import KnowledgeGraphModel
from ......utils.data_structs import create_id, NODES_TYPES_MAP
from ......utils import Logger
from ......db_drivers.vector_driver.utils import VectorDBInstance
from ......utils.cache_kv import CacheKV, CacheUtils
from ......db_drivers.kv_driver import KeyValueDriverConfig, KVDBConnectionConfig

@dataclass
class TraversingPath:
    path: List[Tuple[str,str,str]]
    unique_nids: Set[str]
    unique_qids: Set[str]
    accum_score: float

@dataclass
class TraversedPath:
    path: List[Tuple[str,str,str]]
    score: float

@dataclass
class GraphBeamSearchConfig(BaseGraphSearchConfig):
    # Максимальная глубина построенных путей
    max_depth: int = 10
    # Максимальное количество построенных путей
    max_paths: int = 50
    # Если True, то пути могут пересекаться сами с собой по вершинам, иначе False
    same_path_intersection_by_node: bool = True
    # Если True, то разные пути могут пересекаться по вершинам, иначе False
    diff_paths_intersection_by_node: bool = True
    # Если True, то разные пути могут пересекаться по связям, иначе False
    diff_paths_intersection_by_rel: bool = True
    # Гиперпараметр, отвечающий за учёт длины построенного пути при усреднении его ценности (релевантности).
    # См. calculate_quadruplet_score- и calculate_path_score-методы.
    mean_alpha: float = 0.75
    # Типы вершины, которые можно обходить во время построения путей
    accepted_node_types: List[NodeType] = field(default_factory=lambda:[NodeType.object , NodeType.hyper, NodeType.episodic])
    # Способ финальной фильтрации полученного набора путей.
    final_sorting_mode: str = 'mixed' # 'ended_first' | 'mixed' | 'continuous_first'
    cache_table_name: str = 'qa_beamsearch_q_retriever_cache'

    def to_str(self):
        str_bools = f"{self.same_path_intersection_by_node};{self.diff_paths_intersection_by_node};{self.diff_paths_intersection_by_rel}"
        str_accepted_nodes = ";".join(sorted(list(map(lambda v: v.value, self.accepted_node_types))))
        return f"{self.max_depth}|{self.max_paths}|{str_bools}|{self.mean_alpha}|{str_accepted_nodes}|{self.final_sorting_mode}"


class BeamSearchTripletsRetriever(AbstractQuadrupletsRetriever, CacheUtils): # Keeping class name for configs.py compatibility
    def __init__(self, kg_model: KnowledgeGraphModel, log: Logger,
                 search_config: Union[GraphBeamSearchConfig, Dict] = GraphBeamSearchConfig(),
                 cache_kvdriver_config: KeyValueDriverConfig = None, verbose: bool = False) -> None:
        self.log = log
        self.verbose = verbose
        self.kg_model = kg_model

        if type(search_config) is dict:
            if 'accepted_node_types' in search_config:
                search_config['accepted_node_types'] = list(map(lambda k: NODES_TYPES_MAP[k], search_config['accepted_node_types']))
            search_config = GraphBeamSearchConfig(**search_config)
        self.config = search_config

        if cache_kvdriver_config is not None and self.config.cache_table_name is not None:
            cache_config = deepcopy(cache_kvdriver_config)
            cache_config.db_config.db_info['table'] = self.config.cache_table_name
            self.cachekv = CacheKV(cache_config)
        else:
            self.cachekv = None

    def get_cache_key(self, query: str, node_id: str) -> List[object]:
        return [self.config.to_str(), query, node_id]

    def calculate_path_score(self, path_len: int, accum_score: float) -> float:
        return accum_score / pow(path_len-1, self.config.mean_alpha)

    @staticmethod
    def calculate_quadruplet_score(raw_score: float, max_score_value: float = 10e+5) -> float:
        # Note: в качества скора используется метрика косинусного расстояния [distance]
        # (её нужно вычесть из единицы, чтобы получить метрику косинусной близоси [similarity])

        if type(raw_score) in [int, str] or raw_score is None:
            raise ValueError(raw_score, type(raw_score))

        if raw_score < 0.0 or raw_score > 1.0:
            raise ValueError(raw_score)

        if np.abs(1.0 - raw_score) < 10e-10:
            return max_score_value

        return -np.log(1.0 - raw_score)

    def get_available_nids(self, base_nid: str, cur_path_idx: int,
            traversing_paths: List[TraversingPath], prev_nid: str = None) -> List[str]:
        if type(base_nid) is not str:
            raise ValueError(f"base_nid: {base_nid} {type(base_nid)}")

        adj_nids = self.kg_model.graph_struct.db_conn.get_adjecent_nids(base_nid, self.config.accepted_node_types)
        adj_nids = set(adj_nids)
        if prev_nid is not None:
            if type(prev_nid) is not str:
                raise ValueError(f"prev_nid: {prev_nid} {type(prev_nid)}")
            adj_nids.discard(prev_nid)

        if not self.config.same_path_intersection_by_node:
            adj_nids.difference_update(traversing_paths[cur_path_idx].unique_nids)

        if not self.config.diff_paths_intersection_by_node:
            for i in range(len(traversing_paths)):
                if i != cur_path_idx:
                    adj_nids.difference_update(traversing_paths[i].unique_nids)

        return list(adj_nids)

    def get_available_rinfo(
            self, base_nid: str, adj_nids: List[str], cur_path_idx: int,
            traversing_paths: List[TraversingPath]) -> Tuple[Dict[str, str], Dict[str, List[str]]]:
        if type(base_nid) is not str:
            raise ValueError(f"base_nid: {base_nid} {type(base_nid)}")

        shared_q_info = dict()
        rids_to_qids_map = defaultdict(list)
        for adj_nid in adj_nids:
            # Updating id_type to 'quadruplet' logic (or 'both' using t_id)
            tmp_shared_ids = self.kg_model.graph_struct.db_conn.get_nodes_shared_ids(base_nid, adj_nid, id_type='both')
            # Assuming 't_id' is the quadruplet ID
            tmp_ids_map = {item['t_id']: item['r_id'] for item in tmp_shared_ids}
            cur_qids = set(tmp_ids_map.keys())

            # shared_q_info stores q_id -> adj_nid
            tmp_shared_ids = cur_qids.difference(traversing_paths[cur_path_idx].unique_qids)

            if not self.config.diff_paths_intersection_by_rel:
                for i in range(len(traversing_paths)):
                    if i != cur_path_idx:
                        tmp_shared_ids.difference_update(traversing_paths[i].unique_qids)

            for q_id in list(tmp_shared_ids):
                shared_q_info[q_id] = adj_nid
                rids_to_qids_map[tmp_ids_map[q_id]].append(q_id)

        return shared_q_info, rids_to_qids_map

    def get_quadruplet_scores(self, query_vinstance: VectorDBInstance, shared_q_info: Dict[str, str],
                           rids_to_qids_map: Dict[str, List[str]], batch_size:int=512) -> List[Tuple[str, str, float]]:
        r_ids = list(rids_to_qids_map.keys())
        extended_scores_info = []

        batches = len(r_ids) // batch_size
        batches += 1 if len(r_ids) % batch_size != 0 else 0

        for step in range(batches):
            cur_rids_batch = r_ids[step * batch_size: (step+1)* batch_size]

            # Use 'quadruplets' collection
            scored_rels = self.kg_model.embeddings_struct.vectordbs['quadruplets'].retrieve(
                [query_vinstance], n_results=len(cur_rids_batch), includes=[], subset_ids=cur_rids_batch)[0]

            for raw_score, quadruplet_info in scored_rels:
                cur_r_id, cur_q_score = (quadruplet_info.id, BeamSearchTripletsRetriever.calculate_quadruplet_score(raw_score))
                if cur_r_id in rids_to_qids_map: # Should be, given subset_ids
                    for q_id in rids_to_qids_map[cur_r_id]:
                        extended_scores_info.append((q_id, shared_q_info[q_id], cur_q_score))

        return extended_scores_info

    @staticmethod
    def extend_tpath(pinfo: TraversingPath, quadruplet_scores: List[Tuple[str, str, float]]) -> List[TraversingPath]:

        if len(pinfo.path) < 1:
            raise ValueError(pinfo)

        new_tpaths = []
        for q_id, new_nid, q_score in quadruplet_scores:
            ext_trpath = deepcopy(pinfo)

            ext_trpath.path.append((ext_trpath.path[-1][2], q_id, new_nid))
            ext_trpath.unique_nids.add(new_nid)

            if q_id in ext_trpath.unique_qids:
                raise ValueError(f"Квадруплет с id '{q_id}' уже существует в пути {ext_trpath}. Все квадруплеты должны быть уникальными.")

            ext_trpath.unique_qids.add(q_id)
            ext_trpath.accum_score += q_score

            new_tpaths.append(ext_trpath)

        return new_tpaths

    def filter_paths(self, ended_paths: List[TraversedPath],
                     continuous_paths: List[TraversedPath]) -> List[TraversedPath]:
        filtered_paths = []
        if self.config.final_sorting_mode == 'continuous_first':
            filtered_paths += sorted(continuous_paths, key=lambda pinfo:pinfo.score)[:self.config.max_paths]
            if len(filtered_paths) < self.config.max_paths:
                num_missed_paths = self.config.max_paths - len(filtered_paths)
                filtered_paths += sorted(ended_paths, key=lambda pinfo:pinfo.score)[:num_missed_paths]

        if self.config.final_sorting_mode == 'ended_first':
            filtered_paths += sorted(ended_paths, key=lambda pinfo: pinfo.score)[:self.config.max_paths]
            if len(filtered_paths) < self.config.max_paths:
                num_missed_paths = self.config.max_paths - len(filtered_paths)
                filtered_paths += sorted(continuous_paths, key=lambda pinfo:pinfo.score)[:num_missed_paths]

        elif self.config.final_sorting_mode == 'mixed':
            filtered_paths = sorted(continuous_paths + ended_paths, key=lambda pinfo:pinfo.score)[:self.config.max_paths]

        else:
            raise KeyError

        return filtered_paths

    def graph_beamsearch(self, query: str, node_id: str) -> List[TraversedPath]:
        traversing_paths = [TraversingPath(
            path=[(None, None, node_id)], unique_nids={node_id},
            unique_qids=set(), accum_score=0.0)]
        ended_paths = []

        query_emb = self.kg_model.embeddings_struct.embedder.encode_queries([query])[0]
        query_vinstance = VectorDBInstance(embedding=query_emb)

        for cur_depth in range(self.config.max_depth):
            self.log(f"Текущая глубина обхода графа: {cur_depth}", verbose=self.verbose)
            self.log(f"Имеющееся количество незавершившихся путей: {len(traversing_paths)}", verbose=self.verbose)
            path_candidates = list()

            if len(traversing_paths) < 1:
                self.log(f"Больше некуда двигаться. Прекращаем обход графа", verbose=self.verbose)
                break

            opext_s_time = time()
            for i in range(len(traversing_paths)):
                curp_s_time = time()
                cur_path_info = traversing_paths[i]
                prev_nid, tail_nid = cur_path_info.path[-1][0], cur_path_info.path[-1][2]
                self.log(f"Информация по текущему пути:\n* номер: {i}\n* len: {len(cur_path_info.path)}\n* tail_nid: {tail_nid}\n* prev_nid: {prev_nid}", verbose=self.verbose)

                adj_nids = self.get_available_nids(tail_nid, i, traversing_paths, prev_nid=prev_nid)
                self.log(f"Смежные вершины: {len(adj_nids)}\n", verbose=self.verbose)

                if len(adj_nids) < 1:
                    self.log("У tail-вершины нет смежных вершин. Считаем путь завершившимся.", verbose=self.verbose)
                    if len(cur_path_info.path) > 1:
                        ended_paths.append(TraversedPath(path=deepcopy(cur_path_info.path), score=self.calculate_path_score(
                            len(cur_path_info.path), cur_path_info.accum_score)))
                    continue

                shared_q_info, rids_to_qids_map = self.get_available_rinfo(tail_nid, adj_nids, i, traversing_paths)
                if len(shared_q_info) < 1:
                    self.log("Нет доступных связей для соединения tail-вершины с новой вершиной, Считаем путь завершившимся.", verbose=self.verbose)
                    if len(cur_path_info.path) > 1:
                        ended_paths.append(TraversedPath(path=deepcopy(cur_path_info.path), score=self.calculate_path_score(
                            len(cur_path_info.path), cur_path_info.accum_score)))
                    continue

                quadruplet_scores = self.get_quadruplet_scores(query_vinstance, shared_q_info, rids_to_qids_map)
                new_tpaths = BeamSearchTripletsRetriever.extend_tpath(traversing_paths[i], quadruplet_scores)
                self.log(f"Количество новых расширенных путей для текущего пути (до урезания): {len(new_tpaths)}", verbose=self.verbose)
                sorted_new_tpaths = sorted(new_tpaths, key=lambda pinfo: pinfo.accum_score)
                path_candidates += sorted_new_tpaths[:self.config.max_paths]
                self.log(f"Текущее количество путей-кандидатов: {len(path_candidates)}", verbose=self.verbose)
                curp_e_time = time()
                self.log(f"Затраченное время на расширение текущего пути: {curp_e_time - curp_s_time} сек.", verbose=self.verbose)

            opext_e_time = time()

            self.log(f"Количество найденных путей-кандидатов (до урезаний): {len(path_candidates)}", verbose=self.verbose)
            self.log(f"Затраченное суммарное время на текущую итерацию: {opext_e_time-opext_s_time} сек.", verbose=self.verbose)

            ordered_candidates = sorted(path_candidates, key=lambda pinfo: pinfo.accum_score)
            traversing_paths = ordered_candidates[:self.config.max_paths]

        self.log(f"Достигнут предел по глубине обхода графа: {self.config.max_depth}", verbose=self.verbose)

        flt_s_time = time()
        continuous_paths = []
        for path_info in traversing_paths:
            continuous_paths.append(
                TraversedPath(path=path_info.path, score=self.calculate_path_score(
                    len(path_info.path), path_info.accum_score)))
        filtered_paths = self.filter_paths(ended_paths, continuous_paths)
        flt_e_time = time()
        self.log(f"Финальное количество найденных путей: {len(filtered_paths)}", verbose=self.verbose)
        self.log(f"Затраченнное время на фильтрацию путей: {flt_e_time-flt_s_time} сек.", verbose=self.verbose)

        return filtered_paths

    @CacheUtils.cache_method_output
    def search(self, query: str, node_id: str) -> List[Quadruplet]:
        paths_info = self.graph_beamsearch(query, node_id)

        uniques_qids = set()
        for p_info in paths_info:
            for quadruplet_info in p_info.path[1:]:
                uniques_qids.add(quadruplet_info[1])

        extracted_quadruplets = self.kg_model.graph_struct.db_conn.read(list(uniques_qids))
        return extracted_quadruplets

    def get_relevant_quadruplets(self, query_info: QueryInfo) -> List[Quadruplet]:
        self.log("START KNOWLEDGE RETRIEVING ...", verbose=self.verbose)
        self.log("RETRIEVER: BeamSearchQuadrupletsRetriever", verbose=self.verbose)
        self.log(f"BASE_QUESTION ID: {create_id(query_info.query)}", verbose=self.verbose)
        self.log(f"BASE_QUESTION: {query_info.query}", verbose=self.verbose)

        node_ids = set([node.id for node in query_info.linked_nodes])
        self.log(f"Вершины, для которых будет запущейн BeamSearch: {node_ids}", verbose=self.verbose)

        unique_quadruplets = dict()
        for node_id in node_ids:
            self.log(f"Запускаем BeamSearch по вершине с id: {node_id}", verbose=self.verbose)
            tmp_quadruplets = self.search(query_info.query, node_id)
            self.log(f"Количество извлечённых квадруплетов для данной вершины: {len(tmp_quadruplets)}", verbose=self.verbose)
            unique_quadruplets.update({quadruplet.id: quadruplet for quadruplet in tmp_quadruplets})

        self.log(f"Суммарное количество уникальных (по строковому представлению) извлечённых квадруплетов: {len(unique_quadruplets)}", verbose=self.verbose)
        self.log(f"Распределение типов связей в наборе извлечённых квадруплетов: {Counter([quadruplet.relation.type for quadruplet in unique_quadruplets.values()])}", verbose=self.verbose)

        return list(unique_quadruplets.values())
