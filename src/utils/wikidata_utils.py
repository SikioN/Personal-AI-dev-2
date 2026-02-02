import os
import pickle
from typing import Dict, Optional

class WikidataMapper:
    """Helper for mapping between Wikidata IDs and human labels."""
    def __init__(self, kg_path: str):
        self.id2name = {}
        self.name2id = {}
        
        ent_file = os.path.join(kg_path, "wd_id2entity_text.txt")
        rel_file = os.path.join(kg_path, "wd_id2relation_text.txt")
        
        if os.path.exists(ent_file):
            with open(ent_file, 'r', encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split('\t')
                    if len(parts) >= 2:
                        wd_id, name = parts[0], parts[1]
                        self.id2name[wd_id] = name
                        self.name2id[name.lower()] = wd_id
                        
        if os.path.exists(rel_file):
            with open(rel_file, 'r', encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split('\t')
                    if len(parts) >= 2:
                        wd_id, name = parts[0], parts[1]
                        self.id2name[wd_id] = name
                        self.name2id[name.lower()] = wd_id

    def get_id(self, name: str) -> Optional[str]:
        return self.name2id.get(name.lower())

    def get_label(self, wd_id: str) -> str:
        return self.id2name.get(wd_id, wd_id)
