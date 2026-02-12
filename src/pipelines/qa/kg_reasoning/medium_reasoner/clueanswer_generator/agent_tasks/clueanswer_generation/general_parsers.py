from typing import List

from ........utils import Quadruplet, QuadrupletCreator

def cagen_custom_formate(query: str, quadruplets: List[Quadruplet]) -> str:
    if len(query) < 1:
        raise ValueError

    filtered_context = list(map(lambda quadruplet: f"- {(QuadrupletCreator.stringify(quadruplet)[1] if quadruplet.stringified is None else quadruplet.stringified).strip()}", quadruplets))
    return {'c':"\n".join(filtered_context) if len(filtered_context) else "<|Empty|>", 'q': query}

def cagen_custom_postprocess(parsed_response: str, **kwargs) -> str:
    if len(parsed_response) < 1:
        raise ValueError

    return parsed_response
