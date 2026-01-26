from typing import List

def dc_custom_formate(query: str) -> str:
    if len(query) < 1:
        raise ValueError

    return {'query': query}

def dc_custom_postprocess(parsed_response: str, **kwargs) -> bool:
    if len(parsed_response) < 1:
        raise ValueError
    
    if parsed_response.startswith("Yes"):
        candecomp_sign = True
    elif parsed_response.startswith("No"):
         candecomp_sign = False
    else:
        raise ValueError   

    return candecomp_sign