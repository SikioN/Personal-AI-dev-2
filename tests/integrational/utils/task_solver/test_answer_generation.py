# import pytest

# import sys
# sys.path.insert(0, "../")

# from src.utils import Triplet, ReturnStatus
# from src.utils import AgentTaskSolver
# from typing import List, Dict

# @pytest.mark.parametrize("lang, query, context_triplets, agent_stub_answers, expected_answer, expected_status", [
#     # 1. русский язык
#     # 1.1. позитивный тест
#     # 1.1.1 найдена одна устаревшая связь
#     ('ru', ..., ..., ..., ..., ReturnStatus.success),
#     # 1.1.2 найдена несколько устаревших связей
#     ('ru', ..., ..., ..., ..., ReturnStatus.success),
#     # 1.1.3 устаревший связей не найдено
#     ('ru', ..., ..., ..., [], ReturnStatus.success),
#     # 1.2. ошибка в formater-функции (пустой список existing-триплетов)
#     ('ru', ..., ..., ..., None, ReturnStatus.bad_formater),
#     # 1.3. ошибка мапинга значений в user-prompt
#     # TODO
#     # 1.4. ошибка генерации
#     # TODO
#     # 1.5. ошибка в parser-функции
#     ('ru', ..., ..., ..., None, ReturnStatus.bad_parser),
#     # 1.6. ошибка в postprocessor-функции
#     # TODO
#     # 2. английский язык
#     # 2.1. позитивный тест
#     # 2.1.1 найдена одна устаревшая связь
#     ('en', ..., ..., ..., ..., ReturnStatus.success),
#     # 2.1.2 найдена несколько устаревших связей
#     ('en', ..., ..., ..., ..., ReturnStatus.success),
#     # 2.1.3 устаревший связей не найдено
#     ('en', ..., ..., ..., [], ReturnStatus.success),
#     # 2.2. ошибка в formater-функции (пустой список existing-триплетов)
#     ('en', ..., ..., [], None, ReturnStatus.bad_formater),
#     # 2.3. ошибка мапинга значений в user-prompt
#     # TODO
#     # 2.4. ошибка генерации
#     # TODO
#     # 2.5. ошибка в parser-функции
#     ('en', ..., ..., ..., None, ReturnStatus.bad_parser),
#     # 2.6. ошибка в postprocessor-функции
#     # TODO
#     # 3. ошибка при распознавании языка
#     # TODO
# ])
# def test_answer_generation(ag_solver: AgentTaskSolver, lang: str, query: str, context_triplets: List[Triplet],
#                            agent_stub_answers: List[str], expected_answer: str, expected_status: ReturnStatus):
#     ag_solver.agent.looped_answers.clear()
#     ag_solver.agent.looped_answers += agent_stub_answers

#     real_answer, real_status = ag_solver.solve(lang, query=query, context_tripelets=context_triplets)
#     assert expected_status == real_status
#     assert expected_answer == real_answer
