from typing import List, Dict, Set

from ......utils import Triplet
from ......utils.data_structs import create_id

def rs_custom_formate(base_triplet: Triplet, incident_triplets: List[Triplet]) -> Dict[str,str]:
    if len(incident_triplets) < 1:
        raise ValueError

    def _custom_triplet_stringify(triplet: Triplet) -> str:
        return f"{triplet.start_node.name}, {triplet.relation.name}, {triplet.end_node.name}"

    new_str_triplet = f'"{_custom_triplet_stringify(base_triplet)}"'
    existing_str_triplets = '; '.join(map(lambda triplet: f'"{_custom_triplet_stringify(triplet)}"', incident_triplets))

    return {'ex_triplets': existing_str_triplets, 'new_triplets': new_str_triplet}

def rs_custom_postprocess(parsed_response: Dict[str, Set[str]], base_triplet: Triplet, incident_triplets: List[Triplet]) -> List[str]:
    if len(incident_triplets) < 1:
        raise ValueError

    def _custom_triplet_stringify(triplet: Triplet) -> str:
        return f"{triplet.start_node.name}, {triplet.relation.name}, {triplet.end_node.name}"

    custom_ids_to_triplets = {create_id(_custom_triplet_stringify(triplet)): triplet for triplet in incident_triplets}
    base_triplet_custom_id = create_id(_custom_triplet_stringify(base_triplet))
    obsolete_str_ids = parsed_response.get(base_triplet_custom_id, [])

    triplet_ids_to_remove = []
    for custom_id in custom_ids_to_triplets.keys():
        if custom_id in obsolete_str_ids:
            triplet_ids_to_remove.append(custom_ids_to_triplets[custom_id].id)

    return triplet_ids_to_remove
