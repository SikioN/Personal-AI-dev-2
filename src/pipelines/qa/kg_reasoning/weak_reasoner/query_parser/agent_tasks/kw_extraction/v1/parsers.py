from typing import List

def kwe_custom_parse(raw_response: str, **kwargs) -> List[str]:
    """Функция предназначена для разбора ответа от LLM-агента, в рамках задачи по извлечению ключевых сущностей из текста на естественном языке.

    :param raw_response: Исходный ответ LLM-агента.
    :type raw_response: str
    :return: Разобранный список ключевых сущностей из ответа LLM-агента.
    :rtype: List[str]
    """
    raw_response = raw_response.strip(' .')
    if len(raw_response) < 1:
        raise ValueError

    entities = list(filter(lambda item: len(item) > 0, list(map(lambda item: item.strip(), raw_response.split('|')))))
    return entities
