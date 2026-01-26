from typing import List

def planinit_custom_formate(query: str):
    if len(query) < 1:
        raise ValueError
    
    return {'query': query}

def planinit_custom_postprocess(parsed_response: List[str], **kwargs) -> List[str]:
    if len(parsed_response) < 1:
        raise ValueError

    return parsed_response