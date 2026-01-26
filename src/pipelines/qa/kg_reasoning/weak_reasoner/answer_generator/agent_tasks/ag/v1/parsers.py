def en_simpleag_custom_parse(raw_response: str, **kwargs) -> str:
    """Функция предназначена для разбора ответа LLM-агента, полученного в рамках условной QA-задачи на английском языке.

    :param raw_response: Исходный ответ LLM-агента.
    :type raw_response: str
    :return: Разобранный ответ на user-вопрос от LLM-агента.
    :rtype: str
    """

    if len(raw_response) < 1:
        raise ValueError

    found_line = ""
    for line in raw_response.strip().split("\n"):
        if "Final answer 3" in line:
            found_line = line
            break
    if found_line:
        answer = found_line.split("Final answer 3:")[-1].strip()
    else:
        answer = raw_response.strip()

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

    answer = raw_response.strip()

    if len(answer) < 1:
        raise ValueError

    return answer
