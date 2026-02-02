from typing import List, Dict, Set, Tuple, Optional
from src.kg_model.knowledge_graph_model import KnowledgeGraphModel
from src.utils.data_structs import Triplet, TripletCreator, Node, Relation
import networkx as nx

class KGNavigator:
    """Helper class to navigate the Knowledge Graph and extract subgraphs."""
    def __init__(self, kg_model: KnowledgeGraphModel):
        self.kg_model = kg_model

    def get_neighborhood(self, node_ids: List[str], depth: int = 1) -> List[Triplet]:
        """Fetch all triplets connected to the given nodes within specified depth."""
        all_triplets = []
        visited_nodes = set(node_ids)
        current_layer = set(node_ids)
        
        for d in range(depth):
            next_layer = set()
            for node_id in current_layer:
                # Get adjacent node IDs
                adj_ids = self.kg_model.graph_struct.db_conn.get_adjecent_nids(node_id)
                for adj_id in adj_ids:
                    # Get triplets between node_id and adj_id
                    triplets = self.kg_model.graph_struct.db_conn.get_triplets(node_id, adj_id)
                    all_triplets.extend(triplets)
                    if adj_id not in visited_nodes:
                        next_layer.add(adj_id)
                        visited_nodes.add(adj_id)
            current_layer = next_layer
        return all_triplets

    def triplets_to_nx(self, triplets: List[Triplet]) -> nx.MultiDiGraph:
        """Convert a list of Triplets to a NetworkX graph."""
        G = nx.MultiDiGraph()
        for t in triplets:
            s_id = t.start_node.id
            o_id = t.end_node.id
            r_name = t.relation.name
            t_name = t.time.name if t.time else ""
            
            G.add_node(s_id, label=t.start_node.name, type=t.start_node.type)
            G.add_node(o_id, label=t.end_node.name, type=t.end_node.type)
            
            edge_label = r_name
            if t_name:
                edge_label += f"\n({t_name})"
            
            G.add_edge(s_id, o_id, label=edge_label, relation=r_name, time=t_name)
        return G
