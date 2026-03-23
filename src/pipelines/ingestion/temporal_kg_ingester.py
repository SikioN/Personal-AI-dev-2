"""
Temporal KG Ingestion Pipeline.

Generic ingester for adding temporal quadruplets to any KnowledgeGraphModel.
Supports three input formats:
  - out.json  (JSON array, project standard from scripts/merge_out_json.py)
  - full.txt  (TSV: s_id\\tr_id\\to_id\\t[start_year]\\t[end_year])
  - List[Quadruplet]  (direct programmatic use)

Optionally updates tkbc pickle files (ent_id / rel_id / ts_id / train.pickle)
required by the TComplEx temporal scorer.

Usage:
    ingester = TemporalKGIngester(
        kg_model,
        tkbc_dir="wikidata_big/kg/tkbc_processed_data/wikidata_big/"
    )
    result = ingester.ingest_json("out.json")
    print(result)  # IngestionResult(added=42, skipped=0, errors=0, tkbc_updated=True)
"""
from __future__ import annotations

import json
import logging
import os
import pickle
from dataclasses import dataclass, field
from datetime import datetime as _dt
from typing import Dict, List, Optional, Tuple

import numpy as np

from src.kg_model.knowledge_graph_model import KnowledgeGraphModel
from src.utils.data_structs import (
    NodeCreator,
    NodeType,
    Quadruplet,
    QuadrupletCreator,
    RelationCreator,
    RelationType,
)

try:
    from src.pipelines.ingestion.entity_resolver import EntityResolver
except ImportError:
    EntityResolver = None  # type: ignore

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class IngestionResult:
    """Summary of a single ingestion run."""
    added: int = 0            # quadruplets successfully added to KnowledgeGraphModel
    skipped: int = 0          # records skipped (parse errors, bad years, etc.)
    errors: int = 0           # unexpected exceptions during KG update
    tkbc_updated: bool = False  # whether tkbc pickle files were updated


# ---------------------------------------------------------------------------
# Main ingester
# ---------------------------------------------------------------------------

