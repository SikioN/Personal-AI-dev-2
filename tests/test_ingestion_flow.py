import unittest
import json
import os
import shutil
from pathlib import Path
from unittest.mock import MagicMock, ANY

from src.pipelines.ingestion.core_loader import CoreLoader
from scripts.adapters.process_wikidata import process_file
from src.utils.data_structs import Quadruplet

class TestIngestionPipeline(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("tests/temp_ingestion")
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self.input_file = self.test_dir / "raw_input.json"
        self.intermediate_file = self.test_dir / "standardized.jsonl"
        
        # Create dummy input data (mimicking a JSON list dump)
        self.raw_data = [
            '[',
            '{"s": "Q1", "s_label": "Entity1", "p": "P1", "p_label": "Rel1", "o": "Q2", "o_label": "Entity2", "start": "2020"},',
            '{"s": "Q3", "p": "P2", "o": "Q4"}', # Minimal fields
            ']'
        ]
        with open(self.input_file, "w") as f:
            f.write("\n".join(self.raw_data))

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_pipeline_flow(self):
        # 1. Run Adapter
        process_file(str(self.input_file), str(self.intermediate_file))
        
        # Verify intermediate output exists and has content
        self.assertTrue(self.intermediate_file.exists())
        with open(self.intermediate_file, "r") as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 2) # Should extract 2 quadruplets
            item1 = json.loads(lines[0])
            self.assertEqual(item1['s']['id'], 'Q1')
            self.assertEqual(item1['t']['prop']['start'], '2020')

        # 2. Run CoreLoader
        # Mock KG Model
        mock_kg_model = MagicMock()
        mock_logger = MagicMock()
        
        loader = CoreLoader(mock_kg_model, mock_logger)
        loader.load_from_jsonl(str(self.intermediate_file), batch_size=10)
        
        # Verify mock interaction
        # Should call add_knowledge once with a list of 2 Quadruplets
        mock_kg_model.add_knowledge.assert_called_once()
        call_args = mock_kg_model.add_knowledge.call_args
        quadruplets_arg = call_args[0][0] # First arg is the list
        
        self.assertEqual(len(quadruplets_arg), 2)
        self.assertIsInstance(quadruplets_arg[0], Quadruplet)
        self.assertEqual(quadruplets_arg[0].start_node.name, "Entity1")
        self.assertEqual(quadruplets_arg[0].time.type.value, "time") # From first item
        
        self.assertEqual(quadruplets_arg[1].relation.name, "P2") # Fallback for P2 label (using ID is better than Unknown)
        self.assertEqual(quadruplets_arg[1].time.name, "Always") # Default for second item

        print("Integration Test Passed: Adapter -> JSONL -> CoreLoader -> MockKG")

if __name__ == "__main__":
    unittest.main()
