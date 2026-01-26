from typing import List, Dict
from collections import deque
import pytest
import sys

# TO CHANGE
PROJECT_BASE_DIR = '../'
sys.path.insert(0, PROJECT_BASE_DIR)

from src.utils import AgentTaskSolver, Triplet
from src.utils.errors import ReturnStatus

from cases import NO_THESIS_REPL_AGENT_ANSWER, ONE_THESIS_REPL_AGENT_ANSWER,\
    SEVERAL_THESIS_REPL_AGENT_ANSWER, BAD_THESIS_AGENT_ANSWER

from cases import HYPER_TRIPLET1, HYPER_TRIPLET2, HYPER_TRIPLET3, HYPER_TRIPLET4, HYPER_TRIPLET5

@pytest.mark.parametrize("llm_stub_answer, base_triplet, lang, incident_triplets, expected_status, expected_output", [
    # нет замен
    (NO_THESIS_REPL_AGENT_ANSWER, HYPER_TRIPLET1, 'en', [HYPER_TRIPLET2, HYPER_TRIPLET3], ReturnStatus.success, []),
    # одна замена
    (ONE_THESIS_REPL_AGENT_ANSWER, HYPER_TRIPLET2, 'en', [HYPER_TRIPLET4, HYPER_TRIPLET3], ReturnStatus.success, [HYPER_TRIPLET4.id]),
    # несколько замен
    (SEVERAL_THESIS_REPL_AGENT_ANSWER, HYPER_TRIPLET3, 'en', [HYPER_TRIPLET4, HYPER_TRIPLET5], ReturnStatus.success, [HYPER_TRIPLET4.id, HYPER_TRIPLET5.id]),
    # ответ сгенерирован в неверном формате (parse error?)
    (BAD_THESIS_AGENT_ANSWER, HYPER_TRIPLET1, 'en', [HYPER_TRIPLET4, HYPER_TRIPLET3], ReturnStatus.success, []),
])
def test_replace_thesises(replace_thesis_agent_solver: AgentTaskSolver, llm_stub_answer: str, lang: str,
                          base_triplet: Triplet, incident_triplets: List[Triplet],
                          expected_status: ReturnStatus, expected_output: List[str]):

    replace_thesis_agent_solver.agent.looped_answers = deque([llm_stub_answer])

    real_output, real_status = replace_thesis_agent_solver.solve(lang=lang, base_triplet=base_triplet,
                                     incident_triplets=incident_triplets)

    assert real_status == expected_status

    if real_output is None:
        assert expected_output is real_output
    else:
        assert real_output == expected_output
