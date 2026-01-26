from typing import List
import re

def casumm_custom_parse(raw_response: str, **kwargs) -> str:
    if len(raw_response) < 1:
        raise ValueError

    answer_pos = re.search(r"\[answer\]", raw_response, re.IGNORECASE)

    # Ответ не соответствует формату
    if answer_pos is None:
        raise ValueError

    answer1 = raw_response[answer_pos.span(0)[1]:].strip()
    # Пустой ответ
    if len(answer1) < 1:
        raise ValueError
    
    answer2 = re.sub("<final-answer>", "", answer1).strip()
    # Пустой ответ
    if len(answer2) < 1:
        raise ValueError

    return answer2