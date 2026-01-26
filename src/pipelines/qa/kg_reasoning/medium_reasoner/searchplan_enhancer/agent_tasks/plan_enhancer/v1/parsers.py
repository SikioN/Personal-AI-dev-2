from typing import List
import re

def planenh_custom_parse(raw_response: str, **kwargs) -> List[str]:
    if len(raw_response) < 1:
        raise ValueError
    
    parsed_steps = list(map(lambda raw_step: re.search(r"[\d]{,2}. (.*)", raw_step) , raw_response.split("\n")))
    filtered_steps = list(filter(lambda step: step is not None, parsed_steps))
    try:
        formated_steps = list(map(lambda step: step.group(1), filtered_steps))
    except IndexError:
        raise ValueError
    
    return formated_steps