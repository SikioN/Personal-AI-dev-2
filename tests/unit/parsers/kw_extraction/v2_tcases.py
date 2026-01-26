KWE_PARSE_V2_TEST_CASES = [
    # пустая строк
    ('', 'en', [], True),
    # одна сущность
    ('asd', 'en', ['asd'], False),
    # несколько сущностей
    ('asd | qwe | zxc', 'en', ['asd', 'qwe', 'zxc'], False)
]
