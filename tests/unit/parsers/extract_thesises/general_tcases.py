from cases import VALID_HYPER_TRIPLET1, VALID_HYPER_TRIPLET1_2,\
      VALID_HYPER_TRIPLET7, VALID_HYPER_TRIPLET8

# "text, expected_output, exception"
ETHESISES_FORMATE_TEST_CASES = [
    # пустая строка
    ("", None, True),
    # непустая строка
    ("simple text", {'text': 'simple text'}, False)
]

# "parsed_response, rel_prop, node_prop, expected_output, exception"
ETHESISES_POSTPROCESS_TEST_CASES = [
    # пустой rel_prop
    ([('rty',['qwe'])], dict(), {'k1': 'v1'}, [VALID_HYPER_TRIPLET7], False),
    # пустой node_prop
    ([('qsdcb',['qazxsw'])], {'k5': 'v5'}, dict(), [VALID_HYPER_TRIPLET8], False),
    # пустая thesis-строка
    ([('',['qwe', 'asd'])], dict(), dict(), None, True),
    # пустая entity-строка
    ([('rty',['', 'asd'])], dict(), dict(), None, True),
    # несколько валидных тезисов
    ([('rty',['qwe', 'asd'])], {'k5': 'v5'}, {'k1': 'v1'}, [VALID_HYPER_TRIPLET1, VALID_HYPER_TRIPLET1_2], False)
]
