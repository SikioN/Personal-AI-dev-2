
import chromadb
import os

def inspect_raw():
    ROOT_DIR = os.getcwd()
    nodes_path = os.path.join(ROOT_DIR, "data/graph_structures/vectorized_nodes/wikidata_test")
    
    print(f"Connecting to ChromaDB at {nodes_path}...")
    client = chromadb.PersistentClient(path=nodes_path)
    
    collection_name = "personalaitable"
    try:
        collection = client.get_collection(collection_name)
    except Exception as e:
        print(f"Error getting collection '{collection_name}': {e}")
        print("Available collections:", [c.name for c in client.list_collections()])
        return

    target_id = "e0dbcf3abfbb2f07e30a19cd676ab2f9"
    print(f"Looking for ID: {target_id}")
    
    result = collection.get(ids=[target_id])
    
    if result and result['documents']:
        print("\nFOUND DOCUMENT:")
        print(f"'{result['documents'][0]}'")
        print("\nMETADATA:")
        print(result['metadatas'][0])
    else:
        print("ID not found.")
        # Dump any 5 docs to check format
        print("\nDumping 5 random docs:")
        sample = collection.get(limit=5)
        for i, doc in enumerate(sample['documents']):
            print(f"ID: {sample['ids'][i]} -> '{doc}'")

if __name__ == "__main__":
    inspect_raw()
