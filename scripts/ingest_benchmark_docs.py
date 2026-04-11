#!/usr/bin/env python3
"""
ingest_benchmark_docs.py — Ingest only the 25 PDF documents referenced in the benchmark.

Reads simple_questions_39_final_2025.xlsx, extracts unique PDF names from the
'source_file' column, finds matching files in --docs-dir, and ingests them into
a SEPARATE database at --out-dir (default: data/benchmark_db).

The production database (data/kuzu_db, data/graph_structures/) is NOT touched.

Usage:
    python scripts/ingest_benchmark_docs.py \\
      --docs-dir /path/to/benchmark_pdfs \\
      --out-dir  data/benchmark_db

Then train a separate TComplEx:
    python scripts/export_kuzu_to_jsonl.py \\
      --kuzu-path data/benchmark_db/kuzu_db \\
      --out       data/benchmark_db/quadruplets.jsonl

    python scripts/retrain_tcomplex.py \\
      --from-scratch \\
      --jsonl data/benchmark_db/quadruplets.jsonl \\
      --tkbc-dir data/benchmark_db/tcomplex/ \\
      --checkpoint-out data/benchmark_db/tcomplex.ckpt

Then run the benchmark:
    python scripts/run_benchmark.py \\
      --kuzu-path     data/benchmark_db/kuzu_db \\
      --chroma-nodes  data/benchmark_db/chroma/nodes/default \\
      --chroma-quads  data/benchmark_db/chroma/quads/default \\
      --tcomplex-ckpt data/benchmark_db/tcomplex.ckpt \\
      --tcomplex-data data/benchmark_db/tcomplex/ \\
      --max-facts 20 --top-k 20
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
GREEN  = '\033[0;32m'
YELLOW = '\033[1;33m'
RED    = '\033[0;31m'
BOLD   = '\033[1m'
NC     = '\033[0m'
DIVIDER = f"{BOLD}{'═' * 60}{NC}"

def _ok(msg):   print(f"  {GREEN}[OK]{NC}  {msg}")
def _warn(msg): print(f"  {YELLOW}[WARN]{NC} {msg}")
def _err(msg):  print(f"  {RED}[ERR]{NC}  {msg}")
def _info(msg): print(f"  [--]  {msg}")


def _read_benchmark_filenames(excel_path: str) -> list[str]:
    """Read unique PDF basenames from the benchmark Excel."""
    try:
        import pandas as pd
        df = pd.read_excel(excel_path, engine='openpyxl')
    except Exception as e:
        _err(f"Cannot read {excel_path}: {e}")
        sys.exit(1)

    # Column names as in run_benchmark.py
    df.columns = ['question', 'expected', 'source_file',
                  'context_location', 'context', 'bot_answer_old', 'correct_old']

    names = df['source_file'].dropna().astype(str).str.strip().unique().tolist()
    # Keep only PDF-like names (may already include .pdf or not)
    names = [n for n in names if n and n.lower() != 'nan']
    return names


_SUPPORTED_EXT = {'.pdf', '.txt', '.docx', '.pptx'}


def _match_pdfs(docs_dir: str, benchmark_names: list[str]) -> tuple[list[str], list[str]]:
    """
    For each benchmark name, find the matching file in docs_dir (by basename, any supported ext).
    Returns (found_paths, missing_names).
    """
    # Build index: stem (no ext) → full path, and full filename → full path
    index: dict[str, str] = {}
    for dirpath, _, files in os.walk(docs_dir):
        for fname in files:
            if Path(fname).suffix.lower() in _SUPPORTED_EXT:
                stem = Path(fname).stem.lower()
                full_path = os.path.join(dirpath, fname)
                # stem without extension (highest priority — matches regardless of ext)
                if stem not in index:
                    index[stem] = full_path
                # full filename with extension
                index[fname.lower()] = full_path

    found: list[str] = []
    missing: list[str] = []
    for name in benchmark_names:
        key = name.lower()
        key_stem = Path(name).stem.lower()
        if key in index:
            found.append(index[key])
        elif key_stem in index:
            found.append(index[key_stem])
        else:
            missing.append(name)

    # Deduplicate (same file may match multiple names)
    found = list(dict.fromkeys(found))
    return found, missing


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Ingest benchmark PDFs into a separate database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--docs-dir', required=True,
                        help='Directory containing the benchmark PDF files')
    parser.add_argument('--out-dir', default='data/benchmark_db',
                        help='Root directory for the new DB (default: data/benchmark_db)')
    parser.add_argument('--excel', default='simple_questions_39_final_2025.xlsx',
                        help='Benchmark Excel file (default: simple_questions_39_final_2025.xlsx)')
    parser.add_argument('--workers', type=int, default=None,
                        help='Parallel extraction workers')
    parser.add_argument('--reprocess', action='store_true',
                        help='Re-extract files that were already processed')
    args = parser.parse_args()

    # ── Resolve paths ─────────────────────────────────────────────────────────
    sys.path.insert(0, str(Path(__file__).parent.parent))

    repo_root = Path(__file__).parent.parent
    out_dir = os.path.abspath(args.out_dir)
    docs_dir = os.path.abspath(args.docs_dir)
    excel_path = os.path.abspath(args.excel) if not os.path.isabs(args.excel) else args.excel
    if not os.path.exists(excel_path):
        excel_path = str(repo_root / args.excel)

    # ── Set env vars BEFORE any src imports (QAConfig uses default_factory lambdas) ──
    # env must be set BEFORE load_engine() is called
    os.environ['KUZU_PATH']          = os.path.join(out_dir, 'kuzu_db')
    os.environ['CHROMA_NODES_PATH']  = os.path.join(out_dir, 'chroma', 'nodes', 'default')
    os.environ['CHROMA_QUADS_PATH']  = os.path.join(out_dir, 'chroma', 'quads', 'default')
    os.environ['TCOMPLEX_DATA_PATH'] = os.path.join(out_dir, 'tcomplex')
    os.environ['INGEST_STATS_PATH']  = os.path.join(out_dir, 'ingest_stats.json')

    from dotenv import load_dotenv
    load_dotenv()

    logging.basicConfig(level=logging.WARNING, format='%(levelname)s %(message)s')
    for _log in ('src', 'extract', 'chromadb', 'kuzu', 'sentence_transformers',
                 'transformers', 'urllib3', 'httpx'):
        logging.getLogger(_log).setLevel(logging.ERROR)

    print()
    print(f"{BOLD}====  ingest_benchmark_docs.py  ===={NC}\n")
    print(f"  out-dir   : {out_dir}")
    print(f"  docs-dir  : {docs_dir}")
    print(f"  excel     : {excel_path}")
    print()

    # ── Validate inputs ───────────────────────────────────────────────────────
    if not os.path.isdir(docs_dir):
        _err(f"docs-dir not found: {docs_dir}")
        sys.exit(1)
    if not os.path.exists(excel_path):
        _err(f"Excel not found: {excel_path}")
        sys.exit(1)

    # ── Read benchmark PDF names from Excel ───────────────────────────────────
    benchmark_names = _read_benchmark_filenames(excel_path)
    print(f"  Benchmark references {len(benchmark_names)} unique file(s):")
    for n in sorted(benchmark_names):
        print(f"    · {n}")
    print()

    # ── Match against docs-dir ────────────────────────────────────────────────
    found_files, missing_names = _match_pdfs(docs_dir, benchmark_names)

    if missing_names:
        _warn(f"{len(missing_names)} file(s) NOT found in {docs_dir}:")
        for n in missing_names:
            _warn(f"    missing: {n}")
    _ok(f"Found {len(found_files)} / {len(benchmark_names)} file(s)")
    print()

    if not found_files:
        _err("No files to ingest. Check --docs-dir.")
        sys.exit(1)

    # ── Filter already-processed (unless --reprocess) ────────────────────────
    if not args.reprocess:
        try:
            from extract.extract_quadruplets import (
                _load_processed_manifest, _is_processed,
            )
            _load_processed_manifest()
            new_files = [fp for fp in found_files if not _is_processed(fp)]
            already = len(found_files) - len(new_files)
            if already:
                _info(f"Skipping {already} already-processed file(s) "
                      "(use --reprocess to force re-extraction)")
            found_files = new_files
        except Exception as exc:
            _warn(f"Could not load processed manifest: {exc} — processing all files")

    if not found_files:
        print("  All files already processed. Nothing to do.\n")
        sys.exit(0)

    # ── Ensure output directories exist ───────────────────────────────────────
    for subdir in ['kuzu_db', os.path.join('chroma', 'nodes', 'default'),
                   os.path.join('chroma', 'quads', 'default'), 'tcomplex']:
        Path(os.path.join(out_dir, subdir)).mkdir(parents=True, exist_ok=True)

    # ── Initialize DocIngestionService (uses sandbox paths via env) ───────────
    _info("Initialising KG model for sandbox DB...")
    t0 = time.time()
    try:
        from src.bot.engine_loader import load_engine
        # env must be set BEFORE this call — already done above
        engine, _, kg_model = load_engine()

        from src.pipelines.ingestion.doc_ingestion_service import DocIngestionService
        service = DocIngestionService(
            kg_model=kg_model,
            inmemory_engine=engine if kg_model is None else None,
        )
        _ok(f"KG model ready  ({time.time() - t0:.1f}s)")
    except Exception as exc:
        _err(f"Failed to initialise KG model: {exc}")
        raise

    # ── Parallel extraction ───────────────────────────────────────────────────
    workers = args.workers or min(32, (os.cpu_count() or 4) * 4)
    print(f"\n{DIVIDER}")
    print(f"{BOLD}  [1/2] Extracting facts from {len(found_files)} file(s)"
          f"  (workers={workers}){NC}")
    print(DIVIDER)
    print()

    all_quads: list[dict] = []
    _lock = threading.Lock()
    files_ok = 0
    files_fail = 0
    total_errors = 0
    t1 = time.time()

    def _process_one(fp: str) -> None:
        nonlocal files_ok, files_fail, total_errors
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
        list(pool.map(_process_one, found_files))

    elapsed1 = time.time() - t1
    print()
    _ok(f"Extracted {len(all_quads)} total facts in {elapsed1:.0f}s"
        + (f"  ({files_fail} file(s) failed)" if files_fail else ''))

    if not all_quads:
        print("\n  No facts extracted. Done.\n")
        sys.exit(0)

    # ── Finalize to KuzuDB + ChromaDB ─────────────────────────────────────────
    tkbc_dir = os.environ['TCOMPLEX_DATA_PATH']
    print(f"\n{DIVIDER}")
    print(f"{BOLD}  [2/2] Writing {len(all_quads)} facts → KuzuDB + ChromaDB{NC}")
    print(f"        KuzuDB   : {os.environ['KUZU_PATH']}")
    print(f"        ChromaDB : {os.environ['CHROMA_NODES_PATH']}")
    print(DIVIDER)
    print()

    t2 = time.time()
    try:
        added = service._finalize_ingestion(all_quads, tkbc_dir)
        _ok(f"Saved {added} facts  ({time.time() - t2:.0f}s)")
    except Exception as exc:
        _err(f"Finalize failed: {exc}")
        raise

    # Mark files as processed
    try:
        from extract.extract_quadruplets import _mark_processed, _file_sha256
        for fp in found_files:
            _mark_processed(fp, 0, _file_sha256(fp))
    except Exception:
        pass

    # ── Final summary ─────────────────────────────────────────────────────────
    print()
    print(DIVIDER)
    print(f"{BOLD}  Done — Sandbox DB ready{NC}")
    print(DIVIDER)
    print(f"  Files processed : {files_ok}")
    if files_fail:
        print(f"  Files failed    : {files_fail}")
    print(f"  Facts extracted : {len(all_quads)}")
    print(f"  Facts in new KG : {added}")
    print(f"  KuzuDB path     : {os.environ['KUZU_PATH']}")
    print(f"  ChromaDB (nodes): {os.environ['CHROMA_NODES_PATH']}")
    print()
    print("  Next steps:")
    print(f"    python scripts/export_kuzu_to_jsonl.py \\")
    print(f"      --kuzu-path {os.environ['KUZU_PATH']} \\")
    print(f"      --out       {out_dir}/quadruplets.jsonl")
    print()
    print(f"    python scripts/retrain_tcomplex.py --from-scratch \\")
    print(f"      --jsonl {out_dir}/quadruplets.jsonl \\")
    print(f"      --tkbc-dir {tkbc_dir}/ \\")
    print(f"      --checkpoint-out {out_dir}/tcomplex.ckpt")
    print()
    print(f"    python scripts/run_benchmark.py \\")
    print(f"      --kuzu-path     {os.environ['KUZU_PATH']} \\")
    print(f"      --chroma-nodes  {os.environ['CHROMA_NODES_PATH']} \\")
    print(f"      --chroma-quads  {os.environ['CHROMA_QUADS_PATH']} \\")
    print(f"      --tcomplex-ckpt {out_dir}/tcomplex.ckpt \\")
    print(f"      --tcomplex-data {tkbc_dir}/ \\")
    print(f"      --max-facts 20 --top-k 20")
    print(DIVIDER)
    print()


if __name__ == '__main__':
    main()
