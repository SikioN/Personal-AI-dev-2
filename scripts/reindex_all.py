#!/usr/bin/env python3
"""
reindex_all.py — Full re-indexing pipeline:
1. Clear KuzuDB and ChromaDB.
2. Ingest documents from a directory (extract facts, add to DBs).
3. Retrain TComplEx temporal scorer on the new facts.

Usage:
    python scripts/reindex_all.py --input-dir new_docs --tkbc-dir wikidata_big/kg/tkbc_processed_data/wikidata_big/
"""
import os
import sys
import logging
import argparse
import subprocess
from pathlib import Path

# Add project root to path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)

from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

def run_command(cmd_list: list[str], description: str):
    logger.info(f"--- Running: {description} ---")
    logger.info(f"Command: {' '.join(cmd_list)}")
    try:
        subprocess.run(cmd_list, check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Error during {description}: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Full re-indexing pipeline")
    parser.add_argument("--input-dir", default="new_docs", help="Directory with source documents (PDF/TXT)")
    parser.add_argument("--tkbc-dir", required=True, help="Path to tkbc data directory (e.g. wikidata_big/kg/tkbc_processed_data/wikidata_big/)")
    parser.add_argument("--epochs", type=int, default=50, help="TComplEx training epochs")
    parser.add_argument("--force", action="store_true", help="Force re-processing of already processed files")
    args = parser.parse_args()

    load_dotenv()

    # 1. Clear databases
    logger.info("Step 1: Clearing KuzuDB and ChromaDB...")
    run_command([sys.executable, "scripts/clear_kg.py"], "Clearing KG")

    # 2. Ingest documents
    # Note: We use the existing logic from doc_ingestion_service.py 
    # but we can also use a script if available. 
    # Since DocIngestionService is mainly for the bot, 
    # we'll use a direct python call to instantiate it.
    
    logger.info(f"Step 2: Ingesting documents from '{args.input_dir}'...")
    from src.pipelines.ingestion.doc_ingestion_service import DocIngestionService
    from src.bot.engine_loader import load_engine
    
    # Force production mode for reindexing
    os.environ["USE_INMEMORY"] = "false"
    
    _, _, kg_model = load_engine() # This gets the production KG model
    if kg_model is None:
        logger.error("Could not initialize production KnowledgeGraphModel. Check .env and KuzuDB/ChromaDB paths.")
        sys.exit(1)
        
    service = DocIngestionService(kg_model)
    
    # Ensure input_dir is absolute
    input_path = os.path.abspath(args.input_dir)
    if not os.path.exists(input_path):
        logger.error(f"Input directory not found: {input_path}")
        sys.exit(1)
        
    stats = service.ingest_directory(input_path, tkbc_dir=args.tkbc_dir, reprocess=args.force)
    logger.info(f"Ingestion completed: {stats}")

    # 3. Retrain TComplEx
    logger.info("Step 3: Retraining TComplEx temporal scorer...")
    retrain_cmd = [
        sys.executable, "scripts/retrain_tcomplex.py",
        "--tkbc-dir", args.tkbc_dir,
        "--epochs", str(args.epochs)
    ]
    run_command(retrain_cmd, "Retraining TComplEx")

    logger.info("==========================================")
    logger.info("✅ FULL RE-INDEXING COMPLETED SUCCESSFULLY!")
    logger.info("==========================================")

if __name__ == "__main__":
    main()
