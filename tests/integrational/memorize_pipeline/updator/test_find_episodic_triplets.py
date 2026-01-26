import pytest

import sys
sys.path.insert(0, "../")

from src.utils import Triplet
from src.pipelines.memorize import LLMUpdator

from typing import List, Dict

from cases import INIT_KNOWLEDGE_GRAPH
from cases import TEST_O_EPISODIC1, TEST_O_EPISODIC2, TEST_DELETE_TRIPLETS1, TEST_DELETE_TRIPLETS2
from cases import TEST_H_EPISODIC1, TEST_DELETE_TRIPLETS3, TEST_H_EPISODIC2,\
    TEST_DELETE_TRIPLETS4, TEST_H_EPISODIC3, EPISODIC_TRIPLET3, EPISODIC_TRIPLET13, EPISODIC_TRIPLET14, EPISODIC_TRIPLET1

@pytest.mark.parametrize("kg_triplets, base_triplet, delete_tripelts, expected_obsolete_ids", [
    # 1. не найдено устаревших трипелтов
    # 1.1. нуль сопоставленных object-вершин
    (INIT_KNOWLEDGE_GRAPH, TEST_O_EPISODIC1, [], set()),
    # 1.2. нуль смежных episodic-вершин
    (INIT_KNOWLEDGE_GRAPH, TEST_O_EPISODIC2, TEST_DELETE_TRIPLETS1, set()),
    # 2. есть общие hyper-вершины у данной object-вершины и episodic-вершины
    (INIT_KNOWLEDGE_GRAPH, TEST_O_EPISODIC2, [], set()),
    # 3. найден один устаревший триплет
    (INIT_KNOWLEDGE_GRAPH, TEST_O_EPISODIC2, TEST_DELETE_TRIPLETS2, {EPISODIC_TRIPLET1.id})
])
def test_find_o_episodic(llm_updator: LLMUpdator, kg_triplets: List[Triplet],
                         base_triplet: Triplet, delete_tripelts: List[Triplet],
                         expected_obsolete_ids: List[str]):
    llm_updator.kg_model.clear()
    llm_updator.kg_model.add_knowledge(kg_triplets)
    llm_updator.kg_model.remove_knowledge(delete_tripelts)

    real_obsolete_ids  = llm_updator.find_episodic_o_obsolete_triplet_ids(base_triplet)
    assert len(real_obsolete_ids) == len(expected_obsolete_ids)
    assert expected_obsolete_ids == set(real_obsolete_ids)

@pytest.mark.parametrize("kg_triplets, base_triplet, delete_tripelts, expected_obsolete_ids", [
    # 1. не найдено устаревших трипелтов
    # 1.1. нуль сопоставленных hyper-вершин
    (INIT_KNOWLEDGE_GRAPH, TEST_H_EPISODIC1, [], set()),
    # 1.2. у сопоставленных hyper-вершин есть смежные object-вершины
    (INIT_KNOWLEDGE_GRAPH, TEST_H_EPISODIC2, [], set()),
    # 1.3. найден один устаревший триплет
    (INIT_KNOWLEDGE_GRAPH, TEST_H_EPISODIC2, TEST_DELETE_TRIPLETS3, {EPISODIC_TRIPLET3.id}),
    # 2. найдено несколько устаревших триплетов
    (INIT_KNOWLEDGE_GRAPH, TEST_H_EPISODIC3, TEST_DELETE_TRIPLETS4, {EPISODIC_TRIPLET13.id, EPISODIC_TRIPLET14.id}),
])
def test_find_h_episodic(llm_updator: LLMUpdator, kg_triplets: List[Triplet],
                         base_triplet: Triplet, delete_tripelts: List[Triplet],
                         expected_obsolete_ids: List[str]):
    llm_updator.kg_model.clear()
    llm_updator.kg_model.add_knowledge(kg_triplets)
    llm_updator.kg_model.remove_knowledge(delete_tripelts)

    real_obsolete_ids  = llm_updator.find_episodic_h_obsolete_triplet_ids(base_triplet)

    assert len(real_obsolete_ids) == len(expected_obsolete_ids)
    assert expected_obsolete_ids == set(real_obsolete_ids)
