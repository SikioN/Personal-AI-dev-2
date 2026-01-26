from typing import List

def qd_custom_parse(raw_response: str, **kwargs) -> List[str]:
    if len(raw_response) < 1:
        raise ValueError
    
    parsed_subq = list(filter(lambda sub_q: len(sub_q), raw_response.split("\n")))
    
    formated_subq = list(map(lambda subq: subq.strip("- "), parsed_subq))
    formated_subq = list(filter(lambda sub_q: len(sub_q), formated_subq))
    if len(formated_subq) < 2:
        raise ValueError
    
    return formated_subq