from src.pipelines.ingestion.core_loader import CoreLoader
from src.kg_model.knowledge_graph_model import KnowledgeGraphModel, KnowledgeGraphModelConfig
from src.kg_model.graph_model import GraphModelConfig
from src.kg_model.embeddings_model import EmbeddingsModelConfig
from src.db_drivers.graph_driver import GraphDriverConfig
from src.db_drivers.vector_driver.embedders import EmbedderModelConfig
from src.utils import Logger
from src.pipelines.qa.qa_engine import QAEngine

def run_test():
    log = Logger('qa_subset_log')
    print("Initializing components...")

    # Configs
    emb_conf = EmbedderModelConfig(model_name_or_path='sentence-transformers/all-MiniLM-L6-v2')
    graph_conf = GraphModelConfig(
        driver_config=GraphDriverConfig(db_vendor='inmemory_graph', db_config={})
    )
    emb_model_conf = EmbeddingsModelConfig(embedder_config=emb_conf)
    
    config = KnowledgeGraphModelConfig(
        graph_config=graph_conf,
        embeddings_config=emb_model_conf,
        log=log
    )

    kg_model = KnowledgeGraphModel(config=config)
    
    # 1. Ingest Subset
    loader = CoreLoader(kg_model, log)
    print('Starting subset ingestion (5000 items)...')
    try:
        loader.load_from_jsonl('processed_data/subset_quadruplets.jsonl', batch_size=1000)
    except Exception as e:
        print(f"Ingestion failed: {e}")
        return

    print('Ingestion complete.')
    counts = kg_model.count_items()
    print(f'KG Counts: {counts}')

    # 2. Run QA
    print("Initializing QA Engine...")
    # Pass the model name as finetuned_model_path
    qa_engine = QAEngine(kg_model, finetuned_model_path='sentence-transformers/all-MiniLM-L6-v2')
    
    # We need a query that matches something in the first 5000 items.
    # We should inspect the first item to form a query.
    # But for now, let's try generic query or check specific entity if known.
    # Let's read first line of subset to see content.
    with open('processed_data/subset_quadruplets.jsonl') as f:
        first_line = f.readline()
        print(f"First item: {first_line[:200]}...")
    
    # Assuming first item has a subject name
    import json
    item = json.loads(first_line)
    s_name = item['s']['name']
    query = f"Who is {s_name}?"
    print(f"Running QA for query: '{query}'")

    results = qa_engine.get_ranked_results(query, top_k=3)
    
    print("\n--- Results ---")
    for res in results:
        print(res)

if __name__ == "__main__":
    run_test()
