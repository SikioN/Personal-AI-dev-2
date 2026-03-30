#!/usr/bin/env python3
"""
ingest_directory.py — Batch-ingest documents from a directory.

Scans --dir for PDF/DOCX/PPTX/TXT files, extracts facts via LLM in parallel,
writes to KuzuDB + ChromaDB, then optionally retrains TComplEx.

GPU-adaptive: A100 80 GB → A100 40 GB → A30/A10 → A4/T4 → CPU.

Usage:
    python scripts/ingest_directory.py --dir /path/to/docs [options]

See --help for all options.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import logging
import os
import sys
import threading
import time
from pathlib import Path

# ─── Color codes ──────────────────────────────────────────────────────────────
RED    = '\033[0;31m'
GREEN  = '\033[0;32m'
YELLOW = '\033[1;33m'
BOLD   = '\033[1m'
NC     = '\033[0m'

DIVIDER = f"{BOLD}{'═' * 58}{NC}"

def _ok(msg: str)   -> None: print(f"  {GREEN}[OK]{NC}  {msg}")
def _warn(msg: str) -> None: print(f"  {YELLOW}[WARN]{NC} {msg}")
def _err(msg: str)  -> None: print(f"  {RED}[ERR]{NC}  {msg}")
def _info(msg: str) -> None: print(f"  [--]  {msg}")


# ─── GPU tier table ───────────────────────────────────────────────────────────
# (min_vram_gb, tier_name, embed_batch, amp)
# embed_batch: batch size for ChromaDB/E5 embedding inference
# amp        : 'bf16' | 'fp16' | None
_TIER_TABLE = [
    (70, 'ultra', 1024, 'bf16'),   # A100 80 GB, H100
    (36, 'high',   512, 'bf16'),   # A100 40 GB, A6000
    (20, 'mid',    256, 'bf16'),   # A30, A10G
    ( 8, 'low',    128, 'fp16'),   # A4, T4, RTX 3070
    ( 0, 'tiny',    64,  None),    # small GPU / CPU fallback
]


def _detect_gpu_profile() -> dict:
    """Return GPU profile dict; never raises."""
    try:
        import torch
    except ImportError:
        return {
            'is_gpu': False, 'tier': 'cpu', 'embed_batch': 64,
            'amp': None, 'num_gpus': 0,
        }

    if torch.cuda.is_available():
        props    = torch.cuda.get_device_properties(0)
        vram_gb  = props.total_memory / 1e9
        num_gpus = torch.cuda.device_count()
        bf16_ok  = torch.cuda.is_bf16_supported()

        tier, embed_batch, amp = 'tiny', 64, None
        for min_vram, t, eb, a in _TIER_TABLE:
            if vram_gb >= min_vram:
                tier, embed_batch, amp = t, eb, a
                break
        if amp == 'bf16' and not bf16_ok:
            amp = 'fp16'

        return {
            'is_gpu':      True,
            'backend':     'cuda',
            'tier':        tier,
            'embed_batch': embed_batch,
            'amp':         amp,
            'num_gpus':    num_gpus,
            'name':        props.name,
            'vram_gb':     round(vram_gb, 1),
            'bf16':        bf16_ok,
        }

    mps = getattr(getattr(torch, 'backends', None), 'mps', None)
    if mps and mps.is_available():
        return {
            'is_gpu':      True,
            'backend':     'mps',
            'tier':        'mps',
            'embed_batch': 128,
            'amp':         None,
            'num_gpus':    1,
            'name':        'Apple Silicon (MPS)',
            'vram_gb':     None,
            'bf16':        False,
        }

    return {
        'is_gpu': False, 'backend': 'cpu', 'tier': 'cpu',
        'embed_batch': 64, 'amp': None, 'num_gpus': 0,
    }


def _print_device_banner(profile: dict) -> None:
    print(DIVIDER)
    if profile['is_gpu']:
        name    = profile.get('name', 'GPU')
        vram    = f"  {profile['vram_gb']} GB VRAM" if profile.get('vram_gb') else ''
        n       = profile.get('num_gpus', 1)
        tier    = profile['tier']
        amp_str = profile.get('amp') or 'fp32'
        multi   = f"  ·  {n} GPUs (DataParallel)" if n > 1 else ''
        print(f"  {GREEN}{BOLD}[GPU]{NC}  {name}{vram}{multi}")
        print(f"        tier={tier}  AMP={amp_str}  embed_batch={profile['embed_batch']}")
    else:
        print(f"  {RED}{BOLD}[CPU]{NC}  No CUDA/MPS GPU detected — running on CPU (slow)")
    print(DIVIDER)
    print()


# ─── Directory scanner ────────────────────────────────────────────────────────
_SUPPORTED_EXT = {'.pdf', '.docx', '.pptx', '.txt'}


def _scan_directory(root: str) -> tuple[list[str], list[str]]:
    """Return (supported_files, unsupported_files), sorted."""
    valid: list[str] = []
    skipped: list[str] = []
    for dirpath, _dirs, files in os.walk(root):
        for fname in sorted(files):
            if fname.startswith('.'):
                continue
            fp  = os.path.join(dirpath, fname)
            ext = Path(fname).suffix.lower()
            (valid if ext in _SUPPORTED_EXT else skipped).append(fp)
    return valid, skipped


# ─── Main ─────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description='Batch-ingest documents → KuzuDB + ChromaDB + TComplEx retrain',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--dir', required=True,
                        help='Directory containing documents to ingest')
    parser.add_argument('--tkbc-dir', default=None,
                        help='TKBC pickle directory for TComplEx retrain '
                             '(default: $TCOMPLEX_DATA_PATH)')
    parser.add_argument('--workers', type=int, default=None,
                        help='Parallel extraction workers (default: min(32, cpu*4))')
    parser.add_argument('--epochs', type=int, default=50,
                        help='TComplEx retrain epochs (default: 50)')
    parser.add_argument('--lr', type=float, default=1e-3,
                        help='TComplEx learning rate (default: 1e-3)')
    parser.add_argument('--skip-retrain', action='store_true',
                        help='Skip TComplEx retrain')
    parser.add_argument('--no-amp', action='store_true',
                        help='Disable BF16/FP16 AMP (force FP32)')
    parser.add_argument('--reprocess', action='store_true',
                        help='Re-extract files that were already processed')
    args = parser.parse_args()

    # ── Bootstrap path + env ──────────────────────────────────────────────────
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from dotenv import load_dotenv
    load_dotenv()

    logging.basicConfig(level=logging.WARNING, format='%(levelname)s %(message)s')
    # Silence verbose library loggers — the script drives its own UX
    for _log in ('src', 'extract', 'chromadb', 'kuzu', 'sentence_transformers',
                 'transformers', 'urllib3', 'httpx'):
        logging.getLogger(_log).setLevel(logging.ERROR)

    # ── Device banner ─────────────────────────────────────────────────────────
    gpu_profile = _detect_gpu_profile()
    print()
    print(f"{BOLD}====  ingest_directory.py  ===={NC}\n")
    _print_device_banner(gpu_profile)

    # ── Validate directory ────────────────────────────────────────────────────
    doc_dir = os.path.abspath(args.dir)
    if not os.path.isdir(doc_dir):
        _err(f"Directory not found: {doc_dir}")
        sys.exit(1)

    valid_files, skipped_files = _scan_directory(doc_dir)
    for fp in skipped_files:
        _warn(f"Unsupported format — skipped: {Path(fp).name}")

    if not valid_files:
        _err(f"No supported files (.pdf/.docx/.pptx/.txt) in: {doc_dir}")
        sys.exit(1)

    print(f"  Found {len(valid_files)} supported file(s)"
          + (f"  (skipped {len(skipped_files)} unsupported)" if skipped_files else ""))
    print()

    # ── Filter already-processed files ───────────────────────────────────────
    if not args.reprocess:
        try:
            from extract.extract_quadruplets import (
                _load_processed_manifest, _is_processed,
            )
            _load_processed_manifest()
            new_files = [fp for fp in valid_files if not _is_processed(fp)]
            already = len(valid_files) - len(new_files)
            if already:
                _info(f"Skipping {already} already-processed file(s) "
                      "(pass --reprocess to force re-extraction)")
            valid_files = new_files
        except Exception as exc:
            _warn(f"Could not load processed manifest: {exc} — processing all files")

    if not valid_files:
        print("  All files already processed. Nothing to do.\n")
        sys.exit(0)

    # ── Initialize DocIngestionService ────────────────────────────────────────
    _info("Initialising KG model (first run may take a minute)...")
    t0 = time.time()
    try:
        from src.bot.engine_loader import load_engine
        engine, _, kg_model = load_engine()

        # If the production engine failed due to a KuzuDB lock, abort immediately.
        # Silently falling back to in-memory would save facts to a stash file
        # instead of KuzuDB, causing silent data loss.
        if kg_model is None and os.environ.get('USE_INMEMORY', 'false').lower() != 'true':
            raise RuntimeError(
                "Production engine failed to load — KuzuDB is likely locked by another process.\n"
                "  Stop the bot first:  pkill -f 'run_db\\|bot.py'\n"
                "  Then re-run:         bash setup.sh --build-kg --reprocess"
            )

        from src.pipelines.ingestion.doc_ingestion_service import DocIngestionService
        service = DocIngestionService(
            kg_model=kg_model,
            inmemory_engine=engine if kg_model is None else None,
        )
        _ok(f"KG model ready  ({time.time() - t0:.1f}s)")
    except Exception as exc:
        _err(f"Failed to initialise KG model: {exc}")
        raise

    # ── Step 1: Parallel extraction ───────────────────────────────────────────
    workers = args.workers or min(32, (os.cpu_count() or 4) * 4)
    print(f"\n{DIVIDER}")
    print(f"{BOLD}  [1/3] Extracting facts from {len(valid_files)} file(s)"
          f"  (workers={workers}){NC}")
    print(DIVIDER)
    print()

    all_quads: list[dict] = []
    _lock = threading.Lock()
    total_errors = 0
    files_ok     = 0
    files_fail   = 0
    t1 = time.time()

    def _process_one(fp: str) -> None:
        nonlocal total_errors, files_ok, files_fail
        fname = Path(fp).name
        try:
            res   = service.ingest_file(fp, progress_callback=None)
            quads = res.get('quadruplets', [])
            errs  = res.get('errors', 0)
            with _lock:
                all_quads.extend(quads)
                total_errors += errs
                if quads or not errs:
                    files_ok += 1
                else:
                    files_fail += 1
            suffix = f"  ({errs} chunk errors)" if errs else ''
            _ok(f"{fname}  →  {len(quads)} facts{suffix}")
        except Exception as exc:
            with _lock:
                files_fail += 1
            _warn(f"Skipped {fname}: {exc}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(_process_one, valid_files))

    elapsed1 = time.time() - t1
    print()
    _ok(f"Extracted {len(all_quads)} total facts in {elapsed1:.0f}s"
        + (f"  ({files_fail} file(s) failed)" if files_fail else ''))

    if not all_quads:
        print("\n  No facts extracted. Done.\n")
        sys.exit(0)

    # ── Step 2: Finalize to KuzuDB + ChromaDB ─────────────────────────────────
    tkbc_dir = args.tkbc_dir or os.environ.get('TCOMPLEX_DATA_PATH')
    print(f"\n{DIVIDER}")
    print(f"{BOLD}  [2/3] Writing {len(all_quads)} facts → KuzuDB + ChromaDB{NC}")
    print(DIVIDER)
    print()

    t2 = time.time()
    try:
        added = service._finalize_ingestion(all_quads, tkbc_dir)
        _ok(f"Saved {added} facts  ({time.time() - t2:.0f}s)")
    except Exception as exc:
        _err(f"Finalize failed: {exc}")
        raise

    # Mark files as processed so they are skipped on next run
    try:
        from extract.extract_quadruplets import _mark_processed, _file_sha256
        for fp in valid_files:
            _mark_processed(fp, 0, _file_sha256(fp))
    except Exception:
        pass

    # ── Step 3: TComplEx retrain ──────────────────────────────────────────────
    print(f"\n{DIVIDER}")
    print(f"{BOLD}  [3/3] TComplEx retrain{NC}")
    print(DIVIDER)
    print()

    if args.skip_retrain:
        _info("--skip-retrain: skipping TComplEx retrain")
    elif added == 0:
        _info("No new facts added — TComplEx retrain not needed")
    else:
        try:
            _run_tcomplex_retrain(tkbc_dir, args, gpu_profile)
        except Exception as exc:
            _warn(f"TComplEx retrain failed: {exc}")
            _warn("Ingestion succeeded. Run retrain manually:")
            _warn(f"  python scripts/retrain_tcomplex.py --tkbc-dir {tkbc_dir or '<dir>'}"
                  f" --epochs {args.epochs}")

    # ── Final status ──────────────────────────────────────────────────────────
    from src.pipelines.ingestion.doc_ingestion_service import get_ingest_stats
    stats       = get_ingest_stats()
    total_in_kg = stats.get('total_facts', '?')
    since_rt    = stats.get('facts_since_last_retrain', 0)

    print()
    print(DIVIDER)
    print(f"{BOLD}  Result{NC}")
    print(DIVIDER)
    print(f"  Files processed      : {files_ok}")
    if files_fail:
        print(f"  Files failed         : {files_fail}")
    print(f"  Facts extracted      : {len(all_quads)}")
    print(f"  Facts added to KG    : {added}")
    print(f"  Total facts in KG    : {total_in_kg}")
    if since_rt and not args.skip_retrain:
        print(f"  Since last retrain   : {since_rt}"
              + ("  ✓ retrained" if not args.skip_retrain and added > 0 else ''))
    print(DIVIDER)
    print()


def _run_tcomplex_retrain(tkbc_dir: str | None, args, gpu_profile: dict) -> None:
    """Run TComplEx finetune with GPU-adaptive settings."""
    if not tkbc_dir:
        _warn("TCOMPLEX_DATA_PATH not set and --tkbc-dir not provided — skipping")
        return
    if not os.path.isdir(tkbc_dir):
        _warn(f"tkbc-dir not found: {tkbc_dir} — skipping")
        return

    train_path = os.path.join(tkbc_dir, 'train.pickle')
    if not os.path.exists(train_path):
        _warn(f"train.pickle not found in {tkbc_dir} — skipping")
        return

    import pickle
    from src.kg_model.temporal.temporal_model import TemporalScorer
    from src.utils.device_utils import get_device
    import torch

    # Checkpoint path
    ckpt = os.environ.get(
        'TCOMPLEX_CHECKPOINT',
        str(Path(__file__).parent.parent / 'models' / 'cronkgqa' / 'tcomplex.ckpt'),
    )
    if not os.path.exists(ckpt):
        _warn(f"TComplEx checkpoint not found: {ckpt} — skipping")
        return

    device = get_device(verbose=False)
    _ok(f"Loading TComplEx from {ckpt}  (device={device})")
    scorer = TemporalScorer(checkpoint_path=ckpt, device=device)

    # Derive AMP and multi-GPU flags from profile
    use_amp  = not args.no_amp and gpu_profile.get('amp') is not None
    num_gpus = gpu_profile.get('num_gpus') if gpu_profile['is_gpu'] else None
    if num_gpus == 0:
        num_gpus = None

    with open(train_path, 'rb') as fh:
        train_data = pickle.load(fh)

    _ok(f"Training rows: {len(train_data):,}  epochs={args.epochs}"
        f"  lr={args.lr}  AMP={use_amp}  GPUs={num_gpus or 'auto'}")

    t0 = time.time()
    scorer.finetune(
        train_data=train_data,
        epochs=args.epochs,
        batch_size=None,     # auto-computed from GPU memory inside finetune()
        lr=args.lr,
        num_gpus=num_gpus,
        use_amp=use_amp,
    )
    elapsed = time.time() - t0

    # Save checkpoint
    out_ckpt = ckpt
    torch.save(scorer.model.state_dict(), out_ckpt)
    _ok(f"Retrain done in {elapsed:.0f}s — checkpoint saved: {out_ckpt}")

    # Reset counter
    from src.pipelines.ingestion.doc_ingestion_service import reset_facts_since_retrain
    reset_facts_since_retrain()


if __name__ == '__main__':
    main()
