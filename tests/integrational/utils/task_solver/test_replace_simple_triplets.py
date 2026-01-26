import pytest

import sys
sys.path.insert(0, "../")

from src.utils import Triplet, ReturnStatus
from src.utils import AgentTaskSolver
from typing import List

from cases import EN_VALID_SIMPLE_TRIPLET1, EN_VALID_SIMPLE_TRIPLET2, EN_VALID_SIMPLE_TRIPLET3,\
      RU_VALID_SIMPLE_TRIPLET1, RU_VALID_SIMPLE_TRIPLET2, RU_VALID_SIMPLE_TRIPLET3

RU_MATCHED_OBOSLETE_TRIPELET_2 = '[["фыв, епи, ячс" -> "йцу, епи, фыв"]]'
RU_MATCHED_OBSOLETE_TRIPLET_2AND3 = '[["фыв, епи, ячс" -> "йцу, епи, фыв"],["ячс, епи, йцу" -> "йцу, епи, фыв"]]'
RU_ZERO_MATCHED_OBSOLETE_TRIPLETS = '[]'
RU_BAD_REPONSE_TRIPLET_2AND3 = '[["фыв, епи, ячс" "йцу, епи, фыв"],["ячс, епи, йцу" "йцу, епи, фыв"]]'

EN_MATCHED_OBOSLETE_TRIPELET_2 = '[["asd, zxc, uio" -> "qwe, zxc, asd"]]'
EN_MATCHED_OBSOLETE_TRIPLET_2AND3 = '[["asd, zxc, uio" -> "qwe, zxc, asd"],["uio, zxc, qwe" -> "qwe, zxc, asd"]]'
EN_ZERO_MATCHED_OBSOLETE_TRIPLETS = '[]'
EN_BAD_REPONSE_TRIPLET_2AND3 = '[["asd, zxc, uio" "qwe, zxc, asd"],["uio, zxc, qwe" "qwe, zxc, asd"]]'

@pytest.mark.parametrize("lang, base_triplet, incident_triplets, agent_stub_answers, expected_triplet_ids, expected_status", [
    # 1. русский язык
    # 1.1. позитивный тест
    # 1.1.1 найдена одна устаревшая связь
    ('ru', RU_VALID_SIMPLE_TRIPLET1, [RU_VALID_SIMPLE_TRIPLET2, RU_VALID_SIMPLE_TRIPLET3], [RU_MATCHED_OBOSLETE_TRIPELET_2], [RU_VALID_SIMPLE_TRIPLET2.id], ReturnStatus.success),
    # 1.1.2 найдена несколько устаревших связей
    ('ru', RU_VALID_SIMPLE_TRIPLET1, [RU_VALID_SIMPLE_TRIPLET2, RU_VALID_SIMPLE_TRIPLET3], [RU_MATCHED_OBSOLETE_TRIPLET_2AND3], [RU_VALID_SIMPLE_TRIPLET2.id, RU_VALID_SIMPLE_TRIPLET3.id], ReturnStatus.success),
    # 1.1.3 устаревший связей не найдено
    ('ru', RU_VALID_SIMPLE_TRIPLET1, [RU_VALID_SIMPLE_TRIPLET2, RU_VALID_SIMPLE_TRIPLET3], [RU_ZERO_MATCHED_OBSOLETE_TRIPLETS], [], ReturnStatus.success),
    # 1.2. ошибка в formater-функции (пустой список existing-триплетов)
    ('ru', RU_VALID_SIMPLE_TRIPLET1, [], [], None, ReturnStatus.bad_formater),
    # 1.3. ошибка мапинга значений в user-prompt
    # TODO
    # 1.4. ошибка генерации
    # TODO
    # 1.5. ошибка в parser-функции
    ('ru', RU_VALID_SIMPLE_TRIPLET1, [RU_VALID_SIMPLE_TRIPLET2, RU_VALID_SIMPLE_TRIPLET3], [RU_BAD_REPONSE_TRIPLET_2AND3], None, ReturnStatus.bad_parser),
    # 1.6. ошибка в postprocessor-функции
    # TODO
    # 2. английский язык
    # 2.1. позитивный тест
    # 2.1.1 найдена одна устаревшая связь
    ('en', EN_VALID_SIMPLE_TRIPLET1, [EN_VALID_SIMPLE_TRIPLET2, EN_VALID_SIMPLE_TRIPLET3], [EN_MATCHED_OBOSLETE_TRIPELET_2], [EN_VALID_SIMPLE_TRIPLET2.id], ReturnStatus.success),
    # 2.1.2 найдена несколько устаревших связей
    ('en', EN_VALID_SIMPLE_TRIPLET1, [EN_VALID_SIMPLE_TRIPLET2, EN_VALID_SIMPLE_TRIPLET3], [EN_MATCHED_OBSOLETE_TRIPLET_2AND3], [EN_VALID_SIMPLE_TRIPLET2.id, EN_VALID_SIMPLE_TRIPLET3.id], ReturnStatus.success),
    # 2.1.3 устаревший связей не найдено
    ('en', EN_VALID_SIMPLE_TRIPLET1, [EN_VALID_SIMPLE_TRIPLET2, EN_VALID_SIMPLE_TRIPLET3], [EN_ZERO_MATCHED_OBSOLETE_TRIPLETS], [], ReturnStatus.success),
    # 2.2. ошибка в formater-функции (пустой список existing-триплетов)
    ('en', EN_VALID_SIMPLE_TRIPLET1, [], [], None, ReturnStatus.bad_formater),
    # 2.3. ошибка мапинга значений в user-prompt
    # TODO
    # 2.4. ошибка генерации
    # TODO
    # 2.5. ошибка в parser-функции
    ('en', EN_VALID_SIMPLE_TRIPLET1, [EN_VALID_SIMPLE_TRIPLET2, EN_VALID_SIMPLE_TRIPLET3], [EN_BAD_REPONSE_TRIPLET_2AND3], None, ReturnStatus.bad_parser),
    # 2.6. ошибка в postprocessor-функции
    # TODO
    # 3. ошибка при распознавании языка
    # TODO
])
def test_replace_simple(replace_simple_solver: AgentTaskSolver, lang: str, base_triplet: Triplet, incident_triplets: List[Triplet],
                        agent_stub_answers: List[str], expected_triplet_ids: List[str], expected_status: ReturnStatus):
    replace_simple_solver.agent.looped_answers.clear()
    replace_simple_solver.agent.looped_answers += agent_stub_answers

    real_triplet_ids, real_status = replace_simple_solver.solve(
        lang=lang, base_triplet=base_triplet, incident_triplets=incident_triplets)
    assert expected_status == real_status
    assert expected_triplet_ids == real_triplet_ids
