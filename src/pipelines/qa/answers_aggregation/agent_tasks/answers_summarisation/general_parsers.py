from typing import List

def subasumm_custom_formate(query: str, sub_queries: List[str], sub_answers: List[str]) -> str:
    if len(query) < 1 or len(sub_queries) < 2 or len(sub_answers) != len(sub_queries):
        raise ValueError
    
    search_info = '\n\n'.join(list(map(lambda pair: f'[Search Query]\n{pair[0]}\n[Finded Information]\n{pair[1]}', zip(sub_queries, sub_answers))))

    return {'query': query, 'search_info': search_info}

def subasumm_custom_postprocess(parsed_response: List[str], **kwargs) -> List[str]:
    if len(parsed_response) < 1:
        raise ValueError

    return parsed_response