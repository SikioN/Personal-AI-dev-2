
import sys
import os
import importlib.util

def import_client():
    file_path = os.path.join(os.getcwd(), "src/llm/ollama_client.py")
    spec = importlib.util.spec_from_file_location("ollama_client", file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["ollama_client"] = module
    spec.loader.exec_module(module)
    return module.OllamaClient

def test_ollama():
    print("Initializing Ollama Client (Bypassing src package)...")
    OllamaClient = import_client()
    
    # Use llama3.2 as seen in 'ollama list'
    client = OllamaClient(model="llama3.2")
    
    question = "Who received an award for acting?"
    print(f"Testing with question: '{question}'")
    
    try:
        result = client.extract_search_parameters(question)
        print("--- Extraction Result ---")
        print(result)
        
        # Check for expected keys
        if "entities" in result:
             print("\nSUCCESS: JSON extracted with 'entities' list.")
             print(f"Entities: {result.get('entities')}")
             print(f"Relation: {result.get('relation')}")
             print(f"Time: {result.get('time')}")
        elif "entity" in result:
             print("\nWARNING: Legacy 'entity' key found (Single entity).")
             print(f"Entity: {result.get('entity')}")
        else:
            print("\nWARNING: Extraction might be incomplete. Check the output.")
            
    except Exception as e:
        print(f"\nERROR: Failed to connect or parse. Is Ollama running? Error: {e}")

if __name__ == "__main__":
    test_ollama()
