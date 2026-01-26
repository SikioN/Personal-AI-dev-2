GOOD_RESPONSE1 = 'a | b | c;\nd | e | f.'
GOOD_RESPONSE2 = 'a | b | c.'
BAD_RESPONSE1 = 'a b c;\nd e f.'
BAD_RESPONSE2 = 'a | b | c\n d | e | f.'

ETRIPLETS_PARSE_V2_TEST_CASES = [
    # пустая строка
    ("", 'en', None, True),
    # валидный формат (один триплет)
    (GOOD_RESPONSE2, 'en', [('a','b','c')], False),
    # валидный формат (несколько триплетов)
    (GOOD_RESPONSE1, 'en', [('a','b','c'), ('d','e','f')], False),
    # невалидный формат (|)
    (BAD_RESPONSE1, 'en', None, True),
    # невалидный формат (;)
    (BAD_RESPONSE2, 'en', None, True)
]
