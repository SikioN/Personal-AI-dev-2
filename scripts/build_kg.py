#!/usr/bin/env python3
"""
build_kg.py — First-time build of KuzuDB + ChromaDB from full.txt.

Usage:
    python scripts/build_kg.py
    python scripts/build_kg.py --force    # rebuild even if already populated
"""
import os
import sys
import logging
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Build KuzuDB + ChromaDB from full.txt")
    parser.add_argument("--force", action="store_true", help="Rebuild even if already populated")
    args = parser.parse_args()

    # Load .env if python-dotenv is available
    try:
        from dotenv import load_dotenv
        load_dotenv()
        logger.info("Loaded .env")
    except ImportError:
        pass

    from src.config.qa_config import QAConfig
    from src.bot.engine_loader import _load_quadruplets, _load_id2label, _resolve_kg_data_path, ROOT_DIR

    config = QAConfig.from_env()
    kg_data_path = _resolve_kg_data_path()

    full_txt = os.path.join(kg_data_path, "full.txt")
    ent_file = os.path.join(kg_data_path, "wd_id2entity_text.txt")
    rel_file = os.path.join(kg_data_path, "wd_id2relation_text.txt")

    if not os.path.exists(full_txt):
        logger.error(f"full.txt not found at: {full_txt}")
        logger.error("Set KG_DATA_PATH env var or place data in wikidata_big/kg/")
        sys.exit(1)

    # ── Build KnowledgeGraphModel with KuzuDB + ChromaDB ──────────────────────
    from src.db_drivers.vector_driver.embedders import EmbedderModelConfig
    from src.kg_model.embeddings_model import EmbeddingsModelConfig
    from src.db_drivers.vector_driver import VectorDriverConfig, VectorDBConnectionConfig
    from src.kg_model.graph_model import GraphModelConfig
    from src.db_drivers.graph_driver import GraphDriverConfig
    from src.db_drivers.graph_driver.connectors.KuzuConnector import DEFAULT_KUZU_CONFIG
    from src.db_drivers.graph_driver.utils import GraphDBConnectionConfig
    from src.kg_model.knowledge_graph_model import KnowledgeGraphModel, KnowledgeGraphModelConfig

    kuzu_path = os.path.abspath(config.kuzu_path)
    nodes_path = os.path.abspath(os.environ.get(
        "CHROMA_NODES_PATH",
        os.path.join(ROOT_DIR, "data/graph_structures/vectorized_nodes/default"),
    ))
    quads_path = os.path.abspath(os.environ.get(
        "CHROMA_QUADS_PATH",
        os.path.join(ROOT_DIR, "data/graph_structures/vectorized_quadruplets/default"),
    ))

    os.makedirs(kuzu_path, exist_ok=True)
    os.makedirs(nodes_path, exist_ok=True)
    os.makedirs(quads_path, exist_ok=True)

    logger.info(f"KuzuDB path:    {kuzu_path}")
    logger.info(f"ChromaDB nodes: {nodes_path}")
    logger.info(f"ChromaDB quads: {quads_path}")

    # KuzuDB — same schema as DEFAULT_KUZU_CONFIG, override path only
    kuzu_cfg = GraphDBConnectionConfig(
        params=dict(DEFAULT_KUZU_CONFIG.params, path=kuzu_path)
    )
    graph_driver_cfg = GraphDriverConfig(db_vendor="kuzu", db_config=kuzu_cfg)

    # ChromaDB
    nodes_cfg = VectorDriverConfig(
        db_vendor="chroma",
        db_config=VectorDBConnectionConfig(
            conn={"path": nodes_path},
            db_info={"db": "default_db", "table": "personalaitable"},
        ),
    )
    quads_cfg = VectorDriverConfig(
        db_vendor="chroma",
        db_config=VectorDBConnectionConfig(
            conn={"path": quads_path},
            db_info={"db": "default_db", "table": "personalaitable"},
        ),
    )

    model_path = (
        os.environ.get("FINETUNED_MODEL_PATH")
        or os.environ.get("MODEL_PATH")
        or os.path.join(ROOT_DIR, "models/wikidata_finetuned_remote/wikidata_finetuned")
    )
    embedder_cfg = EmbedderModelConfig(
        model_name_or_path=model_path if os.path.exists(model_path)
        else "intfloat/multilingual-e5-small"
    )
    emb_cfg = EmbeddingsModelConfig(
        nodesdb_driver_config=nodes_cfg,
        quadrupletsdb_driver_config=quads_cfg,
        embedder_config=embedder_cfg,
    )
    kg_model_cfg = KnowledgeGraphModelConfig(
        embeddings_config=emb_cfg,
        graph_config=GraphModelConfig(driver_config=graph_driver_cfg),
    )

    logger.info("Initializing KnowledgeGraphModel (KuzuDB + ChromaDB)...")
    kg_model = KnowledgeGraphModel(kg_model_cfg)

    # Check if already populated
    db_conn = kg_model.graph_struct.db_conn
    counts = db_conn.count_items()
    existing = counts.get("quadruplets", 0)
    if existing > 0 and not args.force:
        logger.info(f"KuzuDB already has {existing:,} quadruplets. Use --force to rebuild.")
        return

    # ── Load data ─────────────────────────────────────────────────────────────
    logger.info(f"Loading id2label from {ent_file} ...")
    id2label = _load_id2label(ent_file)
    id2label.update(_load_id2label(rel_file))
    logger.info(f"Loaded {len(id2label):,} labels")

    logger.info(f"Loading quadruplets from {full_txt} ...")
    raw_quads = _load_quadruplets(full_txt)
    logger.info(f"Loaded {len(raw_quads):,} quadruplets")

    if not raw_quads:
        logger.error("No quadruplets loaded. Check full.txt format.")
        sys.exit(1)

    # ── Batch insert into KuzuDB ──────────────────────────────────────────────
    from src.utils.data_structs import NodeCreator, RelationCreator, QuadrupletCreator

    BATCH = 1000
    total = len(raw_quads)
    logger.info(f"Inserting {total:,} quadruplets into KuzuDB (batch={BATCH})...")

    for start in range(0, total, BATCH):
        batch = raw_quads[start : start + BATCH]
        quad_objs = []
        seen_ids: set = set()

        for s, r, o, t in batch:
            s_node = NodeCreator.create("object", id2label.get(s, s))
            s_node.id = s
            o_node = NodeCreator.create("object", id2label.get(o, o))
            o_node.id = o
            r_rel = RelationCreator.create("simple", id2label.get(r, r))
            t_node = NodeCreator.create("time", t if t else "Always")
            q = QuadrupletCreator.create(s_node, r_rel, o_node, t_node)
            q.start_node.prop["wd_id"] = s
            q.relation.prop["wd_id"] = r
            q.end_node.prop["wd_id"] = o
            if q.id not in seen_ids:
                seen_ids.add(q.id)
                quad_objs.append(q)

        if quad_objs:
            db_conn.create(quad_objs)

        if (start // BATCH) % 20 == 0:
            done = min(start + BATCH, total)
            logger.info(f"  {done:,}/{total:,} ({100 * done // total}%)")

    final_counts = db_conn.count_items()
    logger.info(f"KuzuDB populated: {final_counts}")
    logger.info("Done. Run the bot with: bash run_db.sh")


if __name__ == "__main__":
    main()
