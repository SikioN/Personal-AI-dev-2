from typing import List
import re

def answgen_custom_parse(raw_response: str, **kwargs) -> List[str]:
    if len(raw_response) < 1:
        raise ValueError

    answer_pos = re.search(r"\[answer\]", raw_response, re.IGNORECASE)

    # Ответ не соответствует формату
    if answer_pos is None:
        raise ValueError

    answer = raw_response[answer_pos.span(0)[1]:].strip()

    # Пустой ответ
    if len(answer) < 1:
        raise ValueError

    return answer