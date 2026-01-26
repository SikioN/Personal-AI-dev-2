EN_GOOD_RESPONSE1 = '[Chain of thoughts]: bla bla bla\n[Answer]: simple answer'
EN_BAD_RESPONSE1 = '[Chain of thoughts]: bla bla bla\n[Answer]: '
EN_BAD_RESPONSE2 = '[Chain of thoughts]: bla bla bla\n[answer]: simple answer'

# "raw_response, lang, expected_output, exception"
AG_PARSE_V2_TEST_CASES = [
    # пустая строка
    ('', 'en', None, True),
    # валидный формат + есть ответ\
    (EN_GOOD_RESPONSE1, 'en', 'simple answer', False),
    # валидный формат + пустой ответ
    (EN_BAD_RESPONSE1, 'en', None, True),
    # изменённый регистр формата
    (EN_BAD_RESPONSE2, 'en', 'simple answer', False)
]
