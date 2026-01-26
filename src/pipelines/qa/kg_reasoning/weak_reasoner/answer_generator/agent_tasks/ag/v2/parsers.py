import re

def en_simpleag_custom_parse(raw_response: str, **kwargs) -> str:
    """Функция предназначена для разбора ответа LLM-агента, полученного в рамках условной QA-задачи на английском языке.

    :param raw_response: Исходный ответ LLM-агента.
    :type raw_response: str
    :return: Разобранный ответ на user-вопрос от LLM-агента.
    :rtype: str
    """

    if len(raw_response) < 1:
        raise ValueError

    answer_pos = re.search(r"\[answer\]", raw_response, re.IGNORECASE)

    # Ответ не соответствует формату
    if answer_pos is None:
        raise ValueError

    answer = raw_response[answer_pos.span(0)[1]:]

    # Пустой ответ
    if len(answer) < 1:
        raise ValueError

    return answer

def ru_simpleag_custom_parse(raw_response: str, **kwargs) -> str:
    """Функция предназначена для разбора ответа LLM-агента, полученного в рамках условной QA-задачи на русском языке.

    :param raw_response: Исходный ответ LLM-агента.
    :type raw_response: str
    :return: Разобранный ответ на user-вопрос от LLM-агента.
    :rtype: str
    """
    if len(raw_response) < 1:
        raise ValueError

    answer_pos = re.search(r"\[ответ\]: ", raw_response, re.IGNORECASE)

    # Ответ не соответствует формату
    if answer_pos is None:
        raise ValueError

    answer = raw_response[answer_pos.span(0)[0]:]

    # Пустой ответ
    if len(answer) < 1:
        raise ValueError

    return answer
