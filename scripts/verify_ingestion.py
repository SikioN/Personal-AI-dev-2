from src.kg_model.embeddings_model import EmbeddingsModel, EmbeddingsModelConfig
from src.db_drivers.vector_driver.embedders import EmbedderModelConfig
import sys

def verify():
    print("Initializing EmbeddingsModel to verify ChromaDB content...")
    
    # Must use same config as ingestion
    emb_conf = EmbedderModelConfig(model_name_or_path='sentence-transformers/all-MiniLM-L6-v2')
    emb_model_conf = EmbeddingsModelConfig(embedder_config=emb_conf)

    try:
        emb_model = EmbeddingsModel(config=emb_model_conf)
    except Exception as e:
        print(f"Failed to initialize EmbeddingsModel: {e}")
        sys.exit(1)

    print(f"Collections found: {list(emb_model.vectordbs.keys())}")

    nodes_count = emb_model.vectordbs['nodes'].count_items()
    quads_count = emb_model.vectordbs['quadruplets'].count_items()

    print(f"Nodes count: {nodes_count}")
    print(f"Quadruplets count: {quads_count}")

    if quads_count == 0:
        print("ERROR: Quadruplets collection is empty!")
        sys.exit(1)
        
    print("SUCCESS: Vector DB is populated.")

if __name__ == "__main__":
    verify()
