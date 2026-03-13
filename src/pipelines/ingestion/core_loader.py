import json
import logging
from typing import List, Dict, Union, Optional
from tqdm import tqdm
from pathlib import Path

from ...kg_model import KnowledgeGraphModel
from ...utils.data_structs import Quadruplet, Node, Relation, NodeCreator, RelationCreator, QuadrupletCreator, NodeType, RelationType
from ...utils import Logger

class CoreLoader:
    def __init__(self, kg_model: KnowledgeGraphModel, logger: Logger = None):
        self.kg_model = kg_model
        self.logger = logger

    def _parse_node(self, data: Union[str, Dict], default_type: NodeType = NodeType.object) -> Node:
        if isinstance(data, str):
            # If strictly string, assume it's the name. ID will be generated or inferred inside Creator? 
            # NodeCreator generates ID if not provided? No, usually it creates a hash.
            # Let's verify NodeCreator usage.
            return NodeCreator.create(name=data, n_type=default_type)
        elif isinstance(data, dict):
            # Handle string-based type to Enum conversion
            type_str = data.get('type', default_type.value)
            # Find matching enum
            try:
                n_type = NodeType(type_str)
            except ValueError:
                # Fallback or strict? Let's try to map keys if possible, or default
                # But for now assume valid enum values in JSON
                n_type = default_type
                
            node = NodeCreator.create(
                name=data.get('name', 'Unknown'),
                n_type=n_type,
                prop=data.get('prop', {})
            )
            # If ID is provided in JSON, override it?
            # NodeCreator.create doesn't accept 'id' argument typically (it generates it).
            # But we can set it manually if needed for maintaining external IDs.
            if 'id' in data:
                node.id = data['id'] 
            return node
        else:
            raise ValueError(f"Invalid node data: {data}")

    def _parse_relation(self, data: Union[str, Dict], default_type: RelationType = RelationType.simple) -> Relation:
        if isinstance(data, str):
            return RelationCreator.create(name=data, r_type=default_type)
        elif isinstance(data, dict):
            type_str = data.get('type', default_type.value)
            try:
                r_type = RelationType(type_str)
            except ValueError:
                r_type = default_type

            rel = RelationCreator.create(
                name=data.get('name', 'Unknown'),
                r_type=r_type,
                prop=data.get('prop', {})
            )
            if 'id' in data:
                rel.id = data['id']
            return rel
        else:
             raise ValueError(f"Invalid relation data: {data}")

    def load_from_jsonl(self, file_path: str, batch_size: int = 500, skip_lines: int = 0) -> None:
        """
        Loads quadruplets from a JSONL file.
        Each line should be a JSON object with keys: 's', 'r', 'o', and optionally 't'.
        Values can be strings (names) or dicts ({name, type, prop, id}).
        """
        buffer = []
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Count lines for tqdm
        with open(path, 'r') as f:
            total_lines = sum(1 for _ in f)

        with open(path, 'r') as f:
            # Fast-forward if needed
            if skip_lines > 0:
                print(f"Skipping first {skip_lines} lines...")
                for _ in range(skip_lines):
                    next(f, None)

            for line in tqdm(f, total=total_lines - skip_lines, desc="Loading Quadruplets"):
                line = line.strip()
                if not line:
                    continue
                    
                try:
                    item = json.loads(line)
                    
                    s = self._parse_node(item.get('s'), NodeType.object)
                    o = self._parse_node(item.get('o'), NodeType.object)
                    r = self._parse_relation(item.get('r'), RelationType.simple)
                    
                    t_data = item.get('t')
                    if t_data:
                        t = self._parse_node(t_data, NodeType.time)
                    else:
                        t = NodeCreator.create(name="Always", n_type=NodeType.time)
                    
                    quadruplet = QuadrupletCreator.create(s, r, o, t)
                    buffer.append(quadruplet)
                    
                    if len(buffer) >= batch_size:
                        self.kg_model.add_knowledge(buffer, check_consistency=False, status_bar=False)
                        buffer = []
                        
                except Exception as e:
                    if self.logger:
                        self.logger(f"Error parsing line: {line[:100]}... Error: {e}")
                    else:
                        print(f"Error parsing line: {e}")
                    
            if buffer:
                self.kg_model.add_knowledge(buffer, check_consistency=True, status_bar=False)
