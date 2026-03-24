"""
doc_ingestion_service.py — Bridge: extract/ → TemporalKGIngester → engine.

Supports both in-memory and production (Neo4j + ChromaDB) modes.
LLM backend is read from the project-standard LLM_BACKEND env var.
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# Path for persisting facts across in-memory restarts
_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
STASH_PATH = os.path.join(_ROOT_DIR, "data", "inmemory_stash.json")
INGEST_STATS_PATH = os.path.join(_ROOT_DIR, "data", "ingest_stats.json")


def _load_stash() -> list[dict]:
    if not os.path.exists(STASH_PATH):
        return []
    try:
        with open(STASH_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _append_stash(quadruplets: list[dict]) -> None:
    """Append new quadruplets to the stash file (idempotent on empty list)."""
    if not quadruplets:
        return
    os.makedirs(os.path.dirname(STASH_PATH), exist_ok=True)
    stash = _load_stash()
    stash.extend(quadruplets)
    with open(STASH_PATH, "w", encoding="utf-8") as f:
        json.dump(stash, f, ensure_ascii=False)


def _update_ingest_stats(added: int) -> None:
    """Increment running total of user-ingested facts."""
    os.makedirs(os.path.dirname(INGEST_STATS_PATH), exist_ok=True)
    try:
        if os.path.exists(INGEST_STATS_PATH):
            with open(INGEST_STATS_PATH, encoding="utf-8") as f:
                stats = json.load(f)
        else:
            stats = {"total_facts": 0}
        stats["total_facts"] = stats.get("total_facts", 0) + added
        with open(INGEST_STATS_PATH, "w", encoding="utf-8") as f:
            json.dump(stats, f)
    except Exception as e:
        logger.warning("Could not update ingest stats: %s", e)


def get_ingested_facts_count() -> int:
    """Return total number of user-ingested facts (from stats file)."""
    try:
        if os.path.exists(INGEST_STATS_PATH):
            with open(INGEST_STATS_PATH, encoding="utf-8") as f:
                return json.load(f).get("total_facts", 0)
    except Exception:
        pass
    return 0


class DocIngestionService:
    """
    Full extract → ingest pipeline.

    Exactly one of ``kg_model`` (production) or ``inmemory_engine`` must be set.
    """

    def __init__(self, kg_model=None, inmemory_engine=None):
        if kg_model is None and inmemory_engine is None:
            raise ValueError("Provide either kg_model or inmemory_engine.")
        self._kg_model = kg_model
        self._inmemory_engine = inmemory_engine

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def ingest_directory(
        self,
        input_dir: str,
        force_retrain: bool = False,
        tkbc_dir: Optional[str] = None,
        reprocess: bool = False,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> dict:
        """
        Full pipeline: read docs → extract quads → ingest.

        Returns:
            {added, skipped, errors, files_processed, files_skipped}
        """
        try:
            from extract.extract_quadruplets import (
                collect_documents,
                fetch_all_wikidata_properties,
                build_quadruplet,
                deduplicate,
                _load_processed_manifest,
                _is_processed,
                _mark_processed,
                _load_custom_registry,
                _load_prop_llm_cache,
                extract_with_ollama,
                extract_with_openai,
            )
        except ImportError:
            raise RuntimeError(
                "Module 'extract' not found. Please ensure the 'extract/' folder is in your PYTHONPATH."
            )

        if not os.path.isdir(input_dir):
            logger.warning("Input dir not found: %s", input_dir)
            return {"added": 0, "skipped": 0, "errors": 0,
                    "files_processed": 0, "files_skipped": 0}

        # Initialise caches
        _load_processed_manifest()
        _load_custom_registry()
        _load_prop_llm_cache()

        prop_map = fetch_all_wikidata_properties(use_cache=True)

        llm_caller = self._make_llm_caller()

        documents = collect_documents(input_dir)
        if not reprocess:
            new_docs = [(fp, txt) for fp, txt in documents if not _is_processed(fp)]
        else:
            new_docs = documents
        files_skipped = len(documents) - len(new_docs)

        if not new_docs:
            logger.info("No new documents to process in %s", input_dir)
            return {"added": 0, "skipped": 0, "errors": 0,
                    "files_processed": 0, "files_skipped": files_skipped}

        all_quads: list[dict] = []
        errors_total = 0
        files_processed = 0

        for fp, txt in new_docs:
            res = self.ingest_file(fp, txt, tkbc_dir=tkbc_dir, progress_callback=progress_callback)
            quads = res.get("quadruplets", [])
            all_quads.extend(quads)
            errors_total += res.get("errors", 0)
            if quads or not res.get("errors"):
                files_processed += 1
            # In batch mode mark after extraction (KG write is one batch for all files)
            _mark_processed(fp, len(quads))
            logger.info("[DocIngestionService] File %s: Extracted %d facts", Path(fp).name, len(quads))

        added = self._finalize_ingestion(all_quads, tkbc_dir, progress_callback)

        return {
            "added": added,
            "skipped": 0,
            "errors": errors_total,
            "files_processed": files_processed,
            "files_skipped": files_skipped,
        }

    def ingest_file(
        self,
        filepath: str,
        text: Optional[str] = None,
        tkbc_dir: Optional[str] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> dict:
        """
        Extract facts from a single file and (optionally) finalize ingestion.
        If called standalone, it will also save to KG.
        """
        try:
            from extract.extract_quadruplets import (
                fetch_all_wikidata_properties,
                build_quadruplet,
                deduplicate,
                _load_processed_manifest,
                _load_custom_registry,
                _load_prop_llm_cache,
                extract_with_ollama,
                extract_with_openai,
            )
        except ImportError:
            raise RuntimeError(
                "Module 'extract' not found. Please ensure the 'extract/' folder is in your PYTHONPATH."
            )

        fname = Path(filepath).name
        try:
            # Ensure caches are ready (inside try so any IO error is caught)
            _load_processed_manifest()
            _load_custom_registry()
            _load_prop_llm_cache()

            if text is None:
                from extract.extract_quadruplets import read_document
                text = read_document(filepath)  # fitz/docx/pptx/txt — correct parsing
                if text is None:
                    logger.warning("[DocIngestionService] Cannot read file: %s", filepath)
                    return {"quadruplets": [], "added": 0, "errors": 1}
                if len(text.strip()) == 0:
                    logger.warning("[DocIngestionService] Extracted text from %s is EMPTY. Could be a scanned PDF without OCR.", fname)
                    return {"quadruplets": [], "added": 0, "errors": 1}
                logger.info("[DocIngestionService] Read %s — %d chars", fname, len(text))

            prop_map = fetch_all_wikidata_properties(use_cache=True)
            llm_caller = self._make_llm_caller()

            llm_backend = os.environ.get("LLM_BACKEND", "deepseek").lower()
            llm_model = self._get_llm_model(llm_backend)
            llm_api_key = self._get_llm_api_key(llm_backend)
            llm_base_url = self._get_llm_base_url(llm_backend)

            logger.info("[DocIngestionService] Using LLM backend=%s model=%s", llm_backend, llm_model)
            if progress_callback:
                progress_callback(f"Извлечение фактов из {fname}...")

            api_chunk_errors = 0
            if llm_backend == "ollama":
                raw_quads = extract_with_ollama(text, model=llm_model)
            elif llm_backend in ("openai", "deepseek", "chatgpt", "qwen", "compatible"):
                raw_quads, api_chunk_errors = extract_with_openai(
                    text,
                    api_key=llm_api_key,
                    model=llm_model,
                    base_url=llm_base_url,
                    workers=4,
                )
            else:
                raw_quads = extract_with_ollama(text, model=llm_model)

            logger.info("[DocIngestionService] LLM returned %d raw quads, %d chunk errors",
                        len(raw_quads), api_chunk_errors)

            built = []
            for raw in raw_quads:
                try:
                    q = build_quadruplet(raw, prop_map, llm_caller)
                    if q:
                        built.append(q)
                except Exception as e:
                    logger.debug("build_quadruplet error: %s", e)

            logger.info("[DocIngestionService] LLM found %d candidates, %d normalized successfully", len(raw_quads), len(built))

            deduped = deduplicate(built)
            build_errors = len(raw_quads) - len(built) if raw_quads else 0
            return {
                "quadruplets": deduped,
                "added": len(deduped),
                "errors": build_errors + api_chunk_errors,
            }

        except Exception as e:
            logger.error("[DocIngestionService] Failed to process %s: %s", filepath, e, exc_info=True)
            return {"quadruplets": [], "added": 0, "errors": 1}

    def ingest_single_file(
        self,
        filepath: str,
        tkbc_dir: Optional[str] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> dict:
        """Extract facts from one file and persist to KG immediately.
        Returns dict with keys: added (int), errors (int).
        """
        result = self.ingest_file(filepath, tkbc_dir=tkbc_dir, progress_callback=progress_callback)
        quads = result.get("quadruplets", [])
        extraction_errors = result.get("errors", 0)
        if not quads:
            return {"added": 0, "errors": extraction_errors, "quadruplets": []}
        added = self._finalize_ingestion(quads, tkbc_dir, progress_callback)
        # Mark ONLY after facts are actually written to KG
        if added > 0:
            from extract.extract_quadruplets import _mark_processed
            _mark_processed(filepath, added)
        return {"added": added, "errors": extraction_errors, "quadruplets": quads}

    def _finalize_ingestion(self, all_quadruplets: list[dict], tkbc_dir: Optional[str], progress_callback=None) -> int:
        if not all_quadruplets:
            return 0

        if progress_callback:
            progress_callback(f"Сохранение {len(all_quadruplets)} фактов в граф...")

        if self._inmemory_engine is not None:
            logger.info("[DocIngestionService] Finalizing ingestion to IN-MEMORY stash.")
            added = self._ingest_to_inmemory(all_quadruplets)
        else:
            logger.info("[DocIngestionService] Finalizing ingestion to PRODUCTION Graph (Kuzu/Neo4j) + VectorDB.")
            result = self._ingest_to_production(all_quadruplets, tkbc_dir)
            added = result.added

        _update_ingest_stats(added)
        return added

    # ------------------------------------------------------------------
    # LLM bridge
    # ------------------------------------------------------------------

    def _make_llm_caller(self) -> Optional[Callable[[str], str]]:
        """Build llm_caller compatible with extract_quadruplets using project LLM client."""
        from src.bot.engine_loader import _make_llm_client
        llm_client = _make_llm_client()
        if llm_client is None:
            return None
        return lambda prompt: llm_client.generate(prompt)

    def _get_llm_model(self, backend: str) -> str:
        models = {
            "ollama": os.environ.get("OLLAMA_MODEL", "qwen3:8b"),
            "deepseek": os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
            "openai": os.environ.get("OPENAI_MODEL", "gpt-4o"),
            "chatgpt": os.environ.get("OPENAI_MODEL", "gpt-4o"),
            "qwen": os.environ.get("QWEN_MODEL", "qwen-plus"),
            "yandexgpt": os.environ.get("YANDEX_MODEL", "yandexgpt"),
            "gigachat": os.environ.get("GIGACHAT_MODEL", "GigaChat"),
        }
        return models.get(backend, "gpt-4o")

    def _get_llm_api_key(self, backend: str) -> str:
        keys = {
            "deepseek": os.environ.get("DEEPSEEK_API_KEY", ""),
            "openai": os.environ.get("OPENAI_API_KEY", ""),
            "chatgpt": os.environ.get("OPENAI_API_KEY", ""),
            "qwen": os.environ.get("QWEN_API_KEY", ""),
        }
        return keys.get(backend, "")

    def _get_llm_base_url(self, backend: str) -> Optional[str]:
        if backend == "deepseek":
            return os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        if backend in ("openai", "chatgpt"):
            return os.environ.get("OPENAI_BASE_URL") or None
        if backend == "qwen":
            return "https://dashscope.aliyuncs.com/compatible-mode/v1"
        return None

    # ------------------------------------------------------------------
    # Ingestion backends
    # ------------------------------------------------------------------

    def _ingest_to_inmemory(self, quadruplets: list[dict]) -> int:
        """Update in-memory engine and persist to stash for restart survival."""
        engine = self._inmemory_engine
        new_tuples = [
            (
                q["s"]["name"], q["r"]["name"], q["o"]["name"],
                q["t"]["prop"].get("start", "unknown"),
            )
            for q in quadruplets
        ]
        new_texts = [f"{s} -- {r} --> {o} (time: {t})" for s, r, o, t in new_tuples]

        engine.raw_quads.extend(new_tuples)
        engine.quad_texts.extend(new_texts)

        if engine.embeddings is not None and engine._embedder is not None:
            import numpy as np
            new_embs = engine._embedder.encode(
                ["passage: " + t for t in new_texts],
                batch_size=64, normalize_embeddings=True,
            )
            if getattr(engine.embeddings, "size", 0) == 0 or getattr(engine.embeddings, "ndim", 1) == 1:
                engine.embeddings = new_embs
            else:
                engine.embeddings = np.vstack([engine.embeddings, new_embs])

        _append_stash(quadruplets)
        logger.info("In-memory: added %d quadruplets (stash updated)", len(new_tuples))
        return len(new_tuples)

    def _ingest_to_production(self, quadruplets: list[dict], tkbc_dir: Optional[str]):
        """Ingest via TemporalKGIngester into Neo4j + ChromaDB."""
        from src.pipelines.ingestion.temporal_kg_ingester import TemporalKGIngester
        from src.pipelines.ingestion.entity_resolver import EntityResolver
        from src.utils.wikidata_utils import WikidataMapper

        records = [{"s": q["s"], "r": q["r"], "o": q["o"], "t": q["t"]} for q in quadruplets]
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json",
                                         delete=False, encoding="utf-8")
        try:
            json.dump(records, tmp)
            tmp.close()

            connector = self._kg_model.graph_struct.db_conn
            mapper = WikidataMapper(connector)
            resolver = EntityResolver(mapper)
            ingester = TemporalKGIngester(
                kg_model=self._kg_model,
                tkbc_dir=tkbc_dir,
                entity_resolver=resolver,
            )
            result = ingester.ingest_json(tmp.name, update_tkbc=(tkbc_dir is not None))
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass

        return result
