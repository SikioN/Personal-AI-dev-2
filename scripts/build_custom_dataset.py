"""
build_custom_dataset.py — Инициальное заполнение графа знаний из документов.

Запуск:
    python scripts/build_custom_dataset.py --input /path/to/docs/
    python scripts/build_custom_dataset.py --input /path/to/docs/ --force
    python scripts/build_custom_dataset.py --input /path/to/docs/ --ask "Кто директор?"

ENV (те же, что в .env бота):
    LLM_BACKEND         = deepseek | openai | ollama | qwen | yandexgpt | gigachat
    DEEPSEEK_API_KEY    = sk-...
    OPENAI_API_KEY      = sk-...
    OLLAMA_URL          = http://localhost:11434
    OLLAMA_MODEL        = qwen3:8b
    USE_INMEMORY        = true   (по умолчанию; false = Neo4j + ChromaDB)
    FINETUNED_MODEL_PATH = models/wikidata_finetuned_remote/wikidata_finetuned

Лимит на размер файла: 100 МБ (MAX_FILE_MB). Более крупные файлы пропускаются.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

# ── PYTHONPATH ──────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("build_dataset")

# ── Constant ─────────────────────────────────────────────────────────────────
MAX_FILE_MB = 100
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".txt"}


# ─────────────────────────────────────────────────────────────────────────────

def _check_files(input_dir: str) -> list[Path]:
    """Scan directory, skip files > MAX_FILE_MB, warn about unsupported formats."""
    all_files = list(Path(input_dir).rglob("*"))
    accepted: list[Path] = []
    skipped_size = 0
    skipped_fmt = 0

    for f in all_files:
        if not f.is_file():
            continue
        if f.suffix.lower() not in ALLOWED_EXTENSIONS:
            skipped_fmt += 1
            continue
        size_mb = f.stat().st_size / (1024 ** 2)
        if size_mb > MAX_FILE_MB:
            logger.warning("SKIP (%.1f MB > %d MB limit): %s", size_mb, MAX_FILE_MB, f.name)
            skipped_size += 1
            continue
        accepted.append(f)
        logger.info("  [%.1f MB] %s", size_mb, f.name)

    logger.info(
        "Files: %d accepted | %d too large (>%d MB) | %d unsupported format",
        len(accepted), skipped_size, MAX_FILE_MB, skipped_fmt,
    )
    return accepted


def _load_engine():
    from src.bot.engine_loader import load_engine
    logger.info("[Engine] Loading (USE_INMEMORY=%s)...", os.environ.get("USE_INMEMORY", "true"))
    engine, navigator, kg_model = load_engine()
    logger.info(
        "[Engine] Ready — %s, KG backend: %s",
        type(engine).__name__,
        type(kg_model).__name__ if kg_model else "in-memory",
    )
    return engine, navigator, kg_model


def _ingest(input_dir: str, kg_model, engine, force: bool = False) -> dict:
    """Run the same LLM-based extract → KG ingest pipeline as the bot."""
    from src.pipelines.ingestion.doc_ingestion_service import DocIngestionService

    service = (
        DocIngestionService(kg_model=kg_model)
        if kg_model is not None
        else DocIngestionService(inmemory_engine=engine)
    )

    def _progress(msg: str):
        print(f"  {msg}")

    stats = service.ingest_directory(
        input_dir=input_dir,
        force_retrain=False,
        tkbc_dir=None,
        reprocess=force,
        progress_callback=_progress,
    )
    return stats


def _qa(engine, question: str, top_k: int = 8) -> str:
    """Run a test question against the freshly built KG."""
    logger.info("[QA] %s", question)
    answer = engine.ask(question, top_k=top_k)
    print(f"\n{'='*60}\n>>> ANSWER: {answer}\n{'='*60}\n")
    return answer


# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build a Knowledge Graph dataset from documents and ingest into the QA pipeline.\n"
            f"Supported formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}. "
            f"Max file size: {MAX_FILE_MB} MB."
        )
    )
    parser.add_argument(
        "--input", "-i", required=True, metavar="DIR",
        help="Directory with documents to ingest (PDF, DOCX, PPTX, TXT).",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-process files already marked as ingested (overrides manifest).",
    )
    parser.add_argument(
        "--ask", "-q", metavar="QUESTION",
        help="Run a test QA question on the KG after ingestion.",
    )
    parser.add_argument(
        "--top-k", type=int, default=8,
        help="Number of facts to retrieve for --ask (default: 8).",
    )
    args = parser.parse_args()

    input_dir = args.input
    if not os.path.isdir(input_dir):
        print(f"ERROR: directory not found: {input_dir}")
        sys.exit(1)

    # ── Pre-flight: list accepted files ──────────────────────────────────────
    print(f"\n[SCAN] {input_dir}")
    accepted = _check_files(input_dir)
    if not accepted:
        print("No accepted files found. Add PDF / DOCX / PPTX / TXT files and retry.")
        sys.exit(0)

    print(f"\n[INGEST] Starting extraction + ingestion for {len(accepted)} files...\n")

    # ── Engine init ──────────────────────────────────────────────────────────
    engine, navigator, kg_model = _load_engine()

    # ── Ingest ───────────────────────────────────────────────────────────────
    stats = _ingest(input_dir, kg_model, engine, force=args.force)

    print(
        f"\n[RESULT] "
        f"added={stats['added']} | "
        f"errors={stats['errors']} | "
        f"files_processed={stats['files_processed']} | "
        f"files_skipped={stats.get('files_skipped', 0)}"
    )

    if stats["added"] == 0:
        print(
            "\nHint: if all files were 'already processed', run with --force to reprocess.\n"
            "Hint: check LLM_BACKEND and API keys in .env if extraction returned 0 facts."
        )

    # ── Optional QA test ─────────────────────────────────────────────────────
    if args.ask:
        _qa(engine, args.ask, top_k=args.top_k)


if __name__ == "__main__":
    main()
