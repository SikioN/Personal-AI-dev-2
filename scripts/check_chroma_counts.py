import chromadb
import os

def check_all_dbs():
    # List from 'find' command earlier
    potential_paths = [
        "./chroma_test_db",
        "./data/graph_structures/vectorized_triplets/default_densedb",
        "./data/graph_structures/vectorized_triplets/wikidata_test",
        "./data/graph_structures/vectorized_nodes/default_densedb",
        "./data/graph_structures/vectorized_nodes/wikidata_test",
        "./debug/qa_pipeline/tesing_db"
    ]

    print("🔍 Hunting for data in all known ChromaDB locations...")

    for rel_path in potential_paths:
        abs_path = os.path.abspath(rel_path)
        if not os.path.exists(os.path.join(abs_path, "chroma.sqlite3")):
            continue
            
        print(f"\n📂 Checking: {rel_path}")
        try:
            client = chromadb.PersistentClient(path=abs_path)
            collections = client.list_collections()
            
            if not collections:
                print("   ⚠️ No collections found.")
                continue
                
            for col in collections:
                count = col.count()
                print(f"   📊 Collection '{col.name}': {count} items")
                if count > 0:
                   print(f"   ✅ FOUND DATA HERE! ({count} items)")
                   # Peek
                   peek = col.get(limit=1)
                   print(f"   Sample: {peek['documents'][0][:50]}...")
                   
        except Exception as e:
            print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    check_all_dbs()
