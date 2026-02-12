from typing import List, Tuple, Dict

from ......utils import NodeCreator, QuadrupletCreator, NodeType
from ......utils.data_structs import RelationType, Quadruplet, RelationCreator

def equadruplets_thesis_custom_formate(text: str, **kwargs) -> Dict[str, str]:
    if len(text) < 1:
        raise ValueError
    return {'text': text}

def equadruplets_thesis_custom_postprocess(parsed_response: List[Tuple[str, List[str]]], node_prop: Dict[str, object] = dict(),
                                 rel_prop: Dict[str, object] = dict(), **kwargs) -> List[Quadruplet]:
    formated_quadruplets = []
    
    # Handle time if passed in rel_prop or node_prop
    time_str = rel_prop.get('time', node_prop.get('time', "No time"))
    if time_str == "No time":
         time_node = None
    else:
         time_node = NodeCreator.create(NodeType.time, time_str, add_stringified_node=True)

    for quadruplet in parsed_response:
        thesis, entities = quadruplet

        if len(thesis) < 1:
            raise ValueError

        thesis_node = NodeCreator.create(name=str(thesis), n_type=NodeType.hyper, prop={**node_prop})
        thesis_rel = RelationCreator.create(name=RelationType.hyper.value, r_type=RelationType.hyper, prop={**rel_prop})
        for entity in entities:
            if len(entity) < 1:
                raise ValueError

            formated_quadruplets.append(QuadrupletCreator.create(
                start_node=NodeCreator.create(name=str(entity), n_type=NodeType.object),
                relation=thesis_rel, end_node=thesis_node,
                time=time_node))

    return formated_quadruplets
