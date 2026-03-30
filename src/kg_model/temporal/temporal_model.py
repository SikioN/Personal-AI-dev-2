
import logging
import torch
import pickle
import os
from typing import Dict, Optional, Tuple
from .tkbc_models import TComplEx

logger = logging.getLogger(__name__)


def _compute_optimal_batch_size(
    n_entities: int,
    rank: int,
    device: str,
    safety_factor: float = 0.4,
) -> int:
    """Auto-compute batch size for TComplEx training on given device.

    With BF16: ~2 bytes/element for activation tensor (batch × n_entities).
    A100 80GB can handle large batches; clamped to power-of-2 for CUDA efficiency.
    """
    if "cuda" not in device:
        return 1000  # CPU: conservative default

    try:
        gpu_idx = int(device.split(":")[-1]) if ":" in device else 0
        total_mem = torch.cuda.get_device_properties(gpu_idx).total_memory
    except Exception:
        total_mem = 80 * 1024 ** 3  # fallback: assume A100 80GB

    # Estimate param memory (float32): 3 embedding tables × n_entities × 2*rank × 4 bytes
    param_mem = 3 * n_entities * 2 * rank * 4
    # Usable memory for activations = total × safety_factor − params − gradients
    usable = max(0, total_mem * safety_factor - 2 * param_mem)
    # Activation cost per batch item: n_entities × 2 bytes (BF16)
    cost_per_item = n_entities * 2
    raw_bs = int(usable / cost_per_item) if cost_per_item > 0 else 1000
    raw_bs = max(256, min(raw_bs, 65536))
    # Round down to nearest power-of-2 for CUDA efficiency
    bs = 1
    while bs * 2 <= raw_bs:
        bs *= 2
    return bs

