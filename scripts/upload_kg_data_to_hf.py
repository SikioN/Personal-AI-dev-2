#!/usr/bin/env python3
"""
upload_kg_data_to_hf.py — Upload KG raw data and TComplEx checkpoint to HuggingFace Hub.

Usage:
    python scripts/upload_kg_data_to_hf.py \
        --kg-repo  YOUR_USERNAME/personal-ai-kg-data \
        --tcomplex YOUR_USERNAME/personal-ai-tcomplex   # omit if no tcomplex.ckpt

Uploads:
  --kg-repo:   wikidata_big/kg/ (full.txt, entity/relation files, tkbc_processed_data/)
               as a private HF Dataset repo
  --tcomplex:  models/cronkgqa/tcomplex.ckpt as a private HF Model repo
               (skipped silently if the file does not exist)

Requires:
    huggingface-cli login  (or HF_TOKEN env var set)
    pip install huggingface_hub>=0.21.0
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_KG_DIR = os.path.join(ROOT, "wikidata_big", "kg")
DEFAULT_TCOMPLEX_CKPT = os.path.join(ROOT, "models", "cronkgqa", "tcomplex.ckpt")


def main():
    parser = argparse.ArgumentParser(description="Upload KG data + TComplEx to HuggingFace Hub")
    parser.add_argument(
        "--kg-repo", required=True,
        help="HF Dataset repo ID for KG data, e.g. your-username/personal-ai-kg-data",
    )
    parser.add_argument(
        "--kg-dir", default=DEFAULT_KG_DIR,
        help=f"Local KG data folder (default: {DEFAULT_KG_DIR})",
    )
    parser.add_argument(
        "--tcomplex", default=None,
        help="HF Model repo ID for TComplEx checkpoint, e.g. your-username/personal-ai-tcomplex",
    )
    parser.add_argument(
        "--tcomplex-ckpt", default=DEFAULT_TCOMPLEX_CKPT,
        help=f"Local TComplEx checkpoint path (default: {DEFAULT_TCOMPLEX_CKPT})",
    )
    parser.add_argument(
        "--public", action="store_true",
        help="Make repos public (default: private)",
    )
    args = parser.parse_args()

    try:
        from huggingface_hub import HfApi
    except ImportError:
        print("[ERR] huggingface_hub not installed. Run: pip install huggingface_hub>=0.21.0")
        sys.exit(1)

    api = HfApi()
    private = not args.public

    # --- Upload KG data ---
    if not os.path.isdir(args.kg_dir):
        print(f"[ERR] KG data directory not found: {args.kg_dir}")
        sys.exit(1)

    required = ["full.txt", "wd_id2entity_text.txt", "wd_id2relation_text.txt"]
    missing = [f for f in required if not os.path.isfile(os.path.join(args.kg_dir, f))]
    if missing:
        print(f"[WARN] Missing expected KG files: {missing}")
        print("       Uploading whatever is present in the directory.")

    api.create_repo(repo_id=args.kg_repo, repo_type="dataset", private=private, exist_ok=True)
    print(f"Uploading KG data {args.kg_dir} → {args.kg_repo} (private={private}) ...")
    url = api.upload_folder(
        folder_path=args.kg_dir,
        repo_id=args.kg_repo,
        repo_type="dataset",
    )
    print(f"[OK] KG data uploaded: {url}")

    # --- Upload TComplEx checkpoint (optional) ---
    if args.tcomplex:
        if not os.path.isfile(args.tcomplex_ckpt):
            print(f"[SKIP] TComplEx checkpoint not found at {args.tcomplex_ckpt} — skipping upload.")
        else:
            api.create_repo(repo_id=args.tcomplex, repo_type="model", private=private, exist_ok=True)
            print(f"Uploading TComplEx {args.tcomplex_ckpt} → {args.tcomplex} (private={private}) ...")
            url = api.upload_file(
                path_or_fileobj=args.tcomplex_ckpt,
                path_in_repo="tcomplex.ckpt",
                repo_id=args.tcomplex,
                repo_type="model",
            )
            print(f"[OK] TComplEx uploaded: {url}")

    print()
    print("Set these env vars on Railway (Variables tab):")
    print(f"  HF_KG_DATA_REPO={args.kg_repo}")
    if args.tcomplex:
        print(f"  HF_TCOMPLEX_REPO={args.tcomplex}")
    print("  KG_DATA_PATH=/app/data/wikidata_big/kg")
    print("  TCOMPLEX_CHECKPOINT=/app/data/models/cronkgqa/tcomplex.ckpt")


if __name__ == "__main__":
    main()
