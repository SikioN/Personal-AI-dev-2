from typing import List, Dict

def cqgen_custom_formate(query: str, base_entities: List[str], matched_objects: List[str]) -> Dict[str, str]:
    if len(query) < 1 or len(base_entities) < 1 or len(matched_objects) != len(base_entities):
        raise ValueError
    
    str_e2o_matching = "\n".join([f'{ent}: {obj}' for ent, obj in zip(base_entities, matched_objects)])

    return {'query': query, 'matched_entities': str_e2o_matching}

def cqgen_custom_postprocess(parsed_response: List[str], **kwargs) -> List[str]:
    if len(parsed_response) < 1:
        raise ValueError

    return parsed_response