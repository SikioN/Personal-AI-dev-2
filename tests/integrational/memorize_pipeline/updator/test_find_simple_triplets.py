import pytest

import sys
sys.path.insert(0, "../")

from src.utils import Triplet
from src.pipelines.memorize import LLMUpdator

from typing import List, Dict

from cases import INIT_KNOWLEDGE_GRAPH,\
    TEST_SIMPLE_TRIPLET1, TEST_SIMPLE_TRIPLET2,\
    TRIPLET_EMPTY_ANSWER, TEST_SIMPLE_TRIPLET4, TEST_SIMPLE_TRIPLET5,\
    TEST_SIMPLE_TRIPLET6, TRIPLET_ANSWER1, TRIPLET_ANSWER2, TRIPLET_ANSWER3,\
    BAD_SIMPLE_ANSWER

from cases import SIMPLE_TRIPLET1, SIMPLE_TRIPLET3

@pytest.mark.parametrize("kg_triplets, triplets, agent_stub_answers, expected_obsolete_ids", [
    # 1. не найдено устаревших трипелтов
    # 1.1. нуль сопоставленных вершин
    (INIT_KNOWLEDGE_GRAPH, [TEST_SIMPLE_TRIPLET1], [[]], [[]]),
    # 1.2. нуль смежных вершин
    (INIT_KNOWLEDGE_GRAPH, [TEST_SIMPLE_TRIPLET2], [[]], [[]]),
    # 1.3. нуль ids от agent-солвера
    (INIT_KNOWLEDGE_GRAPH, [TEST_SIMPLE_TRIPLET2], [[TRIPLET_EMPTY_ANSWER]], [[]]),
    # 2. найден один устаревший триплет
    (INIT_KNOWLEDGE_GRAPH, [TEST_SIMPLE_TRIPLET4], [[TRIPLET_ANSWER1]], [[SIMPLE_TRIPLET1.id]]),
    # 3. найдено несколько устаревших триплетов (разные замены)
    (INIT_KNOWLEDGE_GRAPH, [TEST_SIMPLE_TRIPLET4, TEST_SIMPLE_TRIPLET5], [[TRIPLET_ANSWER1], [TRIPLET_ANSWER2]], [[SIMPLE_TRIPLET1.id], [SIMPLE_TRIPLET3.id]]),
    # 4. найдено несколько устаревших триплетов (итеративная замена того же ребра)
    (INIT_KNOWLEDGE_GRAPH, [TEST_SIMPLE_TRIPLET4, TEST_SIMPLE_TRIPLET6], [[TRIPLET_ANSWER1], [TRIPLET_ANSWER3]], [[SIMPLE_TRIPLET1.id], [TEST_SIMPLE_TRIPLET4.id]]),
    # 5. ошибка при разборе сгенерированного ответа (parser error)
    (INIT_KNOWLEDGE_GRAPH, [TEST_SIMPLE_TRIPLET4], [[BAD_SIMPLE_ANSWER]], [[]])
])
def test_find_simple(llm_updator: LLMUpdator, kg_triplets: List[Triplet], triplets: List[Triplet],
                     agent_stub_answers: List[str], expected_obsolete_ids: List[str]):
    llm_updator.kg_model.clear()
    llm_updator.kg_model.add_knowledge(kg_triplets)

    for triplet, stub_answer, expected_output in zip(triplets, agent_stub_answers, expected_obsolete_ids):

        llm_updator.agent.looped_answers.clear()
        llm_updator.agent.looped_answers += stub_answer

        real_obsolete_ids  = llm_updator.find_simple_obsolete_triplet_ids(triplet)

        assert len(real_obsolete_ids) == len(expected_output)
        assert set(expected_output) == set(real_obsolete_ids)

        if len(real_obsolete_ids) > 0:
            obsolete_triplets = llm_updator.kg_model.graph_struct.db_conn.read(real_obsolete_ids)

            llm_updator.kg_model.remove_knowledge(obsolete_triplets)
            llm_updator.kg_model.add_knowledge([triplet])
