GOOD_RESPONSE1 = "a | ['b', 'c']."
GOOD_RESPONSE2 = "a | ['b', 'c'];\nd | ['e', 'f']."
BAD_RESPONSE1 = "a ['b', 'c'];\nd ['e', 'f']."
BAD_RESPONSE2 = "a | ['b' 'c'];\nd | ['e' 'f']."
BAD_RESPONSE3 = "a | 'b', 'c';\nd | 'e', 'f'."
BAD_RESPONSE4 = "a | [b, c];\nd | [e, f]."

# raw_response, lang, expected_output, exception
ETHESISES_PARSE_V2_TEST_CASES = [
    # пустая строка
    ("", 'en', None, True),
    # валидный формат (один триплет)
    (GOOD_RESPONSE1, 'en', [('a', ['b','c'])], False),
    # валидный формат (несколько триплетов)
    (GOOD_RESPONSE2, 'en', [('a',['b','c']), ('d',['e','f'])], False),
    # невалидный формат (|)
    (BAD_RESPONSE1, 'en', None, True),
    # невалидный формат (,)
    (BAD_RESPONSE2, 'en', None, True),
    # невалидный формат (скобки)
    (BAD_RESPONSE3, 'en', None, True),
    # невалидный формат (кавычки)
    (BAD_RESPONSE4, 'en', None, True)
]
