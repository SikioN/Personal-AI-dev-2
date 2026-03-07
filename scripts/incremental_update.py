#!/usr/bin/env python3
"""
incremental_update.py — Add new facts to the KG with atomicity and optional TComplEx retrain.

Usage:
    python scripts/incremental_update.py --input facts.json \\
        [--tkbc-dir wikidata_big/kg/tkbc_processed_data/wikidata_big/] \\
        [--force-retrain] [--retrain-epochs 50] [--dry-run]

facts.json format (generic, no Wikidata IDs required):
[
  {"subject": {"name": "Albert Einstein", "id": null},
   "relation": "born_in",
   "object":  {"name": "Ulm", "id": null},
   "time_start": "1879", "time_end": null}
]
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import pickle
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _backup_pickles(tkbc_dir: str) -> List[str]:
    backed_up = []
    for fname in ("ent_id", "rel_id", "ts_id", "train.pickle"):
        src = os.path.join(tkbc_dir, fname)
        if os.path.exists(src):
            dst = src + ".bak"
            shutil.copy2(src, dst)
            backed_up.append(src)
            logger.info("Backed up %s → %s.bak", src, src)
    return backed_up


def _restore_pickles(backed_up: List[str]) -> None:
    for src in backed_up:
        bak = src + ".bak"
        if os.path.exists(bak):
            shutil.move(bak, src)
            logger.info("Restored %s from backup.", src)


def _delete_backups(backed_up: List[str]) -> None:
    for src in backed_up:
        bak = src + ".bak"
        if os.path.exists(bak):
            os.remove(bak)


def _convert_facts_json(facts: list) -> list:
    """Convert the generic facts.json format to the TemporalKGIngester out.json format."""
    records = []
    for f in facts:
        subj = f.get("subject", {})
        obj = f.get("object", {})
        rel_name = f.get("relation", "unknown")
        time_start = f.get("time_start")
        time_end = f.get("time_end") or time_start

        if time_start is None:
            continue  # skip atemporal facts for tkbc update

        records.append({
            "s": {"name": subj.get("name", "Unknown"), "id": subj.get("id") or ""},
            "r": {"name": rel_name, "id": "", "type": "simple"},
            "o": {"name": obj.get("name", "Unknown"), "id": obj.get("id") or ""},
            "t": {"prop": {"start": str(time_start), "end": str(time_end)}},
        })
    return records


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Incremental KG update")
    parser.add_argument("--input", required=True, help="Path to facts.json")
    parser.add_argument("--tkbc-dir", default=None,
                        help="Directory with TComplEx pickle files")
    parser.add_argument("--force-retrain", action="store_true",
                        help="Retrain TComplEx after ingestion")
    parser.add_argument("--retrain-epochs", type=int, default=50)
    parser.add_argument("--dry-run", action="store_true",
                        help="Parse and validate facts without writing to the KG")
    args = parser.parse_args()

    # ------------------------------------------------------------------
    # Load facts
    # ------------------------------------------------------------------
    if not os.path.exists(args.input):
        logger.error("Facts file not found: %s", args.input)
        sys.exit(1)

    with open(args.input, encoding="utf-8") as f:
        raw_facts = json.load(f)

    logger.info("Loaded %d facts from %s", len(raw_facts), args.input)

    if args.dry_run:
        logger.info("[DRY RUN] Validation complete. No changes written.")
        return

    # ------------------------------------------------------------------
    # Bootstrap KG model
    # ------------------------------------------------------------------
    from src.config.qa_config import QAConfig
    from src.kg_model.knowledge_graph_model import KnowledgeGraphModel, KnowledgeGraphModelConfig
    from src.kg_model.graph_model import GraphModelConfig
    from src.db_drivers.graph_driver import GraphDriverConfig
    from src.db_drivers.vector_driver import VectorDriverConfig, VectorDBConnectionConfig
    from src.kg_model.embeddings_model import EmbeddingsModelConfig
    from src.db_drivers.vector_driver.embedders import EmbedderModelConfig

    config = QAConfig.from_env()

    graph_driver_cfg = GraphDriverConfig(
        db_vendor='neo4j',
        db_config={
            'host': config.neo4j_host,
            'port': config.neo4j_port,
            'user': config.neo4j_user,
            'pwd': config.neo4j_password,
            'db': config.neo4j_db,
        }
    )
    nodes_cfg = VectorDriverConfig(
        db_vendor='chroma',
        db_config=VectorDBConnectionConfig(
            conn={'host': config.chroma_host, 'port': config.chroma_port},
            db_info={'db': 'default_db', 'table': 'personalaitable'}))
    quads_cfg = VectorDriverConfig(
        db_vendor='chroma',
        db_config=VectorDBConnectionConfig(
            conn={'host': config.chroma_host, 'port': config.chroma_port},
            db_info={'db': 'default_db', 'table': 'personalaitable_quads'}))

    embedder_cfg = EmbedderModelConfig(model_name_or_path='intfloat/multilingual-e5-small')
    kg_model = KnowledgeGraphModel(KnowledgeGraphModelConfig(
        graph_config=GraphModelConfig(driver_config=graph_driver_cfg),
        embeddings_config=EmbeddingsModelConfig(
            nodesdb_driver_config=nodes_cfg,
            tripletsdb_driver_config=quads_cfg,
            embedder_config=embedder_cfg,
        ),
    ))

    # ------------------------------------------------------------------
    # Build EntityResolver
    # ------------------------------------------------------------------
    from src.utils.wikidata_utils import WikidataMapper
    from src.pipelines.ingestion.entity_resolver import EntityResolver

    connector = kg_model.graph_struct.db_conn
    mapper = WikidataMapper(connector)
    resolver = EntityResolver(mapper)

    # ------------------------------------------------------------------
    # Backup pickles
    # ------------------------------------------------------------------
    tkbc_dir = args.tkbc_dir
    backed_up: List[str] = []
    if tkbc_dir and os.path.isdir(tkbc_dir):
        backed_up = _backup_pickles(tkbc_dir)

    # ------------------------------------------------------------------
    # Ingest
    # ------------------------------------------------------------------
    from src.pipelines.ingestion.temporal_kg_ingester import TemporalKGIngester

    records = _convert_facts_json(raw_facts)
    tmp_path = args.input + ".converted_tmp.json"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False)

    ingester = TemporalKGIngester(
        kg_model=kg_model,
        tkbc_dir=tkbc_dir,
        entity_resolver=resolver,
    )

    try:
        result = ingester.ingest_json(tmp_path, update_tkbc=(tkbc_dir is not None))
        os.remove(tmp_path)
    except Exception as exc:
        logger.error("Ingestion failed: %s", exc)
        if backed_up:
            _restore_pickles(backed_up)
            logger.info("Pickles restored from backup.")
        os.remove(tmp_path)
        sys.exit(1)

    # ------------------------------------------------------------------
    # Success
    # ------------------------------------------------------------------
    _delete_backups(backed_up)
    logger.info(
        "Ingestion complete: added=%d skipped=%d errors=%d tkbc_updated=%s",
        result.added, result.skipped, result.errors, result.tkbc_updated,
    )

    if args.force_retrain and tkbc_dir:
        logger.info("Launching TComplEx retrain...")
        retrain_script = str(Path(__file__).parent / "retrain_tcomplex.py")
        subprocess.run([
            sys.executable, retrain_script,
            "--tkbc-dir", tkbc_dir,
            "--epochs", str(args.retrain_epochs),
        ], check=True)


if __name__ == "__main__":
    main()
