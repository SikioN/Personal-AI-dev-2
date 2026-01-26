EN_GOOD_RESPONSE1 = 'Chain of thought 3: bla bla bla\nFinal answer 3: simple answer'
EN_BAD_RESPONSE1 = 'Chain of thought 3: bla bla bla\nFinal answer 3: '
EN_BAD_RESPONSE2 = 'Chain of thought 3: bla bla bla\nFInaL aNsWer: simple answer'

# "raw_response, lang, expected_output, exception"
AG_PARSE_V1_TEST_CASES = [
    # пустая строка
    ('', 'en', None, True),
    # валидный формат + есть ответ\
    (EN_GOOD_RESPONSE1, 'en', 'simple answer', False),
    # валидный формат + пустой ответ
    (EN_BAD_RESPONSE1, 'en', None, True),
    # изменённый регистр формата
    (EN_BAD_RESPONSE2, 'en', 'simple answer', False)
]
