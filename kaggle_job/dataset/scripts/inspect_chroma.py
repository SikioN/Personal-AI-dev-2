import chromadb
import os
import sys
import pandas as pd

# Adjust path to where the DB is located
# Based on previous logs: ../data/graph_structures/vectorized_nodes/default_densedb
# But script is running from project root, so it is likely data/graph_structures/...

def inspect_chroma():
    # Paths from EmbeddingsModel.py (relative to CWD project root)
    paths = {
        "Nodes": "../data/graph_structures/vectorized_nodes/default_densedb",
        "Quadruplets": "../data/graph_structures/vectorized_quadruplets/default_densedb"
    }
    
    for name, base_path in paths.items():
        print(f"\n{'='*30}\n📂 Checking {name} DB at: {base_path}\n{'='*30}")
        
        if not os.path.exists(base_path):
            print(f"❌ Path not found: {base_path}")
            continue

        # Create a temp copy to bypass lock
        import shutil
        import tempfile
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                src_db = os.path.join(base_path, "chroma.sqlite3")
                if not os.path.exists(src_db):
                    print(f"❌ DB file not found: {src_db}")
                    continue
                    
                temp_db_path = os.path.join(temp_dir, "chroma.sqlite3")
                shutil.copy2(src_db, temp_db_path)
                
                # Copy the binary folders too if they exist (crucial for chroma > 0.4)
                # Usually they are UUID folders inside base_path
                for item in os.listdir(base_path):
                    s = os.path.join(base_path, item)
                    d = os.path.join(temp_dir, item)
                    if os.path.isdir(s):
                         shutil.copytree(s, d)

                client = chromadb.PersistentClient(path=temp_dir)
                collections = client.list_collections()
                print(f"Collections found: {[c.name for c in collections]}")
                
                for col in collections:
                    count = col.count()
                    print(f"📊 Collection '{col.name}': {count} items")
                    
                    if count > 0:
                        print(f"👀 Peeking first 3 records in '{col.name}':")
                        geo = col.get(limit=3, include=['documents', 'metadatas'])
                        docs = geo['documents']
                        metas = geo['metadatas']
                        ids = geo['ids']
                        
                        for i in range(len(docs)):
                            print(f"   [ID: {ids[i]}]")
                            print(f"   📝 Text: \"{docs[i]}\"")
                            print(f"   ℹ️ Meta: {metas[i]}")
                            print("-" * 20)
        except Exception as e:
            print(f"❌ Error reading {name}: {e}")

if __name__ == "__main__":
    inspect_chroma()
