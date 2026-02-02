import os
from tqdm import tqdm
from src.kg_model.knowledge_graph_model import KnowledgeGraphModel
from src.utils.data_structs import NodeCreator, RelationCreator, TripletCreator, NodeType, RelationType, create_id
from src.utils.wikidata_utils import WikidataMapper

def hydrate_in_memory_graph(kg_model: KnowledgeGraphModel, mapper: WikidataMapper, data_path: str):
    """
    Hydrate the In-Memory graph connector with data from full.txt.
    Supports both Wikidata IDs and MD5 IDs for compatibility with vector search.
    """
    full_txt_path = os.path.join(data_path, "full.txt")
    if not os.path.exists(full_txt_path):
        print(f"File not found: {full_txt_path}")
        return

    print(f"Hydrating graph from {full_txt_path}...")
    
    connector = kg_model.graph_struct.db_conn
    
    # We'll keep track of already created nodes to avoid duplicates and save memory
    internal_node_ids = {} # wd_id -> internal_id
    
    with open(full_txt_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
        for line in tqdm(lines, desc="Processing triplets"):
            parts = line.strip().split('\t')
            if len(parts) >= 3:
                s_id, r_id, o_id = parts[0], parts[1], parts[2]
                t1 = parts[3] if len(parts) > 3 else ""
                t2 = parts[4] if len(parts) > 4 else ""
                
                # Create or get Subject Node
                if s_id not in internal_node_ids:
                    s_name = mapper.get_label(s_id)
                    s_node = NodeCreator.create(NodeType.object, s_name, prop={'wd_id': s_id})
                    # Internal ID in InMemoryGraphConnector
                    # KEY FIX: Force ID to be hash of name ONLY to match Vector DB
                    new_id = create_id(s_name)
                    s_node.id = new_id
                    
                    internal_node_ids[s_id] = new_id
                    connector.nodes[new_id] = s_node
                    # Index by both Wikidata ID and MD5 ID
                    connector.strid_nodes_index[s_id].add(new_id)
                    connector.strid_nodes_index[s_node.id].add(new_id)
                
                # Create or get Object Node
                if o_id not in internal_node_ids:
                    o_name = mapper.get_label(o_id)
                    o_node = NodeCreator.create(NodeType.object, o_name, prop={'wd_id': o_id})
                    # KEY FIX: Force ID to be hash of name ONLY
                    new_id = create_id(o_name)
                    o_node.id = new_id
                    
                    internal_node_ids[o_id] = new_id
                    connector.nodes[new_id] = o_node
                    connector.strid_nodes_index[o_id].add(new_id)
                    connector.strid_nodes_index[o_node.id].add(new_id)

                # Create Relation and Triplet
                s_node = connector.nodes[internal_node_ids[s_id]]
                o_node = connector.nodes[internal_node_ids[o_id]]
                
                r_name = mapper.get_label(r_id)
                rel = RelationCreator.create(RelationType.simple, r_name, prop={'wd_id': r_id})
                
                time_str = f"{t1}-{t2}" if t1 and t2 and t1 != t2 else (t1 or t2)
                time_node = NodeCreator.create(NodeType.time, time_str) if time_str else None
                
                triplet = TripletCreator.create(s_node, rel, o_node, time=time_node)
                
                # Add triplet to connector
                t_internal_id = connector.generate_id()
                connector.triplets[t_internal_id] = triplet
                connector.tid_triplets_index[triplet.id].add(t_internal_id)
                
                # Add relationship to edges
                sn_internal_id = internal_node_ids[s_id]
                en_internal_id = internal_node_ids[o_id]
                
                connector.edges[sn_internal_id].add(t_internal_id)
                connector.adjacent_nodes[sn_internal_id].add(en_internal_id)
                connector.edges[en_internal_id].add(t_internal_id)
                connector.adjacent_nodes[en_internal_id].add(sn_internal_id)

    print(f"Hydration complete. Nodes: {len(connector.nodes)}, Triplets: {len(connector.triplets)}")
