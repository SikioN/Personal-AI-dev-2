from typing import List, Tuple, Dict

from ......utils import NodeCreator, TripletCreator, NodeType
from ......utils.data_structs import RelationType, Triplet, RelationCreator

def ethesises_custom_formate(text: str, **kwargs) -> Dict[str, str]:
    if len(text) < 1:
        raise ValueError
    return {'text': text}

def ethesises_custom_postprocess(parsed_response: List[Tuple[str, List[str]]], node_prop: Dict[str, object] = dict(),
                                 rel_prop: Dict[str, object] = dict(), **kwargs) -> List[Triplet]:
    formated_triplets = []
    for triplet in parsed_response:
        thesis, entities = triplet

        if len(thesis) < 1:
            raise ValueError

        thesis_node = NodeCreator.create(name=str(thesis), n_type=NodeType.hyper, prop={**node_prop})
        thesis_rel = RelationCreator.create(name=RelationType.hyper.value, r_type=RelationType.hyper, prop={**rel_prop})
        for entity in entities:
            if len(entity) < 1:
                raise ValueError

            formated_triplets.append(TripletCreator.create(
                start_node=NodeCreator.create(name=str(entity), n_type=NodeType.object),
                relation=thesis_rel, end_node=thesis_node))

    return formated_triplets
