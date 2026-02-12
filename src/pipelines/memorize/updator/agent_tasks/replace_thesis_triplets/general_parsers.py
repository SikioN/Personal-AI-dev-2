from typing import List, Dict, Set

from ......utils import Quadruplet
from ......utils.data_structs import create_id

def rt_quadruplet_custom_formate(base_quadruplet: Quadruplet, incident_quadruplets: List[Quadruplet]) -> Dict[str,str]:
    if len(incident_quadruplets) < 1:
        raise ValueError

    def _custom_thesis_stringify(quadruplet: Quadruplet) -> str:
        time_str = f" (Time: {quadruplet.time.name})" if quadruplet.time else ""
        return f"{quadruplet.end_node.name}{time_str}"

    new_str_thesis = f'["{_custom_thesis_stringify(base_quadruplet)}"]'
    existing_str_thesises = '[' +', '.join(map(lambda q: f'"{_custom_thesis_stringify(q)}"', incident_quadruplets)) + ']'

    return {'ex_thesises': existing_str_thesises, 'new_thesises': new_str_thesis}

def rt_quadruplet_custom_postprocess(parsed_response: Dict[str, Set[str]], base_quadruplet: Quadruplet, incident_quadruplets: List[Quadruplet]) -> List[str]:
    if len(incident_quadruplets) < 1:
        raise ValueError

    def _custom_thesis_stringify(quadruplet: Quadruplet) -> str:
        time_str = f" (Time: {quadruplet.time.name})" if quadruplet.time else ""
        return f"{quadruplet.end_node.name}{time_str}"

    custom_ids_to_quadruplets = {create_id(_custom_thesis_stringify(q)): q for q in incident_quadruplets}
    
    base_quadruplet_custom_id = create_id(_custom_thesis_stringify(base_quadruplet))
    obsolete_str_ids = parsed_response.get(base_quadruplet_custom_id, [])

    quadruplet_ids_to_remove = []
    for custom_id in custom_ids_to_quadruplets.keys():
        if custom_id in obsolete_str_ids:
            quadruplet_ids_to_remove.append(custom_ids_to_quadruplets[custom_id].id)

    return quadruplet_ids_to_remove
