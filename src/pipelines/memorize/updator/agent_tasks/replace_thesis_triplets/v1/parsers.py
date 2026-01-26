from typing import Dict
from collections import defaultdict

from .......utils.data_structs import create_id


def rt_custom_parse(raw_response: str, **kwargs) -> Dict[str, object]:
    if len(raw_response) < 1:
        raise ValueError

    raw_replacements = raw_response.lower()
    predicted_outdated = raw_replacements.split("[")[-1].split("]")[0].split('", "')
    thesises_to_remove = defaultdict(set)
    for pair in predicted_outdated:
        splitted_pair = pair.split("<-")
        if len(splitted_pair) != 2:
            continue

        str_existing_thesis = splitted_pair[1].strip(''' \n'".,/''')
        str_new_thesis = splitted_pair[0].strip(''' \n'".,/''')
        thesises_to_remove[create_id(str_new_thesis)].add(create_id(str_existing_thesis))

    return thesises_to_remove
