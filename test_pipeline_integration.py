
import os
import sys
from src.utils.graph_loader import hydrate_in_memory_graph
from src.kg_model.knowledge_graph_model import KnowledgeGraphModel, KnowledgeGraphModelConfig
from src.db_drivers.graph_driver import GraphDriverConfig
from src.pipelines.qa.qa_engine import QAEngine
from src.db_drivers.vector_driver.embedders import EmbedderModelConfig
from src.kg_model.embeddings_model import EmbeddingsModelConfig
from src.utils.wikidata_utils import WikidataMapper
from src.utils import Logger

from src.db_drivers.vector_driver import VectorDriverConfig, VectorDBConnectionConfig

# Setup Logger
logger = Logger("log/test_integration")

def test_pipeline():
    print("=== 1. Initialize KG Model ===")
    
    ROOT_DIR = os.getcwd()
    nodes_path = os.path.join(ROOT_DIR, "data/graph_structures/vectorized_nodes/wikidata_test")
    triplets_path = os.path.join(ROOT_DIR, "data/graph_structures/vectorized_triplets/wikidata_test")
    
    nodes_cfg = VectorDriverConfig(
        db_vendor='chroma', db_config=VectorDBConnectionConfig(
            conn={'path': nodes_path},
            db_info={'db': 'default_db', 'table': "personalaitable"}))
            
    triplets_cfg = VectorDriverConfig(
        db_vendor='chroma', db_config=VectorDBConnectionConfig(
            conn={'path': triplets_path},
            db_info={'db': 'default_db', 'table': "personalaitable"}))
    
    # Configure Embedder to use HF path and correct prompts
    embedder_cfg = EmbedderModelConfig(
        model_name_or_path='intfloat/multilingual-e5-small',
        prompts={"query": "query: ", "document": "passage: "} # Explicitly set correct prompts
    )
    embeddings_cfg = EmbeddingsModelConfig(
        nodesdb_driver_config=nodes_cfg,
        tripletsdb_driver_config=triplets_cfg,
        embedder_config=embedder_cfg
    )
    
    # Configure Graph Model
    from src.kg_model.graph_model import GraphModelConfig

    # Configure Graph Model
    graph_driver_conf = GraphDriverConfig(db_vendor='inmemory_graph')
    graph_conf = GraphModelConfig(driver_config=graph_driver_conf)
    
    config = KnowledgeGraphModelConfig(
        graph_config=graph_conf,
        embeddings_config=embeddings_cfg,
        log=logger, 
        verbose=True
    )
    kg_model = KnowledgeGraphModel(config=config)
    kg_model.graph_struct.db_conn.open_connection()
    
    print("\n=== 2. Hydrate Graph ===")
    data_dir = "wikidata_big/kg" 
    if not os.path.exists(data_dir):
        print(f"Error: Data directory {data_dir} not found!")
        return

    mapper = WikidataMapper(data_dir)
    hydrate_in_memory_graph(kg_model, mapper, data_dir)
    
    print("\n=== 3. Initialize QA Engine (with Ollama) ===")
    # QAEngine will use AgentDriver which defaults to Ollama now
    qa_engine = QAEngine(kg_model=kg_model, finetuned_model_path='intfloat/multilingual-e5-small')
    
    query = "What position did Richard Richards hold?"
    print(f"\n=== 4. Executing Query: '{query}' ===")
    
    try:
        results = qa_engine.get_ranked_results(query, top_k=5)
        
        print(f"\n=== 5. Results (Count: {len(results)}) ===")
        if not results:
            print("No results found.")
            # Print debug info if available
            if hasattr(qa_engine, 'last_extraction'):
                print("Last Extraction Debug:", qa_engine.last_extraction)
        
        for i, res in enumerate(results):
            print(f"#{i+1}: {res['text']} (Conf: {res['confidence']:.4f})")
            
    except Exception as e:
        print(f"\n[CRITICAL ERROR] Pipeline failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_pipeline()
