import os
import sys
import torch
import pickle
import numpy as np
import pandas as pd
import shutil
import tempfile
import subprocess
from tqdm import tqdm
from collections import defaultdict
from types import SimpleNamespace
import chromadb.utils.embedding_functions

# === 1. ENVIRONMENT PATCHING ===
class MockEmbeddingFunction:
    def __init__(self, *args, **kwargs): pass
    def __call__(self, input):
        return [[0.0]*384 for _ in input] 
chromadb.utils.embedding_functions.ONNXMiniLM_L6_V2 = MockEmbeddingFunction

new_cache = os.path.join(tempfile.gettempdir(), "hf_cache_custom_kg")
os.makedirs(new_cache, exist_ok=True)
os.environ['HF_HOME'] = new_cache
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Force CPU to avoid MPS errors
if not torch.cuda.is_available():
    print("CUDA not available. Enforcing CPU execution.")
    def cpu_fallback(self, *args, **kwargs):
        return self.to('cpu')
    torch.Tensor.cuda = cpu_fallback
    torch.nn.Module.cuda = cpu_fallback

# === 2. SETUP PATHS ===
def set_project_root():
    current_dir = os.getcwd()
    # If in notebooks/metrics, go up 2 levels
    if current_dir.endswith("metrics"):
        os.chdir(os.path.join(current_dir, "../.."))
    elif current_dir.endswith("notebooks"):
        os.chdir(os.path.join(current_dir, ".."))
        
    current_dir = os.getcwd()
    if current_dir not in sys.path: sys.path.append(current_dir)
    
    cron_path = os.path.join(current_dir, 'CronKGQA', 'CronKGQA')
    if cron_path not in sys.path: sys.path.append(cron_path)
    return current_dir

PROJ_ROOT = set_project_root()
print(f"Project Root: {PROJ_ROOT}")

# === 3. IMPORTS ===
from src.kg_model.knowledge_graph_model import KnowledgeGraphModel, KnowledgeGraphModelConfig
from src.db_drivers.vector_driver.embedders import EmbedderModelConfig
from src.kg_model.embeddings_model import EmbeddingsModelConfig
from src.db_drivers.vector_driver import VectorDriverConfig, VectorDBConnectionConfig
from src.kg_model.graph_model import GraphModel, GraphModelConfig
from src.db_drivers.graph_driver import GraphDriverConfig
from src.utils.wikidata_utils import WikidataMapper
from src.utils.kg_navigator import KGNavigator
from src.kg_model.temporal.temporal_model import TemporalScorer
from qa_models import QA_model_EmbedKGQA
from transformers import DistilBertTokenizer

# === 4. INITIALIZATION ===
print("Initializing Components...")
# Graph
g_driver_conf = GraphDriverConfig(db_vendor='inmemory_graph')
g_model_conf = GraphModelConfig(driver_config=g_driver_conf)

# Skip ChromaDB to avoid hang
print("Skipping ChromaDB initialization due to lock.")
graph_struct = GraphModel(g_model_conf)
kg_model = SimpleNamespace(graph_struct=graph_struct, embeddings_struct=None)

# Hydrate Graph
kg_data_path = "wikidata_big/kg"
mapper = WikidataMapper(kg_data_path)
from src.utils.graph_loader import hydrate_in_memory_graph
hydrate_in_memory_graph(kg_model, mapper, kg_data_path)

# Temporal Scorer
temporal_scorer = TemporalScorer(device="cpu")

# QA Model
class Args:
    lm_frozen=1
    frozen=1
    combine_all_ents="None"

qa_model = QA_model_EmbedKGQA(temporal_scorer.model, Args())
ckpt_path = "models/cronkgqa/cronkgqa_trained.ckpt"
if os.path.exists(ckpt_path):
    qa_model.load_state_dict(torch.load(ckpt_path, map_location="cpu"), strict=False)
    qa_model.eval()
    tokenizer = DistilBertTokenizer.from_pretrained('distilbert-base-uncased')
    print("✓ QA Model loaded.")
else:
    print("❌ Checkpoint not found.")
    sys.exit(1)

# === 5. EVALUATION FUNCTIONS ===

def eval_baseline_tcomplex(question, head_ids, answers_set, top_k=10):
    if not head_ids: return {'mrr': 0}
    
    tokenized = tokenizer(question, return_tensors="pt", padding=True, truncation=True)
    q_ids = tokenized['input_ids']
    q_mask = tokenized['attention_mask']
    
    head_idx = None
    for qid in head_ids:
        if qid in temporal_scorer.ent_id:
            head_idx = temporal_scorer.ent_id[qid]
            break
    if head_idx is None: return {'mrr': 0}
    
    head_tensor = torch.LongTensor([head_idx])
    dummy = torch.LongTensor([0])
    
    with torch.no_grad():
        scores = qa_model((q_ids, q_mask, head_tensor, dummy, dummy))
        _, top_indices = torch.topk(scores, k=top_k)
        top_indices = top_indices.numpy()[0]
        
    rank = 1000
    id2ent = {v: k for k, v in temporal_scorer.ent_id.items()}
    for i, idx in enumerate(top_indices):
        pred_qid = id2ent.get(idx)
        if pred_qid in answers_set:
            rank = i + 1
            break
        # Fallback for years as ints
        try:
            if str(pred_qid).isdigit() and int(pred_qid) in answers_set:
                rank = i + 1
                break
        except: pass
            
    return {'hits@1': 1 if rank == 1 else 0, 'hits@10': 1 if rank <= 10 else 0, 'mrr': 1.0/rank if rank <= 10 else 0}

