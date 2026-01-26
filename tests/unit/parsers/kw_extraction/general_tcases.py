# "query, expected_output, exception"
KWE_FORMATE_TEST_CASE = [
    # непустая строка
    ("simple query", {'text': 'simple query'}, False),
    # пустая строка
    ("", None, True)
]

# "parsed_output, expected_output, exception"
KWE_POSTPROCESS_TEST_CASES = [
    # Пустой список
    ([], None, True),
    # Непустой список
    (['asd', 'zxc'], ['asd', 'zxc'], False)
]
