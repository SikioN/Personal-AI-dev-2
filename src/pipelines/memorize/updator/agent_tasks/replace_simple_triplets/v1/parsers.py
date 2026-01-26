from typing import Dict
from collections import defaultdict

from .......utils.data_structs import create_id

def rs_custom_parse(raw_response: str, **kwargs) -> Dict[str, object]:
    if len(raw_response) < 1:
        raise ValueError

    raw_replacements = raw_response.lower()
    raw_replacements = raw_replacements.split("[[")[-1] if "[[" in raw_replacements else raw_replacements.split("[\n[")[-1]
    pairs = raw_replacements.replace("[", "").strip("]").split("],")
    triplets_to_remove = defaultdict(set)
    for pair in pairs:
        splitted_pair = pair.split("->")
        if len(splitted_pair) != 2:
            continue

        existing_triplet = splitted_pair[0].split(",")
        if len(existing_triplet) != 3:
            continue
        str_existing_triplet = splitted_pair[0].strip(''' \n'".,/''')

        new_triplet = splitted_pair[1].split(",")
        if len(new_triplet) != 3:
            continue
        str_new_triplet = splitted_pair[1].strip(''' \n'".,/''')

        triplets_to_remove[create_id(str_new_triplet)].add(create_id(str_existing_triplet))

    return triplets_to_remove
