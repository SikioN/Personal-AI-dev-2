from typing import List, Tuple

def etriplets_custom_parse(raw_response: str, **kwargs) -> List[Tuple[str, str, str]]:
    """Функция предназначена для разбора ответа LLM-агента, полученного в рамках задачи по извлечению триплетов типа "simple" из текста на естественном языке.

    :param raw_response: Исходный ответ LLM-агента.
    :type raw_response: str
    :return: Разобранный список триплетов из ответа LLM-агента.
    :rtype: List[Tuple[str, str, str]]
    """
    if len(raw_response) < 1:
        raise ValueError

    raw_response = raw_response.lower().split("\n")
    raw_triplets = []
    for triplet in raw_response:
        if len(triplet.split("|")) != 3:
            continue
            #raise ValueError
        subj, rel, obj = triplet.split("|")
        subj, rel, obj = subj.strip(''' \n'".,/\\'''), rel.strip(''' \n'".,/\\'''), obj.strip(''' \n'".;,/\\''')
        if len(subj) == 0 or len(rel) == 0 or len(obj) == 0:
            raise ValueError
        else:
            raw_triplets.append((subj, rel, obj))

    return raw_triplets
