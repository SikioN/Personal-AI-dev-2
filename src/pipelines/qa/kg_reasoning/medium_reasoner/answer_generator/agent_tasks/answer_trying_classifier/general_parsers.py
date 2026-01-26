from typing import List, Dict

from ....utils import SearchPlanInfo

def answcls_custom_formate(search_plan: SearchPlanInfo) -> Dict[str, str]:
    search_info = '\n\n'.join(list(map(lambda i: f'[Search Query #{i}]\n{search_plan.search_steps[i]}\n[Finded Information]\n{search_plan.steps_answers[i]}', range(len(search_plan.steps_answers)))))

    return {'query': search_plan.base_query, 'search_info': search_info}

def answcls_custom_postprocess(parsed_response: str, **kwargs) -> bool:
    if len(parsed_response) < 1:
        raise ValueError
    
    if parsed_response.startswith("Yes"):
        cananswer_sign = True
    if parsed_response.startswith("No"):
         cananswer_sign = False
    else:
        raise ValueError   

    return cananswer_sign