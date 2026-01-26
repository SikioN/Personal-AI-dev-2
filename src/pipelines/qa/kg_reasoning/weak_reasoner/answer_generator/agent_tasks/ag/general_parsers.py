from typing import List

from ........utils import Triplet, TripletCreator

def simpleag_custom_formate(query: str, triplets: List[Triplet]) -> str:
    if len(query) < 1:
        raise ValueError

    filtered_context = list(map(lambda triplet: f"- {(TripletCreator.stringify(triplet)[1] if triplet.stringified is None else triplet.stringified).strip()}", triplets))
    return {'c':"\n".join(filtered_context) if len(filtered_context) else "<|Empty|>", 'q': query}

def simpleag_custom_postprocess(parsed_response: str, **kwargs) -> str:
    if len(parsed_response) < 1:
        raise ValueError

    return parsed_response
