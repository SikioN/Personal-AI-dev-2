from typing import List, Dict

def casumm_custom_formate(search_query: str, clues_queries: List[str], clue_answers: List[str]) -> Dict[str, str]:
    if len(search_query) < 1 or len(clues_queries) < 1 or len(clue_answers) != len(clues_queries):
        raise ValueError
    
    search_info = '\n\n'.join(list(map(lambda pair: f'[Search Query]\n{pair[0]}\n[Finded Information]\n{pair[1]}', zip(clues_queries, clue_answers))))

    return {'query': search_query, 'search_info': search_info}

def casumm_custom_postprocess(parsed_response: str, **kwargs) -> List[str]:
    if len(parsed_response) < 1:
        raise ValueError

    return parsed_response