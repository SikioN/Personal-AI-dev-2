from typing import List, Dict

def enhcls_custom_formate(query: str, search_steps: List[str], steps_answers: List[str]) -> Dict[str, str]:
    if len(query) < 1 or len(search_steps) < 1 or len(steps_answers) > len(search_steps):
        raise ValueError
    
    complited_squeries = '\n\n'.join([f"Search Query: {cs_step}\nFinded information:\n{answ_step}" for cs_step, answ_step in zip(search_steps, steps_answers)])
    next_squeries = search_steps[len(steps_answers):]
    next_squeries = '\n'.join(list(map(lambda pair: f'{pair[0]}. {pair[1]}', enumerate(next_squeries)))) if len(next_squeries) else "Existing search-plan is complited. Next search-steps need to be planned." 

    return {'query': query, 'complited_squeries': complited_squeries, 'next_squeries': next_squeries}

def enhcls_custom_postprocess(parsed_response: str, **kwargs) -> bool:
    if len(parsed_response) < 1:
        raise ValueError
    
    if parsed_response.startswith("Yes"):
        needenhance_sign = True
    elif parsed_response.startswith("No"):
        needenhance_sign = False
    else:
        raise ValueError   

    return needenhance_sign