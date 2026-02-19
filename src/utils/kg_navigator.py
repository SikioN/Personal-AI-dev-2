from typing import List, Dict, Set, Tuple, Optional
from src.kg_model.knowledge_graph_model import KnowledgeGraphModel
from src.utils.data_structs import Quadruplet, QuadrupletCreator, Node, Relation
import networkx as nx

class KGNavigator:
    """Helper class to navigate the Knowledge Graph and extract subgraphs."""
    def __init__(self, kg_model: KnowledgeGraphModel):
        self.kg_model = kg_model

    def get_neighborhood(self, node_ids: List[str], depth: int = 1, limit: int = 0) -> List[Quadruplet]:
        """Fetch all quadruplets connected to the given nodes within specified depth."""
        all_quadruplets = []
        visited_nodes = set(node_ids)
        current_layer = set(node_ids)
        
        # print(f"DEBUG: [KGNavigator] Getting neighborhood for {node_ids} at depth {depth}")
        
        for d in range(depth):
            next_layer = set()
            for node_id in current_layer:
                # Get adjacent node IDs
                try:
                    adj_ids = self.kg_model.graph_struct.db_conn.get_adjecent_nids(node_id)
                    # print(f"DEBUG: [KGNavigator] Node {node_id} has {len(adj_ids)} adjacent nodes")
                except Exception as e:
                    print(f"DEBUG: [KGNavigator] Error getting adjacent nodes for {node_id}: {e}")
                    adj_ids = []

                # Apply limit per node if specified
                if limit > 0 and len(adj_ids) > limit:
                     adj_ids = list(adj_ids)[:limit]

                for adj_id in adj_ids:
                    # Get quadruplets between node_id and adj_id
                    try:
                        quadruplets = self.kg_model.graph_struct.db_conn.get_quadruplets(node_id, adj_id)
                        all_quadruplets.extend(quadruplets)
                    except Exception as e:
                        print(f"DEBUG: [KGNavigator] Error getting quadruplets between {node_id} and {adj_id}: {e}")
                    
                    if adj_id not in visited_nodes:
                        next_layer.add(adj_id)
                        visited_nodes.add(adj_id)
            current_layer = next_layer
        
        # print(f"DEBUG: [KGNavigator] Total quadruplets found: {len(all_quadruplets)}")
        return all_quadruplets

    def quadruplets_to_nx(self, quadruplets: List[Quadruplet]) -> nx.MultiDiGraph:
        """Convert a list of Quadruplets to a NetworkX graph."""
        G = nx.MultiDiGraph()
        for q in quadruplets:
            s_id = q.start_node.id
            o_id = q.end_node.id
            r_name = q.relation.name
            t_name = q.time.name if q.time else ""
            
            G.add_node(s_id, label=q.start_node.name, type=q.start_node.type)
            G.add_node(o_id, label=q.end_node.name, type=q.end_node.type)
            
            edge_label = r_name
            if t_name:
                edge_label += f"\n({t_name})"
            
            G.add_edge(s_id, o_id, label=edge_label, relation=r_name, time=t_name)
        return G
