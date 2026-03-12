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

        all_quadruplets: list[dict] = []
        errors_total = 0
        files_processed = 0

        llm_backend = os.environ.get("LLM_BACKEND", "deepseek").lower()
        llm_model = self._get_llm_model(llm_backend)
        llm_api_key = self._get_llm_api_key(llm_backend)
        llm_base_url = self._get_llm_base_url(llm_backend)

        for idx, (filepath, text) in enumerate(new_docs):
            fname = Path(filepath).name
            if progress_callback:
                progress_callback(f"Обработка файла {idx + 1}/{len(new_docs)}: {fname}")
            logger.info("Processing %s (%d chars)", filepath, len(text))

            try:
                if llm_backend == "ollama":
                    raw_quads = extract_with_ollama(text, model=llm_model)
                elif llm_backend in ("openai", "deepseek", "chatgpt", "qwen", "compatible"):
                    raw_quads = extract_with_openai(
                        text,
                        api_key=llm_api_key,
                        model=llm_model,
                        base_url=llm_base_url,
                        workers=4,
                    )
                else:
                    raw_quads = extract_with_ollama(text, model=llm_model)

                built = []
                for raw in raw_quads:
                    try:
                        q = build_quadruplet(raw, prop_map, llm_caller)
                        if q:
                            built.append(q)
                    except Exception as e:
                        logger.debug("build_quadruplet error: %s", e)
                        errors_total += 1

                deduped = deduplicate(built)
                all_quadruplets.extend(deduped)
                _mark_processed(filepath, len(deduped))
                files_processed += 1

            except Exception as e:
                logger.error("Failed to process %s: %s", filepath, e)
                errors_total += 1

        if not all_quadruplets:
            return {"added": 0, "skipped": 0, "errors": errors_total,
                    "files_processed": files_processed, "files_skipped": files_skipped}

        if progress_callback:
            progress_callback(f"Сохранение {len(all_quadruplets)} фактов в граф...")

        if self._inmemory_engine is not None:
            added = self._ingest_to_inmemory(all_quadruplets)
            skipped = 0
        else:
            result = self._ingest_to_production(all_quadruplets, tkbc_dir)
            added = result.added
            skipped = result.skipped
            errors_total += result.errors

        _update_ingest_stats(added)
        return {
            "added": added,
            "skipped": skipped,
            "errors": errors_total,
            "files_processed": files_processed,
            "files_skipped": files_skipped,
        }

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
