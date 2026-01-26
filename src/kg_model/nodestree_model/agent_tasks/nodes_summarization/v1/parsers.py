from typing import List
import re

def summn_custom_parse(raw_response: str, **kwargs) -> List[str]:
    # Пустой ответ
    raw_response = raw_response.strip(' .')
    if len(raw_response) < 1:
        raise ValueError

    summary = None
    finded_pattern = re.search(r"\[Output Summary\]\n(.+?)$", raw_response)
    if finded_pattern is not None:
        summary = finded_pattern.group(1)
    else:
        summary = raw_response

    return summary
