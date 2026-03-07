#!/usr/bin/env python3
"""
retrain_tcomplex.py — Wrapper to retrain TComplEx temporal scorer after ingestion.

Usage:
    python scripts/retrain_tcomplex.py \\
        --tkbc-dir wikidata_big/kg/tkbc_processed_data/wikidata_big/ \\
        [--epochs 50] [--batch-size 1000] [--lr 1e-3]
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Retrain TComplEx temporal scorer")
    parser.add_argument("--tkbc-dir", required=True, help="Path to tkbc pickle directory")
    parser.add_argument("--checkpoint-out", default=None,
                        help="Output checkpoint path (default: tcomplex_retrained.ckpt in tkbc-dir)")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--lr", type=float, default=1e-3)
    args = parser.parse_args()

    if not os.path.isdir(args.tkbc_dir):
        logger.error("tkbc-dir not found: %s", args.tkbc_dir)
        sys.exit(1)

    checkpoint_out = args.checkpoint_out or os.path.join(args.tkbc_dir, "tcomplex_retrained.ckpt")

    logger.info("Loading tkbc data from: %s", args.tkbc_dir)
    logger.info("  epochs=%d  batch_size=%d  lr=%.1e", args.epochs, args.batch_size, args.lr)

    try:
        from src.kg_model.temporal.temporal_model import TemporalScorer
        from src.utils.device_utils import get_device
        import torch

        device = get_device()
        logger.info("Device: %s", device)

        # Load existing checkpoint to get model dimensions
        tcomplex_ckpt = os.environ.get(
            "TCOMPLEX_CHECKPOINT",
            os.path.join(args.tkbc_dir, "tcomplex.ckpt")
        )
        if not os.path.exists(tcomplex_ckpt):
            logger.warning("No existing checkpoint found at %s — training from scratch not supported yet.", tcomplex_ckpt)
            logger.warning("Please run the full tkbc training pipeline (kaggle_job/) to create an initial checkpoint.")
            sys.exit(1)

        scorer = TemporalScorer(checkpoint_path=tcomplex_ckpt, device=device)
        logger.info("Loaded TComplEx from %s", tcomplex_ckpt)

        # Fine-tune on new train.pickle rows
        import pickle
        import numpy as np

        train_path = os.path.join(args.tkbc_dir, "train.pickle")
        with open(train_path, "rb") as f:
            train_data = pickle.load(f)

        logger.info("Training rows: %d", len(train_data))
        logger.info("Fine-tuning for %d epochs...", args.epochs)

        # Call the fine-tune method if available
        if hasattr(scorer, 'finetune'):
            scorer.finetune(
                train_data=train_data,
                epochs=args.epochs,
                batch_size=args.batch_size,
                lr=args.lr,
            )
        else:
            logger.warning("TemporalScorer has no finetune() method — skipping.")

        # Save updated checkpoint
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
