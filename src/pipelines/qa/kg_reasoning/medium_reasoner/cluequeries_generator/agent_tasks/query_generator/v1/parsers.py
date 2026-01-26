from typing import List

def cqgen_custom_parse(raw_response: str, **kwargs) -> List[str]:
    if len(raw_response) < 1:
        raise ValueError

    cluequery = raw_response.strip() 

    return cluequery