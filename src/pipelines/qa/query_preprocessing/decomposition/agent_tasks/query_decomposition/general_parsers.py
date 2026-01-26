from typing import List

def qd_custom_formate(query: str) -> str:
    if len(query) < 1:
        raise ValueError

    return {'query': query}

def qd_custom_postprocess(parsed_response: List[str], **kwargs) -> List[str]:
    if len(parsed_response) < 1:
        raise ValueError

    return list(map(lambda subq: subq.strip(), parsed_response))
