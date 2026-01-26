from typing import List, Tuple
import ast

def ethesises_custom_parse(raw_response: str, **kwargs) -> List[Tuple[str, List[str]]]:
    """Функция предназначена для разбора результата генерации ответа LLM-агента, в рамках задачи по извлечению
    триплетов типа "hyper" (тезисной информации) из текста на естественном языке.

    :param raw_response: Исходный ответ LLM-агента.
    :type raw_response: str
    :return: Разобранный список 'тезисных' триплетов из ответа LLM-агента.
    :rtype: List[Tuple[str, str]]
    """
    if len(raw_response) < 1:
        raise ValueError

    raw_thesises = []
    raw_response = raw_response.lower().split("\n")
    for raw_thesis in raw_response:
        if "|" not in raw_thesis:
            continue
            #raise ValueError

        raw_thesis, raw_entities = raw_thesis.split("|")
        thesis = raw_thesis.strip()

        try:
            entities = ast.literal_eval(raw_entities.strip(''' \n'".,;/'''))
        except SyntaxError as e:
            continue
            #raise ValueError

        raw_thesises.append((thesis, entities))

    return raw_thesises
