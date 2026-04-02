#!/usr/bin/env python3
"""
retrain_tcomplex.py — Wrapper to retrain TComplEx temporal scorer after ingestion.

Usage (fine-tune existing checkpoint):
    python scripts/retrain_tcomplex.py \\
        --tkbc-dir wikidata_big/kg/tkbc_processed_data/wikidata_big/ \\
        [--epochs 50] [--batch-size 1000] [--lr 1e-3]

Usage (train from scratch — no Wikidata, local CQ_/CP_ IDs):
    python scripts/retrain_tcomplex.py \\
        --from-scratch \\
        --jsonl extract_data/quadruplets.jsonl \\
        --tkbc-dir data/local_tcomplex/ \\
        --rank 128 \\
        --epochs 100 \\
        --checkpoint-out models/cronkgqa/tcomplex.ckpt
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _train_from_scratch(args) -> None:
    """Build TComplEx from scratch using local JSONL quadruplets (no Wikidata needed)."""
    import json
    import pickle
    import numpy as np

    jsonl_path = args.jsonl
    tkbc_dir = Path(args.tkbc_dir)
    tkbc_dir.mkdir(parents=True, exist_ok=True)

    if not os.path.exists(jsonl_path):
        logger.error("JSONL file not found: %s", jsonl_path)
        sys.exit(1)

    # 1. Load quadruplets from JSONL
    quads_raw = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                quads_raw.append(json.loads(line))
    logger.info("Loaded %d quadruplets from %s", len(quads_raw), jsonl_path)

    if not quads_raw:
        logger.error("No quadruplets found in %s", jsonl_path)
        sys.exit(1)

    # 2. Collect unique entities, relations, timestamps
    entities: set[str] = set()
    relations: set[str] = set()
    timestamps: set[int] = set()

    for q in quads_raw:
        entities.add(q["s"]["id"])
        entities.add(q["o"]["id"])
        relations.add(q["r"]["id"])
        t_prop = q.get("t", {}).get("prop", {})
        for yr_str in [t_prop.get("start", ""), t_prop.get("end", "")]:
            if yr_str and str(yr_str).isdigit():
                timestamps.add(int(yr_str))

    # Build str->int mappings (sorted for reproducibility)
    ent_id = {e: i for i, e in enumerate(sorted(entities))}
    rel_id = {r: i for i, r in enumerate(sorted(relations))}
    # ts_id keys must be (year, 0, 0) tuples — required by TemporalScorer.get_id()
    ts_id  = {(yr, 0, 0): i for i, yr in enumerate(sorted(timestamps))}

    logger.info("Entities: %d  Relations: %d  Timestamps: %d",
                len(ent_id), len(rel_id), len(ts_id))

    # 3. Save pickle mappings
    for name, obj in [("ent_id", ent_id), ("rel_id", rel_id), ("ts_id", ts_id)]:
        with open(tkbc_dir / name, "wb") as f:
            pickle.dump(obj, f)
    logger.info("Saved ent_id, rel_id, ts_id to %s", tkbc_dir)

    # 4. Build train.pickle — numpy array (N, 4): [s_int, r_int, o_int, t_int]
    rows = []
    skipped = 0
    for q in quads_raw:
        s = ent_id.get(q["s"]["id"])
        r = rel_id.get(q["r"]["id"])
        o = ent_id.get(q["o"]["id"])
        t_start = q.get("t", {}).get("prop", {}).get("start", "")
        t_int = ts_id.get((int(t_start), 0, 0)) if t_start and str(t_start).isdigit() else None
        if None in (s, r, o, t_int):
            skipped += 1
            continue
        rows.append([s, r, o, t_int])

    if skipped:
        logger.warning("Skipped %d quadruplets (missing timestamp or mapping)", skipped)

    train_data = np.array(rows, dtype=np.int64)
    with open(tkbc_dir / "train.pickle", "wb") as f:
        pickle.dump(train_data, f)
    logger.info("train.pickle: %d rows", len(train_data))

    if len(train_data) == 0:
        logger.error("No valid training rows — check JSONL timestamps (need numeric years).")
        sys.exit(1)

    # 5. Initialize TComplEx from scratch
    from src.kg_model.temporal.tkbc_models import TComplEx
    from src.utils.device_utils import get_device
    import torch

    device = get_device()
    n_ent = len(ent_id)
    n_rel = len(rel_id)
    n_ts  = len(ts_id)
    rank  = args.rank
    # TComplEx sizes: (n_ent, n_rel*2, n_ent, n_timestamps)
    # n_rel*2 because TComplEx adds inverse relations internally
    sizes = (n_ent, n_rel * 2, n_ent, n_ts)
    model_obj = TComplEx(sizes, rank, no_time_emb=False).to(device)
    logger.info("TComplEx initialized from scratch (n_ent=%d, n_rel=%d, n_ts=%d, rank=%d)",
                n_ent, n_rel, n_ts, rank)

    # 6. Wrap into TemporalScorer without loading a checkpoint
    from src.kg_model.temporal.temporal_model import TemporalScorer
    scorer = object.__new__(TemporalScorer)
    scorer.device = str(device)
    scorer.data_path = str(tkbc_dir)
    scorer.ent_id = ent_id
    scorer.rel_id = rel_id
    scorer.ts_id  = ts_id
    scorer.num_entities   = n_ent
    scorer.num_relations  = n_rel
    scorer.num_timestamps = n_ts
    scorer.model = model_obj

    # 7. Train
    scorer.finetune(
        train_data=train_data,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        num_gpus=args.num_gpus,
        use_amp=not args.no_amp,
    )

    # 8. Save checkpoint
    checkpoint_out = (
        args.checkpoint_out
        or os.environ.get("TCOMPLEX_CHECKPOINT")
        or str(tkbc_dir / "tcomplex.ckpt")
    )
    Path(checkpoint_out).parent.mkdir(parents=True, exist_ok=True)
    scorer.save(checkpoint_out)
    logger.info("Done. Checkpoint saved to: %s", checkpoint_out)
    logger.info("Set TCOMPLEX_CHECKPOINT=%s and TCOMPLEX_DATA_PATH=%s in .env",
                checkpoint_out, tkbc_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="Retrain TComplEx temporal scorer")
    parser.add_argument("--tkbc-dir", required=True,
                        help="Path to tkbc pickle directory (created automatically with --from-scratch)")
    parser.add_argument("--checkpoint-out", default=None,
                        help="Output checkpoint path (default: tcomplex.ckpt inside --tkbc-dir)")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch-size", type=int, default=None,
                        help="Batch size (default: auto-calculated from GPU memory)")
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--num-gpus", type=int, default=None,
                        help="Number of GPUs to use (default: auto-detect)")
    parser.add_argument("--no-amp", action="store_true",
                        help="Disable BF16 AMP (use FP32)")

    # --- From-scratch mode (no Wikidata) ---
    parser.add_argument("--from-scratch", action="store_true",
                        help=(
                            "Train new TComplEx from scratch using local JSONL quadruplets. "
                            "No existing checkpoint required. Builds entity/relation/timestamp "
                            "mappings from CQ_/CP_ IDs and saves pickles to --tkbc-dir."
                        ))
    parser.add_argument("--jsonl", default="extract_data/quadruplets.jsonl",
                        help="Path to quadruplets JSONL for --from-scratch "
                             "(default: extract_data/quadruplets.jsonl)")
    parser.add_argument("--rank", type=int, default=128,
                        help="TComplEx embedding rank for --from-scratch (default: 128)")

    args = parser.parse_args()

    if not os.path.isdir(args.tkbc_dir) and not args.from_scratch:
        logger.error("tkbc-dir not found: %s", args.tkbc_dir)
        sys.exit(1)

    # --from-scratch: build everything from JSONL, no existing checkpoint needed
    if args.from_scratch:
        _train_from_scratch(args)
        return

    # --- Fine-tune existing checkpoint ---
    checkpoint_out = (
        args.checkpoint_out
        or os.environ.get("TCOMPLEX_CHECKPOINT")
        or os.path.join(str(Path(__file__).parent.parent), "models/cronkgqa/tcomplex.ckpt")
    )

    logger.info("Loading tkbc data from: %s", args.tkbc_dir)
    logger.info("  epochs=%d  batch_size=%s  lr=%.1e  num_gpus=%s  amp=%s",
                args.epochs, args.batch_size or "auto", args.lr,
                args.num_gpus or "auto", not args.no_amp)

    try:
        from src.kg_model.temporal.temporal_model import TemporalScorer
        from src.utils.device_utils import get_device
        import torch

        device = get_device()
        logger.info("Device: %s", device)

        tcomplex_ckpt = os.environ.get(
            "TCOMPLEX_CHECKPOINT",
            os.path.join(args.tkbc_dir, "tcomplex.ckpt")
        )
        if not os.path.exists(tcomplex_ckpt):
            logger.error("No existing checkpoint found at %s", tcomplex_ckpt)
            logger.error("To train from scratch without Wikidata, use: --from-scratch --jsonl <path>")
            sys.exit(1)

        scorer = TemporalScorer(checkpoint_path=tcomplex_ckpt, device=device)
        logger.info("Loaded TComplEx from %s", tcomplex_ckpt)

        import pickle
        import numpy as np

        train_path = os.path.join(args.tkbc_dir, "train.pickle")
        with open(train_path, "rb") as f:
            train_data = pickle.load(f)

        logger.info("Training rows: %d", len(train_data))
        logger.info("Fine-tuning for %d epochs...", args.epochs)

        if hasattr(scorer, 'finetune'):
            scorer.finetune(
                train_data=train_data,
                epochs=args.epochs,
                batch_size=args.batch_size,
                lr=args.lr,
                num_gpus=args.num_gpus,
                use_amp=not args.no_amp,
            )
        else:
            logger.warning("TemporalScorer has no finetune() method — skipping.")

        if hasattr(scorer, 'save'):
            scorer.save(checkpoint_out)
            logger.info("Checkpoint saved to: %s", checkpoint_out)
        else:
            torch.save(scorer, checkpoint_out)
            logger.info("Scorer saved to: %s", checkpoint_out)

    except Exception as e:
        logger.error("Retrain failed: %s", e)
        raise


if __name__ == "__main__":
    main()
