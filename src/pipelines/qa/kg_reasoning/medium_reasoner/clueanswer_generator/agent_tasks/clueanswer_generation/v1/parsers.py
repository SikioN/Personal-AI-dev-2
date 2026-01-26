from typing import List
import re

def cagen_custom_parse(raw_response: str, **kwargs) -> List[str]:
    if len(raw_response) < 1:
        raise ValueError

    answer = raw_response.strip()

    # Пустой ответ
    if len(answer) < 1:
        raise ValueError

    return answer