from cases import REPLACE_SIMPLE_RAW_RESPONSE1, REPLACE_SIMPLE_RAW_RESPONSE2,\
      REPLACE_SIMPLE_RAW_RESPONSE3, REPLACE_SIMPLE_RAW_RESPONSE4,\
          REPLACE_SIMPLE_RAW_RESPONSE5, REPLACE_SIMPLE_RAW_RESPONSE6,\
          REPLACE_SIMPLE_RAW_RESPONSE7, REPLACE_SIMPLE_RAW_RESPONSE8,\
          REPLACE_SIMPLE_PARSE_OUTPUT1, REPLACE_SIMPLE_PARSE_OUTPUT2

# "raw_response, lang, expected_output, exception"
RSIMPLE_PARSE_V1_TEST_CASES = [
    # 1. один сопоставленный тезис
    (REPLACE_SIMPLE_RAW_RESPONSE1, 'en', REPLACE_SIMPLE_PARSE_OUTPUT1, False),
    # 2. несколько сопоставленных тезисов
    (REPLACE_SIMPLE_RAW_RESPONSE2, 'en', REPLACE_SIMPLE_PARSE_OUTPUT2, False),
    # 3. сопоставленные тезисы отсутствуют
    ("[]", 'en', dict(), False),
    # 4. невалидный response
    # 4.1. отсутствует стрелка
    (REPLACE_SIMPLE_RAW_RESPONSE3, 'en', None, True),
    # 4.2 отсутствуют скобки
    (REPLACE_SIMPLE_RAW_RESPONSE4, 'en', None, True),
    # 4.3 отсутствуют кавычки
    (REPLACE_SIMPLE_RAW_RESPONSE5, 'en', None, True),
    # 4.4 присутствуте специальный символ в тезисе
    # 4.4.1 стрелка
    (REPLACE_SIMPLE_RAW_RESPONSE6, 'en', None, True),
    # 4.4.2 скобки
    (REPLACE_SIMPLE_RAW_RESPONSE7, 'en', None, True),
    # 4.4.3 кавычки
    (REPLACE_SIMPLE_RAW_RESPONSE8, 'en', None, True)
]
