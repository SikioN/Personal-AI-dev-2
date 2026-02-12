
import torch
import pickle
import os
from typing import Dict, Optional, Tuple
from .tkbc_models import TComplEx

class TemporalScorer:
    def __init__(self, 
                 checkpoint_path: str = "models/cronkgqa/tcomplex.ckpt",
                 data_path: str = "wikidata_big/kg/tkbc_processed_data/wikidata_big/",
                 rank: int = 256, # Rank 256 (matches checkpoint 512 dim)
                 device: str = "cpu"):
        
        self.device = device
        
        # Resolving absolute paths relative to project root
        # This file is in src/kg_model/temporal/ -> 3 levels up to root (src/kg_model/temporal -> src/kg_model -> src -> root)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, "../../.."))
        
        # If paths are relative, make them absolute
        if not os.path.isabs(data_path):
             data_path = os.path.join(project_root, data_path)
             
        if not os.path.isabs(checkpoint_path):
             checkpoint_path = os.path.join(project_root, checkpoint_path)

        self.data_path = data_path
        
        print(f"Loading TemporalScorer resources from {data_path}...")
        self.ent_id = self._load_pickle("ent_id")
        self.rel_id = self._load_pickle("rel_id")
        self.ts_id = self._load_pickle("ts_id")
        
        self.num_entities = len(self.ent_id)
        self.num_relations = len(self.rel_id)
        self.num_timestamps = len(self.ts_id)
        
        print(f"Loaded mappings: {self.num_entities} entities, {self.num_relations} relations, {self.num_timestamps} timestamps")
        
        # Initialize Model
        # TComplEx init: sizes: Tuple[int, int, int, int], rank: int
        # sizes = (n_ent, n_rel, n_ent, n_timestamps)
        # Checkpoint expects 2 * n_rel (inverse relations)
        sizes = (self.num_entities, self.num_relations * 2, self.num_entities, self.num_timestamps)
        
        self.model = TComplEx(sizes, rank, no_time_emb=False)
        
        # Load Weights
        print(f"Loading weights from {checkpoint_path}...")
        if not os.path.exists(checkpoint_path):
            raise FileNotFoundError(f"Checkpoint not found at {checkpoint_path}")
            
        checkpoint = torch.load(checkpoint_path, map_location=device)
        
        # Handle different checkpoint formats (e.g. if wrapped in 'state_dict')
        if isinstance(checkpoint, dict) and 'state_dict' in checkpoint:
            state_dict = checkpoint['state_dict']
        else:
            state_dict = checkpoint
            
        # Remove 'model.' prefix if present (common in Lightning)
        new_state_dict = {}
        for k, v in state_dict.items():
            if k.startswith('model.'):
                new_state_dict[k[6:]] = v
            else:
                new_state_dict[k] = v
                
        self.model.load_state_dict(new_state_dict)
        self.model.to(device)
        self.model.eval()
        print("TemporalScorer initialized successfully.")

    def _load_pickle(self, filename: str):
        path = os.path.join(self.data_path, filename)
        if not os.path.exists(path):
             # Try fallback paths if needed, or raise error
             raise FileNotFoundError(f"Mapping file not found: {path}")
        with open(path, 'rb') as f:
            return pickle.load(f)

    def get_id(self, qid: str, type_: str) -> Optional[int]:
        """Convert string ID (Q123, P456, 2024) to internal int ID"""
        if type_ == 'entity':
            return self.ent_id.get(qid)
        elif type_ == 'relation':
            return self.rel_id.get(qid)
        elif type_ == 'timestamp':
            # ts_id keys are tuples (Y, M, D)
            # Try direct lookup
            res = self.ts_id.get(qid)
            if res is not None: return res
            
            # Try converting year-string to (Year, 0, 0) - confirmed by inspection
            try:
                y = int(qid)
                return self.ts_id.get((y, 0, 0))
            except:
                pass
            return None
        return None

    def score(self, s_qid: str, r_pid: str, o_qid: str, time: str) -> float:
        """
        Calculate probability score for the quadruplet (s, r, o, t).
        Returns -1.0 if entities are not known.
        """
        s_id = self.get_id(s_qid, 'entity')
        r_id = self.get_id(r_pid, 'relation')
        o_id = self.get_id(o_qid, 'entity')
        t_id = self.get_id(time, 'timestamp')
        
        if any(x is None for x in [s_id, r_id, o_id, t_id]):
            # print(f"Missing mapping for {s_qid}, {r_pid}, {o_qid}, {time}")
            return -10.0 # Return low score for unknown entities

        # Prepare tensor: (batch_size, 4) -> (s, r, o, t)
        input_tensor = torch.tensor([[s_id, r_id, o_id, t_id]], device=self.device)
        
        with torch.no_grad():
            score = self.model.forward(input_tensor)
            # TComplEx returns: (scores, regularizer, etc.) or just scores depending on method
            # Wait, tkbc_models.py TComplEx.forward returns tuple: (score, regularizer, time_emb)
            # But TComplEx.score(x) returns just score!
            
            # Let's use score(x) method
            raw_score = self.model.score(input_tensor)
            
            # Usually these scores are logits. We can apply sigmoid if we want 0-1 prob,
            # but for ranking, raw logits are fine. E5 uses cosine (0-1).
            # To be compatible/comparable, maybe sigmoid is better? 
            # Or just normalize.
            # In KG embeddings, higher is better.
            
            return raw_score.item()

