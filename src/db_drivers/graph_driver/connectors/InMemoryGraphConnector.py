from typing import List, Dict, Union
from collections import defaultdict
import gc
from time import time
import hashlib

from ..utils import GraphDBConnectionConfig, AbstractGraphDatabaseConnection
from ....utils import Quadruplet, NodeType
from ....utils.data_structs import RelationType, Node

DEFAULT_INMEMORYGRAPH_CONFIG = GraphDBConnectionConfig()

class InMemoryGraphConnector(AbstractGraphDatabaseConnection):

    def __init__(self, config: GraphDBConnectionConfig = DEFAULT_INMEMORYGRAPH_CONFIG) -> None:
        self.config = config

    def open_connection(self) -> None:
        self.edges = defaultdict(set)
        self.adjacent_nodes = defaultdict(set)

        self.nodes = dict()
        self.quadruplets = dict()

        self.strid_relation_index = defaultdict(set)
        self.strid_nodes_index = defaultdict(set)
        self.qid_quadruplets_index = defaultdict(set)

    def is_open(self) -> bool:
        need_to_exist = [
            'edges', 'adjacent_nodes', 'nodes', 'quadruplets',
            'strid_nodes_index', 'str_relation_index', 'qid_quadruplets_index']
        condition = True
        for field in need_to_exist:
            condition = condition and hasattr(self, field)
        return condition

    def close_connection(self) -> None:
        del self.edges
        del self.adjacent_nodes

        del self.nodes
        del self.quadruplets

        del self.strid_nodes_index
        del self.strid_relation_index
        del self.qid_quadruplets_index
        gc.collect()

    def generate_id(self, seed: str = None) -> str:
        return hashlib.md5((str(time()) if seed is None else seed).encode()).hexdigest()

    def create(self, quadruplets: List[Quadruplet], creation_info: Dict[int,Dict[str,bool]] = dict()) -> None:
        # quadruplet-ids checking
        for quadruplet in quadruplets:
            if type(quadruplet.id) is not str:
                raise ValueError
        unique_ids = set(map(lambda quadruplet: quadruplet.id, quadruplets))
        if len(quadruplets) != len(unique_ids):
            raise ValueError

        for i, quadruplet in enumerate(quadruplets):
            cur_info = creation_info.get(i, None)

            #
            if cur_info is None or cur_info['s_node']:
                new_node_id = self.generate_id()
                self.strid_nodes_index[quadruplet.start_node.id].add(new_node_id)
                self.nodes[new_node_id] = quadruplet.start_node

            if cur_info is None or cur_info['e_node']:
                new_node_id = self.generate_id()
                self.strid_nodes_index[quadruplet.end_node.id].add(new_node_id)
                self.nodes[new_node_id] = quadruplet.end_node

            # Time node handling? For in-memory, we might just store it in quadruplet or add node if we want.
            # Following the Neo4j pattern, we should probably add it as a node if it exists.
            if (cur_info is None or cur_info.get('t_node', False)) and quadruplet.time:
                new_node_id = self.generate_id()
                self.strid_nodes_index[quadruplet.time.id].add(new_node_id)
                self.nodes[new_node_id] = quadruplet.time


            sn_ids = list(self.strid_nodes_index[quadruplet.start_node.id])
            en_ids = list(self.strid_nodes_index[quadruplet.end_node.id])

            for sn_id in sn_ids:
                for en_id in en_ids:
                    t_id = self.generate_id()
                    self.qid_quadruplets_index[quadruplet.id].add(t_id)
                    self.quadruplets[t_id] = quadruplet

                    r_id = self.generate_id()
                    self.strid_relation_index[quadruplet.relation.id].add(r_id)

                    self.edges[sn_id].add(t_id)
                    self.adjacent_nodes[sn_id].add(en_id)

                    self.edges[en_id].add(t_id)
                    self.adjacent_nodes[en_id].add(sn_id)


    def read(self, ids: List[str]) -> List[Quadruplet]:
        quadruplets = []
        for id in ids:
            if type(id) is not str:
                raise ValueError
            t_ids = self.qid_quadruplets_index[id]
            quadruplets += list(map(lambda t_id: self.quadruplets[t_id], list(t_ids)))
        return quadruplets

    def update(self, items: List[Quadruplet]) -> None:
        # TODO
        pass

    def delete(self, ids: List[str], delete_info: Dict[int,Dict[str,bool]] = dict()) -> None:
        for id in ids:
            if type(id) is not str:
                raise ValueError

        for i, q_id in enumerate(ids):
            cur_info = delete_info.get(i, None)

            internal_q_ids = self.qid_quadruplets_index[q_id]

            for internal_q_id in internal_q_ids:
                matched_quadruplet = self.quadruplets[internal_q_id]

                internal_snode_ids = list(self.strid_nodes_index[matched_quadruplet.start_node.id])
                internal_enode_ids = list(self.strid_nodes_index[matched_quadruplet.end_node.id])

                nodes_id_to_delete = set()
                for sn_id in internal_snode_ids:
                    self.edges[sn_id].remove(internal_q_id)
                    self.adjacent_nodes[sn_id].difference_update(internal_enode_ids)

                    if (cur_info is None) or cur_info['s_node']:
                        #assert len(self.edges[sn_id]) == 0
                        #assert self.adjacent_nodes[sn_id] == 0
                        del self.nodes[sn_id]
                        nodes_id_to_delete.add(sn_id)

                if ((cur_info is None) or cur_info['s_node']) and len(nodes_id_to_delete):
                    self.strid_nodes_index[matched_quadruplet.start_node.id].difference_update(nodes_id_to_delete)

                nodes_id_to_delete = set()
                for en_id in internal_enode_ids:
                    self.edges[en_id].remove(internal_q_id)
                    self.adjacent_nodes[en_id].difference_update(internal_snode_ids)

                    if (cur_info is None) or cur_info['e_node']:
                        #assert len(self.edges[en_id]) == 0
                        #assert self.adjacent_nodes[en_id] == 0
                        del self.nodes[en_id]
                        nodes_id_to_delete.add(en_id)

                if ((cur_info is None) or cur_info['e_node']) and len(nodes_id_to_delete):
                    self.strid_nodes_index[matched_quadruplet.end_node.id].difference_update(nodes_id_to_delete)

                self.strid_relation_index[matched_quadruplet.relation.id].pop()
                del self.quadruplets[internal_q_id]

            del self.qid_quadruplets_index[q_id]


    def read_by_name(self, name: str, object_type: Union[RelationType, NodeType], object: str = 'relation') -> List[Union[Quadruplet, Node]]:
        # Note: Реализован наивный способ поиска элементов в графе
        # (алгоритмическая сложность O(n), где n - количество квадруплетов/вершин в графе)

        if type(object_type) not in [RelationType, NodeType]:
            raise ValueError

        if type(name) is not str:
            raise ValueError

        if len(name) < 1:
            raise ValueError

        if object == 'relation':
            formated_output =  [quadruplet for quadruplet in self.quadruplets.values() if quadruplet.relation.type == object_type and quadruplet.relation.name == name]
        elif object == 'node':
            formated_output =  [node for node in self.nodes.values() if node.type == object_type and node.name == name]
        else:
            raise ValueError

        return formated_output

    def get_adjecent_nids(self, base_node_id: str,
            accepted_n_types: List[NodeType] = [NodeType.object, NodeType.hyper, NodeType.episodic]) -> List[str]:
        if type(base_node_id) is not str:
            raise ValueError

        node_db_ids = self.strid_nodes_index.get(base_node_id, [])
        adjanced_nodes_db_ids = []
        for node_id in node_db_ids:
            adjanced_nodes_db_ids += list(self.adjacent_nodes[node_id])

        filtered_adj_n_dbids = list(filter(lambda n_db_id: self.nodes[n_db_id].type in accepted_n_types, adjanced_nodes_db_ids))
        nodes_str_ids = list(map(lambda db_n_id: self.nodes[db_n_id].id, filtered_adj_n_dbids))
        return nodes_str_ids

    def get_nodes_shared_ids(self, node1_id: str, node2_id: str, id_type: str = 'both') -> List[Dict[str,str]]:
        if (type(node1_id) is not str) or (type(node2_id) is not str):
            raise ValueError(node1_id, node2_id)
        if type(id_type) is not str or id_type not in ['quadruplet', 'relation', 'both']:
            raise ValueError(id_type)

        formated_info = []

        n1_internal_ids = self.strid_nodes_index[node1_id]
        n2_internal_ids = self.strid_nodes_index[node2_id]
        for n1 in n1_internal_ids:
            for n2 in n2_internal_ids:
                shared_internal_qids = self.edges[n1].intersection(self.edges[n2])

                for internal_qid in shared_internal_qids:
                    if id_type == 'quadruplet':
                        formated_info.append({'t_id': self.quadruplets[internal_qid].id})
                    elif id_type == 'relation':
                        formated_info.append({'r_id': self.quadruplets[internal_qid].relation.id})
                    elif id_type == 'both':
                        formated_info.append({'t_id': self.quadruplets[internal_qid].id,
                            'r_id':self.quadruplets[internal_qid].relation.id})
                    else:
                        raise ValueError(id_type)

        return formated_info

    def get_quadruplets(self, node1_id: str, node2_id: str) -> List[Quadruplet]:
        if (type(node1_id) is not str) or (type(node2_id) is not str):
            raise ValueError

        start_n_db_ids = self.strid_nodes_index[node1_id]
        if len(start_n_db_ids) < 1:
            raise ValueError
        start_n_edges = set()
        for n_db_id in start_n_db_ids:
            start_n_edges.update(self.edges[n_db_id])

        end_n_db_ids = self.strid_nodes_index[node2_id]
        if len(end_n_db_ids) < 1:
            raise ValueError
        end_n_edges = set()
        for n_db_id in end_n_db_ids:
            end_n_edges.update(self.edges[n_db_id])

        shared_quadruplets_ids = end_n_edges.intersection(start_n_edges)
        quadruplets = list(map(lambda id: self.quadruplets[id], shared_quadruplets_ids))
        return quadruplets

    def get_quadruplets_by_name(self, subj_names: List[str], obj_names: List[str], obj_type: str) -> List[Quadruplet]:
        quadruplets = []
        for quadruplet in self.quadruplets.values():
            if obj_type in str(quadruplet.end_node.type):
                if subj_names and quadruplet.start_node.name in subj_names:
                    quadruplets.append(quadruplet)
                elif obj_names and quadruplet.end_node.name in obj_names:
                    quadruplets.append(quadruplet)
        return quadruplets

    def get_node_type(self, id: str) -> NodeType:
        if id in self.nodes:
            return self.nodes[id].type

        # Check if it is a string ID that maps to internal IDs
        internal_ids = self.strid_nodes_index.get(id)
        if internal_ids and len(internal_ids) > 0:
            first_internal_id = list(internal_ids)[0]
            if first_internal_id in self.nodes:
                return self.nodes[first_internal_id].type

        raise ValueError(f"Node with id {id} not found")

    def count_items(self, id: str = None, id_type: str = None) -> Union[Dict[str,int],int]:
        result = None
        if id_type is None:
            result = {'quadruplets': len(self.quadruplets), 'nodes': len(self.nodes)}

        elif id_type == 'node':
            result = len(self.strid_nodes_index[id])

        elif id_type == 'relation':
            result = len(self.strid_relation_index[id])

        elif id_type == 'quadruplet':
            result = len(self.qid_quadruplets_index[id])

        else:
            raise ValueError

        return result

    def item_exist(self, item_id: str, id_type: str ='quadruplet') -> bool:
        if type(item_id) is not str:
            raise ValueError

        output = None
        if id_type == 'node':
            output = self.strid_nodes_index[item_id]
        elif id_type == 'relation':
            output = self.strid_relation_index[item_id]
        elif id_type == 'quadruplet':
            output = self.qid_quadruplets_index[item_id]
        else:
            raise ValueError

        return len(output) > 0

    def clear(self) -> None:
        self.close_connection()
        self.open_connection()
        gc.collect()
