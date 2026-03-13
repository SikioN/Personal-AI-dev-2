import os
import sys
from src.utils.graph_loader import hydrate_in_memory_graph
from src.kg_model.knowledge_graph_model import KnowledgeGraphModel, KnowledgeGraphModelConfig
from src.db_drivers.graph_driver import GraphDriverConfig
from src.pipelines.qa.qa_engine import QAEngine
from src.db_drivers.vector_driver.embedders import EmbedderModelConfig
from src.kg_model.embeddings_model import EmbeddingsModelConfig

# Setup Logger
from src.utils import Logger
logger = Logger("log/debug_pipeline")

def debug_pipeline():
    print("=== 1. Initialize KG Model ===")
    # 1. Init KG
    logger = Logger("log/debug_pipeline")
    
    # Configure Embedder to use HF path
    embedder_cfg = EmbedderModelConfig(model_name_or_path='intfloat/multilingual-e5-small')
    embeddings_cfg = EmbeddingsModelConfig(embedder_config=embedder_cfg)
    
    config = KnowledgeGraphModelConfig(
        graph_config=GraphDriverConfig(db_vendor='inmemory_graph'),
        embeddings_config=embeddings_cfg
    )
    kg_model = KnowledgeGraphModel(config=config)
    kg_model.graph_struct.db_conn.open_connection()
    
    print("\n=== 2. Hydrate Graph ===")
    # 2. Hydrate
    from src.utils.wikidata_utils import WikidataMapper
    
    # Check where full.txt is. Assuming it's in wikidata_test based on previous context.
    data_dir = "wikidata_big/kg" 
    mapper = WikidataMapper(data_dir)
    hydrate_in_memory_graph(kg_model, mapper, data_dir)
    
    # 3. Check Richard Richards presence
    rr_id = "Q25559009"
    # Check directly in connector
    internal_ids = kg_model.graph_struct.db_conn.strid_nodes_index.get(rr_id)
    print(f"\n[Check] Richard Richards ({rr_id}) in index: {internal_ids}")
    
    if internal_ids:
        node = kg_model.graph_struct.db_conn.nodes.get(list(internal_ids)[0])
        print(f"[Check] Node object: {node}")
        print(f"[Check] Node Type: {kg_model.graph_struct.db_conn.get_node_type(node.id)}")
    else:
        print("[ERROR] Richard Richards NOT found in graph index!")

    print("\n=== 3. Initialize QA Engine ===")
    # 4. Init Engine
    # Use default E5 model path as in app.py
    qa_engine = QAEngine(kg_model=kg_model, finetuned_model_path='intfloat/multilingual-e5-small')
    
    query = "What position did Richard Richards hold?"
    print(f"\n=== 4. Test Entity Extraction for '{query}' ===")
    
    # 5. Extract Entities
    # We call the internal method or the full pipeline? Let's trace get_ranked_results steps manually if possible, 
    # or just call the public method and see logs.
    
    # Manually running extraction
    extracted_entities, _ = qa_engine.entities_extractor.perform(query)
    print(f"[Result] Extracted Entities: {extracted_entities}")
    
    # 6. Test Mapping
    print("\n=== 5. Test Entity Mapping ===")
    # Simulate what get_ranked_results does
    mapped_ids = []
    if extracted_entities:
        for ent in extracted_entities:
            mid = qa_engine.wikidata_mapper.map(ent)
            print(f"Mapping '{ent}' -> {mid}")
            if mid: mapped_ids.append(mid)
            
    # 7. Test Retrieval
    print("\n=== 6. Test Retrieval ===")
    # We need to replicate the logic in get_ranked_results where it looks up the node
    found_nodes = []
    for mid in mapped_ids:
        # Direct lookup
        iids = kg_model.graph_struct.db_conn.strid_nodes_index.get(mid)
        if iids:
            for iid in iids:
                if iid in kg_model.graph_struct.db_conn.nodes:
                     found_nodes.append(kg_model.graph_struct.db_conn.nodes[iid])
    
    print(f"[Result] Found Nodes via Map: {[n.name for n in found_nodes]}")
    
    if not found_nodes:
        print("Fallback to Vector Search (Mock check)...")
        # In this debug script we might not have the vector DB running, skipping vector check for now 
        # as we want the direct mapping to work.

    if found_nodes:
        print("\n=== 7. Test Neighborhood ===")
        from src.utils.kg_navigator import KGNavigator
        navigator = KGNavigator(kg_model)
        neighborhood = navigator.get_neighborhood(found_nodes)
        print(f"[Result] Neighborhood size: {len(neighborhood)}")
        for t in neighborhood[:5]:
            print(f"- {t}")

if __name__ == "__main__":
    debug_pipeline()
