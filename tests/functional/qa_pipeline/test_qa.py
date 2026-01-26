import pytest
from typing import List, Dict
from tqdm import tqdm

import sys
# TO CHANGE
PROJECT_BASE_DIR = '../'
sys.path.insert(0, PROJECT_BASE_DIR)

from src.pipelines.qa import QAPipeline, QAPipelineConfig
from src.pipelines.memorize import MemPipeline

from cases import POPULATED_QA_CONFIGS, KV_CACHE_CONFIG

@pytest.mark.parametrize("qa_config, questions, use_kv_cache, clear_cache, clear_memory", POPULATED_QA_CONFIGS)
def test_qa_pipeline(qa_config: QAPipelineConfig, questions: List[str], use_kv_cache: bool, clear_cache: bool, clear_memory: bool, mem_pipeline: MemPipeline):
    g_items_count = mem_pipeline.updator.kg_model.graph_struct.count_items()
    assert g_items_count['triplets'] != 0
    assert g_items_count['nodes'] != 0
    e_items_count = mem_pipeline.updator.kg_model.embeddings_struct.count_items()
    assert e_items_count['nodes'] != 0
    assert e_items_count['triplets'] != 0

    kv_cache_config = None
    if use_kv_cache:
        kv_cache_config = KV_CACHE_CONFIG
    qa_pipeline = QAPipeline(mem_pipeline.updator.kg_model, qa_config, kv_cache_config)

    for question in questions:
        _, info = qa_pipeline.answer(question)
        assert info.status.value == 0

    if clear_cache:
        qa_pipeline.kg_reasoner.reasoner.clear_kv_caches()

    if clear_memory:
        mem_pipeline.updator.kg_model.clear()
