from typing import List, Dict
from collections import deque
import pytest
import sys

# TO CHANGE
PROJECT_BASE_DIR = '../'
sys.path.insert(0, PROJECT_BASE_DIR)

from src.utils import AgentTaskSolver, Triplet
from src.utils.errors import ReturnStatus

from cases import NO_TRIPLET_REPL_AGENT_ANSWER, ONE_TRIPLET_REPL_AGENT_ANSWER,\
    SEVERAL_TRIPLET_REPL_AGENT_ANSWER, BAD_TRIPLET_AGENT_ANSWER

from cases import SIMPLE_TRIPLET1, SIMPLE_TRIPLET2, SIMPLE_TRIPLET3,\
    SIMPLE_TRIPLET4, SIMPLE_TRIPLET5, SIMPLE_TRIPLET6

@pytest.mark.parametrize("llm_stub_answer, base_triplet, lang, incident_triplets, expected_status, expected_output", [
    # нет замен
    (NO_TRIPLET_REPL_AGENT_ANSWER, SIMPLE_TRIPLET1, 'en', [SIMPLE_TRIPLET2, SIMPLE_TRIPLET3], ReturnStatus.success, []),
    # одна замена
    (ONE_TRIPLET_REPL_AGENT_ANSWER, SIMPLE_TRIPLET2, 'en', [SIMPLE_TRIPLET4, SIMPLE_TRIPLET5], ReturnStatus.success, [SIMPLE_TRIPLET4.id]),
    # несколько замен
    (SEVERAL_TRIPLET_REPL_AGENT_ANSWER, SIMPLE_TRIPLET3, 'en', [SIMPLE_TRIPLET5, SIMPLE_TRIPLET6], ReturnStatus.success, [SIMPLE_TRIPLET5.id, SIMPLE_TRIPLET6.id]),
    # ответ сгенерирован в неверном формате (parse error?)
    (BAD_TRIPLET_AGENT_ANSWER, SIMPLE_TRIPLET1, 'en', [SIMPLE_TRIPLET4, SIMPLE_TRIPLET5], ReturnStatus.success, []),
])
def test_replace_triplets(replace_simple_agent_solver: AgentTaskSolver, llm_stub_answer: str, lang: str,
                          base_triplet: Triplet, incident_triplets: List[Triplet],
                          expected_status: ReturnStatus, expected_output: List[str]):

    replace_simple_agent_solver.agent.looped_answers = deque([llm_stub_answer])

    real_output, real_status = replace_simple_agent_solver.solve(lang=lang, base_triplet=base_triplet,
                                     incident_triplets=incident_triplets)

    assert real_status == expected_status

    if real_output is None:
        assert expected_output is real_output
    else:
        assert real_output == expected_output