def eval_hybrid_ranked(question, head_ids, answers_set):
    # 1. Retrieval (Neo4j 1-hop)
    nav = KGNavigator(kg_model)
    conn = kg_model.graph_struct.db_conn
    start_node_ids = []
    
    for qid in head_ids:
        if hasattr(conn, 'strid_nodes_index'):
            internal_ids = conn.strid_nodes_index.get(qid, [])
            start_node_ids.extend(internal_ids)
            
    if not start_node_ids: return {'mrr': 0} # Retrieval Failed
    
    neighbors = nav.get_neighborhood(start_node_ids, depth=1)
    
    candidate_indices = set()
    for triplet in neighbors:
        # Check End Node
        o_qid = triplet.end_node.prop.get('wd_id')
        if o_qid in temporal_scorer.ent_id:
            candidate_indices.add(temporal_scorer.ent_id[o_qid])
        
        # Check Time in Relation/Fact
        t_val = triplet.time.name if triplet.time else triplet.relation.prop.get('time')
        if t_val:
            try:
                y = int(str(t_val).split('-')[0])
                # If year is in ent_id (sometimes years are entities)
                if str(y) in temporal_scorer.ent_id:
                    candidate_indices.add(temporal_scorer.ent_id[str(y)])
            except: pass

    if not candidate_indices: return {'mrr': 0}
    
    # 2. Scoring (TComplEx) on Candidates ONLY
    tokenized = tokenizer(question, return_tensors="pt", padding=True, truncation=True)
    
    head_idx = None
    for qid in head_ids:
        if qid in temporal_scorer.ent_id:
            head_idx = temporal_scorer.ent_id[qid]
            break
    if head_idx is None: return {'mrr': 0}
    
    with torch.no_grad():
        all_scores = qa_model((tokenized['input_ids'], tokenized['attention_mask'], 
                              torch.LongTensor([head_idx]), torch.LongTensor([0]), torch.LongTensor([0])))[0]
    
    # Masking: Set everything NOT in candidates to -inf
    filtered_scores = torch.full_like(all_scores, -float('inf'))
    candidate_tensor = torch.LongTensor(list(candidate_indices))
    filtered_scores[candidate_tensor] = all_scores[candidate_tensor]
    
    # Top-50
    _, top_indices = torch.topk(filtered_scores, k=50)
    top_indices = top_indices.numpy()
    
    rank = 1000
    id2ent = {v: k for k, v in temporal_scorer.ent_id.items()}
    
    for i, idx in enumerate(top_indices):
        pred_qid = id2ent.get(idx)
        match = False
        if pred_qid in answers_set: match = True
        else:
             try:
                 if str(pred_qid).isdigit() and int(pred_qid) in answers_set: match = True
             except: pass
             
        if match:
            rank = i + 1
            break
            
    return {'hits@1': 1 if rank == 1 else 0, 'hits@10': 1 if rank <= 10 else 0, 'mrr': 1.0/rank if rank <= 10 else 0}

# === 6. MAIN LOOP ===
print("Loading Test Data...")
with open('wikidata_big/questions/test.pickle', 'rb') as f:
    test_data = pickle.load(f)

SAMPLE_SIZE = 50
indices = np.random.choice(len(test_data), SAMPLE_SIZE, replace=False)
results = defaultdict(list)

print(f"Benchmarking {SAMPLE_SIZE} samples...")

for i, idx in enumerate(tqdm(indices)):
    item = test_data[idx]
    q, heads, answers = item['question'], item['entities'], item['answers']
    
    # 1. Baseline
    results['baseline'].append(eval_baseline_tcomplex(q, heads, answers))
    # 2. Hybrid Ranked
    results['hybrid'].append(eval_hybrid_ranked(q, heads, answers))

    if (i + 1) % 5 == 0:
        print(f"Processed {i + 1}/{SAMPLE_SIZE} samples...")
        sys.stdout.flush()

# === 7. REPORT ===
metrics = {}
for method, res in results.items():
    df = pd.DataFrame(res)
    metrics[method] = df.mean().to_dict()

print("\n=== BENCHMARK RESULTS ===")
print(f"| Method | MRR | Hits@1 | Hits@10 |")
print(f"| :--- | :--- | :--- | :--- |")
b = metrics['baseline']
print(f"| Baseline | {b.get('mrr',0):.4f} | {b.get('hits@1',0):.4f} | {b.get('hits@10',0):.4f} |")
h = metrics['hybrid']
print(f"| Hybrid (Neo4j+TComplEx) | {h.get('mrr',0):.4f} | {h.get('hits@1',0):.4f} | {h.get('hits@10',0):.4f} |")
