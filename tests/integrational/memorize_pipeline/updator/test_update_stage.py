import pytest

import sys
sys.path.insert(0, "../")

from src.utils import Triplet
from src.pipelines.memorize import LLMUpdator

from typing import List, Dict

# @pytest.mark.parametrize("kg_triplets, new_triplets, agent_stub_answers, obsolete_flag, expected_kg", [
#     # TODO
# ])
# def test_update_knowledge(llm_updator: LLMUpdator, kg_triplets: List[Triplet], new_triplets: List[Triplet], obsolete_flag: bool,
#                      agent_stub_answers: List[str], expected_graph_ids: List[str], expected_vector_node_ids: List[str],
#                      expected_vector_triplet_ids: List[str]):
#     llm_updator.kg_model.clear()
#     llm_updator.kg_model.add_knowledge(kg_triplets)

#     llm_updator.agent.looped_answers.clear()
#     llm_updator.agent.looped_answers += agent_stub_answers

#     llm_updator.update_knowledge(new_triplets, delete_obsolete_info=obsolete_flag)

#     # TODO
