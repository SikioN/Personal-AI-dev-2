from typing import List, Tuple, Dict, Union

from ......utils import NodeCreator, QuadrupletCreator, NodeType
from ......utils.data_structs import RelationType, Quadruplet, RelationCreator

def equadruplets_custom_formate(text: str, **kwargs) -> Dict[str, str]:
    if len(text) < 1:
        raise ValueError

    return {'text': text}

def equadruplets_custom_postprocess(parsed_response: List[Tuple[str, str, str]],  node_prop: Dict[str, object] = dict(),
                                 rel_prop: Dict[str, object] = dict(), **kwargs) -> List[Quadruplet]:
    formated_quadruplets = []
    
    # Check if time is provided in kwargs, else None (checks for "No time" are done at creator level if needed, or we pass valid Node)
    # LLMExtractor passes 'time' in extraction logic, but here it comes via kwargs?
    # We need to ensure 'time' is passed down if available.
    # LLMExtractor calling: solve(..., rel_prop=props). 'props' takes 'time' key!
    # So 'time' might be in rel_prop or kwargs.
    # In LLMExtractor: props['time'] = time.
    # solve passes rel_prop=props.
    # So rel_prop has 'time'.
    
    time_str = rel_prop.get('time', "No time")
    if time_str == "No time":
         time_node = None
    else:
         time_node = NodeCreator.create(NodeType.time, time_str, add_stringified_node=True)

    for quadruplet in parsed_response:
        subj, rel, obj = quadruplet

        if len(subj) < 1 or len(rel) < 1 or len(obj) < 1:
            raise ValueError

        formated_quadruplets.append(QuadrupletCreator.create(
            start_node=NodeCreator.create(name=subj, n_type=NodeType.object, prop={**node_prop}),
            relation=RelationCreator.create(name=rel, r_type=RelationType.simple, prop={**rel_prop}),
            end_node=NodeCreator.create(name=obj, n_type=NodeType.object, prop={**node_prop}),
            time=time_node
            ))

    return formated_quadruplets
