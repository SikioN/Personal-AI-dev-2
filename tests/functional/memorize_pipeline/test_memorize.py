import pytest
from typing import List, Dict
from tqdm import tqdm

import sys
# TO CHANGE
PROJECT_BASE_DIR = '../'
sys.path.insert(0, PROJECT_BASE_DIR)

from src.pipelines.memorize import MemPipeline, MemPipelineConfig
from src.kg_model import KnowledgeGraphModel

from cases import MEM_CONFIG1, MEM_CONFIG2, KV_CACHE_CONFIG, RAW_TEXTS_EN

@pytest.mark.parametrize("mem_config, raw_texts, use_kv_cache, clear_kv_cache", [
    [MEM_CONFIG1, RAW_TEXTS_EN, True, False],
    [MEM_CONFIG1, RAW_TEXTS_EN, True, True],
    [MEM_CONFIG2, RAW_TEXTS_EN, True, False],
    [MEM_CONFIG2, RAW_TEXTS_EN, True, True]])
def test_mem_pipeline(mem_config: MemPipelineConfig, raw_texts: List[str],
                      use_kv_cache: bool, clear_kv_cache: bool, kg_model: KnowledgeGraphModel):
    kg_model.clear()

    g_items_count = kg_model.graph_struct.count_items()
    assert g_items_count['triplets'] == 0
    assert g_items_count['nodes'] == 0
    e_items_count = kg_model.embeddings_struct.count_items()
    assert e_items_count['nodes'] == 0
    assert e_items_count['triplets'] == 0

    kv_cache_config = None
    if use_kv_cache:
        kv_cache_config = KV_CACHE_CONFIG
    mem_pipeline = MemPipeline(kg_model, mem_config, kv_cache_config)

    for text in tqdm(raw_texts):
        _, status = mem_pipeline.remember(text)
        assert status.status.value == 0

    mem_pipeline.updator.kg_model.graph_struct.db_conn.close_connection()
    mem_pipeline.updator.kg_model.embeddings_struct.vectordbs['nodes'].close_connection()
    mem_pipeline.updator.kg_model.embeddings_struct.vectordbs['triplets'].close_connection()

    if use_kv_cache:
        if clear_kv_cache:
            mem_pipeline.extractor.thesises_extraction_solver.cachekv.kv_conn.clear()
            mem_pipeline.extractor.triplets_extraction_solver.cachekv.kv_conn.clear()
            mem_pipeline.updator.replace_hyper_solver.cachekv.kv_conn.clear()
            mem_pipeline.updator.replace_simple_solver.cachekv.kv_conn.clear()

        mem_pipeline.extractor.thesises_extraction_solver.cachekv.kv_conn.close_connection()
        mem_pipeline.extractor.triplets_extraction_solver.cachekv.kv_conn.close_connection()
        mem_pipeline.updator.replace_hyper_solver.cachekv.kv_conn.close_connection()
        mem_pipeline.updator.replace_simple_solver.cachekv.kv_conn.close_connection()

    mem_pipeline.extractor.agent.close_connection()
    mem_pipeline.updator.agent.close_connection()
