from typing import List

def entextr_custom_parse(raw_response: str, **kwargs) -> List[str]:
    # Пустой ответ
    raw_response = raw_response.strip(' .')
    if len(raw_response) < 1:
        raise ValueError

    extracted_entities = list(map(lambda item: item.strip(), raw_response.split('|')))
    filtered_entities = list(filter(lambda entitie: len(entitie) > 0, extracted_entities))

    return filtered_entities
