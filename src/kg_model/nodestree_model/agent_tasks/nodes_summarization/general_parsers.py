from typing import Dict

def summn_custom_formate(n_descendants: str, new_content: str,
                         current_content: str) -> Dict[str, str]:
    if len(new_content) < 1 or len(current_content) < 1:
        raise ValueError
    if int(n_descendants) < 0:
        raise ValueError

    return {'n_descendants': n_descendants, 'new_content': new_content,
            'current_content': current_content}

def summn_custom_postprocess(parsed_summary: str, **kwargs) -> str:
    if len(parsed_summary) < 1:
        raise ValueError
    return parsed_summary