class TemporalKGIngester:
    """
    Ingests temporal quadruplets from various sources into a KnowledgeGraphModel.

    Parameters
    ----------
    kg_model : KnowledgeGraphModel
        Target knowledge graph (any backend — InMemory, Neo4j, etc.).
    tkbc_dir : str, optional
        Path to the directory containing tkbc pickle files
        (ent_id, rel_id, ts_id, train.pickle).  If None, the tkbc update step
        is skipped even when ``update_tkbc=True`` is passed.
    batch_size : int
        Number of quadruplets per ``add_knowledge()`` call (affects memory).
    """

    def __init__(
        self,
        kg_model: KnowledgeGraphModel,
        tkbc_dir: Optional[str] = None,
        batch_size: int = 500,
        entity_resolver=None,
    ) -> None:
        self.kg_model = kg_model
        self.tkbc_dir = tkbc_dir
        self.batch_size = batch_size
        self.entity_resolver = entity_resolver  # Optional[EntityResolver]

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def ingest_json(self, json_path: str, update_tkbc: bool = True) -> IngestionResult:
        """
        Ingest from the project-standard ``out.json`` format.

        Expected JSON structure (array of records):

        .. code-block:: json

            [
              {
                "s": {"id": "Q937",  "name": "Albert Einstein"},
                "r": {"id": "P27",   "name": "country of citizenship", "type": "simple"},
                "o": {"id": "Q30",   "name": "United States"},
                "t": {"prop": {"start": "1940", "end": "1955"}}
              }
            ]

        ``id`` fields are stored as ``wd_id`` node/relation props and are used
        for tkbc pickle updates and entity resolution in QA.
        """
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"[TemporalKGIngester] JSON file not found: {json_path}")

        with open(json_path, "r", encoding="utf-8") as f:
            records = json.load(f)

        if not isinstance(records, list):
            raise ValueError(
                f"[TemporalKGIngester] Expected a JSON array in {json_path}, got {type(records)}"
            )

        quadruplets, parse_errors = self._json_to_quadruplets(records)
        return self._ingest(quadruplets, parse_errors, update_tkbc)

    def ingest_tsv(
        self,
        tsv_path: str,
        id2entity: Dict[str, str],
        id2relation: Dict[str, str],
        update_tkbc: bool = True,
    ) -> IngestionResult:
        """
        Ingest from the ``full.txt`` TSV format used by the Wikidata pipeline.

        Each line: ``s_id\\tr_id\\to_id\\t[start_year]\\t[end_year]``

        Parameters
        ----------
        id2entity : dict
            Maps entity Wikidata/custom IDs to human-readable names.
        id2relation : dict
            Maps relation IDs to human-readable names.

        Both dicts can be loaded from ``wd_id2entity_text.txt`` /
        ``wd_id2relation_text.txt`` or built programmatically for custom KGs.
        """
        if not os.path.exists(tsv_path):
            raise FileNotFoundError(f"[TemporalKGIngester] TSV file not found: {tsv_path}")

        quadruplets, parse_errors = self._tsv_to_quadruplets(tsv_path, id2entity, id2relation)
        return self._ingest(quadruplets, parse_errors, update_tkbc)

    def ingest_quadruplets(
        self,
        quadruplets: List[Quadruplet],
        update_tkbc: bool = True,
    ) -> IngestionResult:
        """
        Ingest pre-built ``Quadruplet`` objects directly.

        Use this when you already have Quadruplet instances (e.g. from a
        custom parser or another pipeline stage).
        """
        return self._ingest(quadruplets, parse_errors=0, update_tkbc=update_tkbc)

    # ------------------------------------------------------------------ #
    #  Private: parsing                                                    #
    # ------------------------------------------------------------------ #

    def _json_to_quadruplets(
        self, records: List[dict]
    ) -> Tuple[List[Quadruplet], int]:
        """
        Convert ``out.json`` records to Quadruplet objects.

        Returns (quadruplets, error_count).
        """
        quadruplets: List[Quadruplet] = []
        errors = 0

        for i, rec in enumerate(records):
            try:
                s_data = rec["s"]
                r_data = rec["r"]
                o_data = rec["o"]
                t_data = rec.get("t", {})

                # Parse temporal range
                t_props = t_data.get("prop", {})
                start_raw = str(t_props.get("start", "") or "").strip()
                end_raw   = str(t_props.get("end", start_raw) or start_raw).strip()

                if not start_raw or start_raw.lower() in ("unknown", "none"):
                    # Atemporal fact — store with 'Always' sentinel
                    start_year, end_year = None, None
                    t_name = "Always"
                else:
                    try:
                        start_year = int(start_raw)
                        end_year   = int(end_raw) if end_raw and end_raw.lower() not in ("unknown", "none") else start_year
                        t_name = f"{start_year} - {end_year}" if start_year != end_year else str(start_year)
                    except (ValueError, TypeError):
                        logger.debug(
                            "[TemporalKGIngester] Record %d: non-integer year '%s', defaulting to 'Always'",
                            i, start_raw
                        )
                        start_year, end_year = None, None
                        t_name = "Always"

                s_name = s_data.get("name", s_data.get("id", "Unknown"))
                o_name = o_data.get("name", o_data.get("id", "Unknown"))
                s_id_hint = s_data.get("id") or None
                o_id_hint = o_data.get("id") or None

                if self.entity_resolver is not None:
                    s_res = self.entity_resolver.resolve(s_name, node_type="object", wd_id_hint=s_id_hint)
                    o_res = self.entity_resolver.resolve(o_name, node_type="object", wd_id_hint=o_id_hint)
                    s_node = NodeCreator.create(
                        NodeType.object, name=s_res.canonical_name,
                        prop={"wd_id": s_res.canonical_id})
                    if s_res.input_name != s_res.canonical_name:
                        s_node.alias_to_add = s_res.input_name
                    o_node = NodeCreator.create(
                        NodeType.object, name=o_res.canonical_name,
                        prop={"wd_id": o_res.canonical_id})
                    if o_res.input_name != o_res.canonical_name:
                        o_node.alias_to_add = o_res.input_name
                else:
                    s_node = NodeCreator.create(
                        NodeType.object, name=s_name,
                        prop={"wd_id": s_id_hint or ""},
                    )
                    o_node = NodeCreator.create(
                        NodeType.object, name=o_name,
                        prop={"wd_id": o_id_hint or ""},
                    )
                r_node = RelationCreator.create(
                    RelationType.simple,
                    name=r_data.get("name", r_data.get("id", "Unknown")),
                    prop={"wd_id": r_data.get("id", "")},
                )
                t_node = NodeCreator.create(
                    NodeType.time,
                    name=t_name,
                    add_stringified_node=True,
                )

                quadruplets.append(QuadrupletCreator.create(s_node, r_node, o_node, t_node))

            except Exception as exc:
                logger.warning(
                    "[TemporalKGIngester] Skipping record %d due to unexpected error: %s", i, exc
                )
                errors += 1

        logger.info(
            "[TemporalKGIngester] Parsed %d quadruplets from JSON (%d errors).",
            len(quadruplets), errors,
        )
        return quadruplets, errors

    def _tsv_to_quadruplets(
        self,
        tsv_path: str,
        id2entity: Dict[str, str],
        id2relation: Dict[str, str],
    ) -> Tuple[List[Quadruplet], int]:
        """
        Parse ``full.txt``-style TSV lines into Quadruplet objects.

        Line format: ``s_id\\tr_id\\to_id\\t[start_year]\\t[end_year]``
        (matches the format consumed by ``hydrate_in_memory_graph`` in
        ``src/utils/graph_loader.py``).
        """
        quadruplets: List[Quadruplet] = []
        errors = 0

        with open(tsv_path, "r", encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                parts = line.strip().split("\t")
                if len(parts) < 3:
                    continue
                try:
                    s_id, r_id, o_id = parts[0], parts[1], parts[2]
                    s_name = id2entity.get(s_id, s_id)
                    o_name = id2entity.get(o_id, o_id)
                    r_name = id2relation.get(r_id, r_id)

                    if len(parts) >= 5:
                        start_year = int(parts[3])
                        end_year   = int(parts[4])
                        t_name = f"{start_year} - {end_year}" if start_year != end_year else str(start_year)
                    elif len(parts) == 4:
                        start_year = int(parts[3])
                        end_year   = start_year
                        t_name = str(start_year)
                    else:
                        t_name = "Always"
                        start_year, end_year = None, None

                    s_node = NodeCreator.create(NodeType.object, name=s_name, prop={"wd_id": s_id})
                    o_node = NodeCreator.create(NodeType.object, name=o_name, prop={"wd_id": o_id})
                    r_node = RelationCreator.create(
                        RelationType.simple, name=r_name, prop={"wd_id": r_id}
                    )
                    t_node = NodeCreator.create(
                        NodeType.time, name=t_name, add_stringified_node=True
                    )

                    quadruplets.append(QuadrupletCreator.create(s_node, r_node, o_node, t_node))

                except (ValueError, IndexError) as exc:
                    logger.warning(
                        "[TemporalKGIngester] Skipping TSV line %d: %s", lineno, exc
                    )
                    errors += 1

        logger.info(
            "[TemporalKGIngester] Parsed %d quadruplets from TSV (%d errors).",
            len(quadruplets), errors,
        )
        return quadruplets, errors

    # ------------------------------------------------------------------ #
    #  Private: ingestion                                                  #
    # ------------------------------------------------------------------ #

    def _ingest(
        self,
        quadruplets: List[Quadruplet],
        parse_errors: int,
        update_tkbc: bool,
    ) -> IngestionResult:
        """Shared ingestion sink: add to KG + optional tkbc update."""
        result = IngestionResult(errors=parse_errors)

        if not quadruplets:
            logger.info("[TemporalKGIngester] No quadruplets to ingest.")
            return result

        # Add to KnowledgeGraphModel in batches
        kg_errors = 0
        for batch_start in range(0, len(quadruplets), self.batch_size):
            batch = quadruplets[batch_start : batch_start + self.batch_size]
            try:
                is_last = (batch_start + self.batch_size) >= len(quadruplets)
                self.kg_model.add_knowledge(
                    batch,
                    check_consistency=is_last,
                    status_bar=False,
                )
                result.added += len(batch)
                logger.info(
                    "[TemporalKGIngester] Added batch %d-%d to KG.",
                    batch_start, batch_start + len(batch) - 1,
                )
            except Exception as exc:
                logger.error(
                    "[TemporalKGIngester] Error adding batch %d-%d: %s",
                    batch_start, batch_start + len(batch) - 1, exc,
                    exc_info=True
                )
                kg_errors += len(batch)
                result.errors += len(batch)

        # Optionally update tkbc pickle files
        if update_tkbc:
            if self.tkbc_dir is None:
                logger.warning(
                    "[TemporalKGIngester] update_tkbc=True but tkbc_dir was not set — skipping."
                )
            else:
                result.tkbc_updated = self._update_tkbc_pickles(quadruplets)

        logger.info("[TemporalKGIngester] Done. %s", result)
        return result

    # ------------------------------------------------------------------ #
    #  Private: tkbc pickle update                                         #
    # ------------------------------------------------------------------ #

    def _update_tkbc_pickles(self, quadruplets: List[Quadruplet]) -> bool:
        """
        Update tkbc pickle files with the new quadruplets.

        Mirrors the logic from ``scripts/merge_out_json.py`` exactly:
        adds new entity / relation / timestamp IDs and appends new rows to
        ``train.pickle``.

        Returns True if successful, False if an error occurred (non-fatal —
        the KG has already been updated at this point).
        """
        tkbc_dir = self.tkbc_dir
        ent_id_path   = os.path.join(tkbc_dir, "ent_id")
        rel_id_path   = os.path.join(tkbc_dir, "rel_id")
        ts_id_path    = os.path.join(tkbc_dir, "ts_id")
        train_path    = os.path.join(tkbc_dir, "train.pickle")

        # Load all pickles atomically (abort if any is missing)
        try:
            with open(ent_id_path,  "rb") as f: ent_id  = pickle.load(f)
            with open(rel_id_path,  "rb") as f: rel_id  = pickle.load(f)
            with open(ts_id_path,   "rb") as f: ts_id   = pickle.load(f)
            with open(train_path,   "rb") as f: train   = pickle.load(f)
        except (FileNotFoundError, pickle.UnpicklingError) as exc:
            logger.error(
                "[TemporalKGIngester] Could not load tkbc pickles from %s: %s", tkbc_dir, exc
            )
            return False

        new_rows: List[List[int]] = []

        for quad in quadruplets:
            s_id_str = quad.start_node.prop.get("wd_id", quad.start_node.name)
            r_id_str = quad.relation.prop.get("wd_id",  quad.relation.name)
            o_id_str = quad.end_node.prop.get("wd_id",  quad.end_node.name)

            # Parse temporal range from the time node name
            if quad.time and quad.time.name not in ("Always", "Unknown"):
                import re as _re
                years = sorted(int(y) for y in _re.findall(r"(\d{4})", quad.time.name))
                if len(years) >= 2:
                    start_year, end_year = years[0], years[-1]
                elif len(years) == 1:
                    start_year = end_year = years[0]
                else:
                    logger.debug(
                        "[TemporalKGIngester] Atemporal fact '%s' (no years), skipping TComplEx update.",
                        quad.time.name,
                    )
                    continue
            else:
                logger.debug(
                    "[TemporalKGIngester] Atemporal fact (Always/Unknown), skipping TComplEx update."
                )
                continue

            # Register new entities / relation
            if s_id_str not in ent_id: ent_id[s_id_str] = len(ent_id)
            if o_id_str not in ent_id: ent_id[o_id_str] = len(ent_id)
            if r_id_str not in rel_id: rel_id[r_id_str] = len(rel_id)

            # Register new timestamps
            ts_start = (start_year, 0, 0)
            ts_end   = (end_year,   0, 0)
            if ts_start not in ts_id: ts_id[ts_start] = len(ts_id)
            if ts_end   not in ts_id: ts_id[ts_end]   = len(ts_id)

            new_rows.append([
                ent_id[s_id_str],
                rel_id[r_id_str],
                ent_id[o_id_str],
                ts_id[ts_start],
                ts_id[ts_end],
            ])

        if not new_rows:
            logger.info("[TemporalKGIngester] No temporal rows to add to tkbc pickles.")
            return True

        try:
            new_arr  = np.array(new_rows, dtype=train.dtype)
            extended = np.vstack([train, new_arr])

            # 4.2: atomic pickle writes via temp-file + rename to prevent partial updates
            import tempfile, shutil

            def _atomic_pickle(path, data):
                dir_ = os.path.dirname(path) or "."
                with tempfile.NamedTemporaryFile(dir=dir_, delete=False, suffix='.tmp') as tmp:
                    pickle.dump(data, tmp)
                    tmp_path = tmp.name
                shutil.move(tmp_path, path)

            _atomic_pickle(ent_id_path,  ent_id)
            _atomic_pickle(rel_id_path,  rel_id)
            _atomic_pickle(ts_id_path,   ts_id)
            _atomic_pickle(train_path,   extended)

            logger.info(
                "[TemporalKGIngester] tkbc pickles updated: +%d rows (total=%d). "
                "ent=%d rel=%d ts=%d",
                len(new_rows), len(extended),
                len(ent_id), len(rel_id), len(ts_id),
            )
            return True

        except Exception as exc:
            logger.error("[TemporalKGIngester] Failed to save tkbc pickles: %s", exc)
            return False
