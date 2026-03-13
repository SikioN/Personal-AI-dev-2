#!/usr/bin/env python3
"""
upload_model_to_hf.py — Upload finetuned E5 model to HuggingFace Hub (one-time, local step).

Usage:
    python scripts/upload_model_to_hf.py --repo YOUR_HF_USERNAME/wikidata-e5-finetuned [--public]

Requires:
    huggingface-cli login  (or HF_TOKEN env var set)
    pip install huggingface_hub  (transitively installed via sentence-transformers)
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DEFAULT_LOCAL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "models/wikidata_finetuned_remote/wikidata_finetuned",
)


def main():
    parser = argparse.ArgumentParser(description="Upload finetuned E5 model to HuggingFace Hub")
    parser.add_argument(
        "--repo", required=True,
        help="HuggingFace repo ID, e.g. your-username/wikidata-e5-finetuned",
    )
    parser.add_argument(
        "--local-path", default=DEFAULT_LOCAL_PATH,
        help=f"Local model folder (default: {DEFAULT_LOCAL_PATH})",
    )
    parser.add_argument(
        "--public", action="store_true",
        help="Make the repo public (default: private)",
    )
    args = parser.parse_args()

    if not os.path.isdir(args.local_path):
        print(f"[ERR] Local model path not found: {args.local_path}")
        sys.exit(1)

    config_json = os.path.join(args.local_path, "config.json")
    if not os.path.isfile(config_json):
        print(f"[ERR] config.json missing at {args.local_path} — is this a valid model directory?")
        sys.exit(1)

    try:
        from huggingface_hub import HfApi
    except ImportError:
        print("[ERR] huggingface_hub not installed. Run: pip install huggingface_hub")
        sys.exit(1)

    api = HfApi()
    private = not args.public

    api.create_repo(repo_id=args.repo, repo_type="model", private=private, exist_ok=True)
    print(f"Uploading {args.local_path} → {args.repo} (private={private}) ...")
    url = api.upload_folder(
        folder_path=args.local_path,
        repo_id=args.repo,
        repo_type="model",
    )
    print(f"[OK] Uploaded: {url}")
    print()
    print("Set in .env on the server:")
    print(f"  FINETUNED_MODEL_PATH=models/wikidata_finetuned_remote/wikidata_finetuned")
    print()
    print("Download on server with:")
    print("  source .venv/bin/activate")
    print(f'  python -c "from sentence_transformers import SentenceTransformer; '
          f'SentenceTransformer(\'{args.repo}\').save('
          f'\'models/wikidata_finetuned_remote/wikidata_finetuned\')"')


if __name__ == "__main__":
    main()