class TemporalScorer:
    def __init__(self,
                 checkpoint_path: str = None,
                 data_path: str = None,
                 rank: int = 256,  # Rank 256 (matches checkpoint 512 dim)
                 device: str = "cpu"):

        self.device = device

        # Resolve project root: src/kg_model/temporal/ → 3 levels up
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, "../../.."))

        # Fall back to env vars, then hardcoded defaults
        if checkpoint_path is None:
            checkpoint_path = os.environ.get(
                "TCOMPLEX_CHECKPOINT", "models/cronkgqa/tcomplex.ckpt")
        if data_path is None:
            data_path = os.environ.get(
                "TCOMPLEX_DATA_PATH", "wikidata_big/kg/tkbc_processed_data/wikidata_big/")

        # Make relative paths absolute against project root
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
        
        # Load Weights first to auto-detect rank from checkpoint
        print(f"Loading weights from {checkpoint_path}...")
        if not os.path.exists(checkpoint_path):
            raise FileNotFoundError(f"Checkpoint not found at {checkpoint_path}")

        checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)

        # Handle different checkpoint formats (e.g. if wrapped in 'state_dict')
        if isinstance(checkpoint, dict) and 'state_dict' in checkpoint:
            state_dict = checkpoint['state_dict']
        else:
            state_dict = checkpoint

        # Remove 'model.' prefix if present (common in Lightning)
        new_state_dict = {}
        for k, v in state_dict.items():
            new_state_dict[k[6:] if k.startswith('model.') else k] = v

        # Auto-detect rank from checkpoint shape: embeddings.0.weight has shape [n_ent, 2*rank]
        if 'embeddings.0.weight' in new_state_dict:
            detected_rank = new_state_dict['embeddings.0.weight'].shape[1] // 2
            if detected_rank != rank:
                print(f"  [INFO] rank auto-detected from checkpoint: {detected_rank} (was {rank})")
                rank = detected_rank

        # Initialize Model with correct rank
        # TComplEx init: sizes: Tuple[int, int, int, int], rank: int
        # sizes = (n_ent, n_rel, n_ent, n_timestamps)
        # Checkpoint expects 2 * n_rel (inverse relations)
        sizes = (self.num_entities, self.num_relations * 2, self.num_entities, self.num_timestamps)

        self.model = TComplEx(sizes, rank, no_time_emb=False)

        # Copy weights from checkpoint, handling size mismatch when new entities/relations
        # were added after ingestion. For each embedding tensor, copy the rows that exist
        # in the checkpoint; new rows stay randomly initialised and are fine-tuned on retrain.
        model_state = self.model.state_dict()
        size_mismatch = False
        for key, ckpt_tensor in new_state_dict.items():
            if key not in model_state:
                continue
            model_tensor = model_state[key]
            if model_tensor.shape == ckpt_tensor.shape:
                model_state[key] = ckpt_tensor
            else:
                size_mismatch = True
                # Copy along each dim up to the min size
                slices = tuple(slice(0, min(s, c)) for s, c in zip(model_tensor.shape, ckpt_tensor.shape))
                model_tensor[slices].copy_(ckpt_tensor[slices])
                model_state[key] = model_tensor
        self.model.load_state_dict(model_state, strict=True)
        if size_mismatch:
            print(f"  [INFO] Checkpoint size mismatch — old embeddings copied, "
                  f"new entity/relation rows initialised randomly. Run retrain to update them.")

        self.model.to(device)
        self.model.eval()
        print(f"TemporalScorer initialized successfully (rank={rank}).")

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
            raw_score = self.model.score(input_tensor)

            # Usually these scores are logits. We can apply sigmoid if we want 0-1 prob,
            # but for ranking, raw logits are fine. E5 uses cosine (0-1).
            # To be compatible/comparable, maybe sigmoid is better?
            # Or just normalize.
            # In KG embeddings, higher is better.

            return raw_score.item()

    def finetune(
        self,
        train_data,
        epochs: int = 50,
        batch_size: int = None,
        lr: float = 1e-3,
        num_gpus: int = None,
        use_amp: bool = True,
    ) -> None:
        """
        Gradient descent loop on full train_data (numpy array of (s,r,o,t) ints).
        Uses the regularizer loss from TComplEx.forward() as the training signal.

        Args:
            batch_size: None = auto-compute from GPU memory.
            num_gpus: None = auto-detect from torch.cuda.device_count().
            use_amp: Enable BF16 mixed precision on A100 (ignored on CPU/MPS).
        """
        import torch.nn.functional as F

        n = len(train_data)
        if n == 0:
            return

        # ── 1. Determine device and GPU count ─────────────────────────────────
        is_cuda = "cuda" in self.device
        if num_gpus is None:
            num_gpus = torch.cuda.device_count() if is_cuda else 0

        # ── 2. Auto batch_size ────────────────────────────────────────────────
        rank = self.model.embeddings[0].weight.shape[1] // 2
        n_ent = self.model.embeddings[0].weight.shape[0]
        if batch_size is None:
            batch_size = _compute_optimal_batch_size(n_ent, rank, self.device)
            logger.info("[TComplEx] Auto batch_size=%d for device=%s", batch_size, self.device)

        # ── 3. Switch to dense embeddings for multi-GPU compatibility ─────────
        _was_sparse = {}
        if num_gpus > 1 and is_cuda:
            for i, emb in enumerate(self.model.embeddings):
                _was_sparse[i] = emb.sparse
                if emb.sparse:
                    emb.sparse = False

        # ── 4. Wrap with DataParallel if multiple GPUs ────────────────────────
        train_model = self.model
        device_ids = list(range(num_gpus)) if num_gpus > 1 and is_cuda else None
        if device_ids:
            train_model = torch.nn.DataParallel(self.model, device_ids=device_ids)
            logger.info("[TComplEx] Using DataParallel on %d GPUs: %s", num_gpus, device_ids)
            batch_size = batch_size * num_gpus
            logger.info("[TComplEx] Effective batch_size=%d", batch_size)

        # ── 5. TF32 + BF16 AMP setup ──────────────────────────────────────────
        if is_cuda:
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True

        amp_dtype = torch.bfloat16 if (
            use_amp and is_cuda and torch.cuda.is_bf16_supported()
        ) else None
        use_amp_actual = amp_dtype is not None
        if use_amp_actual:
            logger.info("[TComplEx] Using BF16 AMP autocast")

        # ── 6. Optimizer ───────────────────────────────────────────────────────
        underlying = train_model.module if hasattr(train_model, 'module') else train_model
        optimizer = torch.optim.Adagrad(underlying.parameters(), lr=lr)

        # ── 7. Training loop ───────────────────────────────────────────────────
        train_model.train()
        data = torch.tensor(train_data, dtype=torch.long, device=self.device)
        reg_weight = 1e-2

        for epoch in range(epochs):
            perm = torch.randperm(n, device=self.device)
            epoch_loss = 0.0
            steps = 0
            for i in range(0, n, batch_size):
                batch = data[perm[i:i + batch_size]]
                optimizer.zero_grad(set_to_none=True)

                if use_amp_actual:
                    with torch.autocast(device_type="cuda", dtype=amp_dtype):
                        predictions, regularizer, _ = train_model(batch)
                        targets = batch[:, 2]
                        ce_loss = F.cross_entropy(predictions, targets)
                        l3_reg = sum(torch.sum(torch.abs(r) ** 3) for r in regularizer)
                        loss = ce_loss + reg_weight * l3_reg
                else:
                    predictions, regularizer, _ = train_model(batch)
                    targets = batch[:, 2]
                    ce_loss = F.cross_entropy(predictions, targets)
                    l3_reg = sum(torch.sum(torch.abs(r) ** 3) for r in regularizer)
                    loss = ce_loss + reg_weight * l3_reg

                loss.backward()
                optimizer.step()
                epoch_loss += loss.item()
                steps += 1

            if (epoch + 1) % 10 == 0 or epoch == 0:
                logger.info(
                    "[TComplEx] epoch %d/%d  loss=%.4f  bs=%d  amp=%s",
                    epoch + 1, epochs,
                    epoch_loss / max(steps, 1),
                    batch_size,
                    "bf16" if use_amp_actual else "fp32",
                )

        # ── 8. Restore sparse embeddings for inference ─────────────────────────
        if _was_sparse:
            for i, emb in enumerate(self.model.embeddings):
                emb.sparse = _was_sparse.get(i, emb.sparse)

        self.model.eval()
        logger.info("[TComplEx] Fine-tuning complete.")

    def save(self, path: str) -> None:
        """Save current model weights to checkpoint file."""
        torch.save(self.model.state_dict(), path)
        print(f"TemporalScorer checkpoint saved to {path}")

