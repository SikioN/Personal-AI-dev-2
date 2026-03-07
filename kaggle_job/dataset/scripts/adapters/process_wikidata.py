import argparse
import json
import logging
from pathlib import Path
from tqdm import tqdm
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_mapping(path: Path) -> Dict[str, str]:
    """Loads a TSV mapping file (ID -> Label) into a dictionary."""
    mapping = {}
    if not path.exists():
        logger.warning(f"Mapping file not found: {path}. IDs will be used as labels.")
        return mapping
    
    logger.info(f"Loading mapping from {path}...")
    with open(path, 'r', encoding='utf-8') as f:
        for line in tqdm(f, desc=f"Loading {path.name}"):
            parts = line.strip().split('\t')
            if len(parts) >= 2:
                mapping[parts[0]] = parts[1]
    logger.info(f"Loaded {len(mapping)} entries from {path.name}")
    return mapping

def parse_tsv_line(line: str, entity_map: Dict[str, str], relation_map: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """
    Parses a single line from the Wikidata TSV dump.
    Format: S_ID \t R_ID \t O_ID \t Start \t End
    """
    parts = line.strip().split('\t')
    if len(parts) != 5:
        return None
        
    s_id, r_id, o_id, start_year, end_year = parts
    
    # Resolve labels
    s_label = entity_map.get(s_id, s_id)
    r_label = relation_map.get(r_id, r_id)
    o_label = entity_map.get(o_id, o_id) # Objects are also entities usually
    
    s = {"name": s_label, "id": s_id}
    r = {"name": r_label, "id": r_id, "type": "simple"}
    o = {"name": o_label, "id": o_id}
    
    # Time handling
    # If years are missing or placeholders, handle accordingly.
    # Assuming the file format uses specific values for missing, but let's take them as is for now.
    t_name = f"{start_year} - {end_year}"
    t = {
        "name": t_name,
        "type": "time",
        "prop": {
            "start": start_year,
            "end": end_year
        }
    }
    
    return {
        "s": s,
        "r": r,
        "o": o,
        "t": t
    }

def process_file(input_path: str, output_path: str, entities_path: str, relations_path: str, limit: int = None):
    input_file = Path(input_path)
    output_file = Path(output_path)
    
    if not input_file.exists():
        logger.error(f"Input file not found: {input_path}")
        return

    # Load mappings
    entity_map = load_mapping(Path(entities_path))
    relation_map = load_mapping(Path(relations_path))

    logger.info(f"Processing {input_path} -> {output_path}")
    
    count = 0
    with open(input_file, 'r', encoding='utf-8') as fin, \
         open(output_file, 'w', encoding='utf-8') as fout:
        
        for line in tqdm(fin, desc="Processing Quadruplets"):
            quadruplet = parse_tsv_line(line, entity_map, relation_map)
            if quadruplet:
                fout.write(json.dumps(quadruplet, ensure_ascii=False) + '\n')
                count += 1
                
            if limit and count >= limit:
                break
                
    logger.info(f"Finished. Extracted {count} quadruplets.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Wikidata Dump Processor to Standardized Quadruplets")
    parser.add_argument("--input", type=str, required=True, help="Path to input Wikidata dump file (TSV)")
    parser.add_argument("--output", type=str, required=True, help="Path to output .jsonl file")
    parser.add_argument("--entities", type=str, required=True, help="Path to entity mapping file")
    parser.add_argument("--relations", type=str, required=True, help="Path to relation mapping file")
    parser.add_argument("--limit", type=int, default=None, help="Max records to process")
    
    args = parser.parse_args()
    
    process_file(args.input, args.output, args.entities, args.relations, args.limit)
