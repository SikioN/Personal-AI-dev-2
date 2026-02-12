from typing import List, Dict, Set

from ......utils import Quadruplet
from ......utils.data_structs import create_id

def rs_quadruplet_custom_formate(base_quadruplet: Quadruplet, incident_quadruplets: List[Quadruplet]) -> Dict[str,str]:
    if len(incident_quadruplets) < 1:
        raise ValueError

    def _custom_quadruplet_stringify(quadruplet: Quadruplet) -> str:
        # Include time in the string representation for better LLM context
        time_str = f", Time: {quadruplet.time.name}" if quadruplet.time else ""
        return f"{quadruplet.start_node.name}, {quadruplet.relation.name}, {quadruplet.end_node.name}{time_str}"

    new_str_quadruplet = f'"{_custom_quadruplet_stringify(base_quadruplet)}"'
    existing_str_quadruplets = '; '.join(map(lambda q: f'"{_custom_quadruplet_stringify(q)}"', incident_quadruplets))

    return {'ex_triplets': existing_str_quadruplets, 'new_triplets': new_str_quadruplet}

def rs_quadruplet_custom_postprocess(parsed_response: Dict[str, Set[str]], base_quadruplet: Quadruplet, incident_quadruplets: List[Quadruplet]) -> List[str]:
    if len(incident_quadruplets) < 1:
        raise ValueError

    def _custom_quadruplet_stringify(quadruplet: Quadruplet) -> str:
        # Consistency in stringification key for creating IDs
        time_str = f", Time: {quadruplet.time.name}" if quadruplet.time else ""
        return f"{quadruplet.start_node.name}, {quadruplet.relation.name}, {quadruplet.end_node.name}{time_str}"

    custom_ids_to_quadruplets = {create_id(_custom_quadruplet_stringify(q)): q for q in incident_quadruplets}
    
    # We must ensure the LLM output matches these IDs. 
    # The LLM is likely asked to return the *text* or *id*? 
    # "parsed_response" is Dict[str, Set[str]]. 
    # The prompts likely ask for the *string representation* of the obsolete triplet.
    # The `create_id` hashes that string.
    # We need to verify if the LLM prompt is updated to handle/output the time component in the string?
    # I am not updating the prompt file now, but if the LLM sees the string with Time, it should output it with Time (ignoring minor diffs handled by parser?).
    # Standard parsers usually match exact strings or use fuzzy matching.
    # If the parser expects the LLM to return exactly "S, R, O, Time: T", and the LLM does, then `create_id` works.
    
    base_quadruplet_custom_id = create_id(_custom_quadruplet_stringify(base_quadruplet))
    obsolete_str_ids = parsed_response.get(base_quadruplet_custom_id, [])

    quadruplet_ids_to_remove = []
    for custom_id in custom_ids_to_quadruplets.keys():
        if custom_id in obsolete_str_ids:
            quadruplet_ids_to_remove.append(custom_ids_to_quadruplets[custom_id].id)

    return quadruplet_ids_to_remove
