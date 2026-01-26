from typing import List, Tuple, Dict

from ......utils import NodeCreator, TripletCreator, NodeType
from ......utils.data_structs import RelationType, Triplet, RelationCreator

def etriplets_custom_formate(text: str, **kwargs) -> Dict[str, str]:
    if len(text) < 1:
        raise ValueError

    return {'text': text}

def etriplets_custom_postprocess(parsed_response: List[Tuple[str, str, str]],  node_prop: Dict[str, object] = dict(),
                                 rel_prop: Dict[str, object] = dict(), **kwargs) -> List[Triplet]:
    formated_triplets = []
    for triplet in parsed_response:
        subj, rel, obj = triplet

        if len(subj) < 1 or len(rel) < 1 or len(obj) < 1:
            raise ValueError

        formated_triplets.append(TripletCreator.create(
            start_node=NodeCreator.create(name=subj, n_type=NodeType.object, prop={**node_prop}),
            relation=RelationCreator.create(name=rel, r_type=RelationType.simple, prop={**rel_prop}),
            end_node=NodeCreator.create(name=obj, n_type=NodeType.object, prop={**node_prop})))

    return formated_triplets
