from cases import VALID_SIMPLE_TRIPLET1, VALID_SIMPLE_TRIPLET2,\
      VALID_SIMPLE_TRIPLET7, VALID_SIMPLE_TRIPLET8

# "text, expected_output, exception"
ETRIPLETS_FORMATE_TEST_CASES = [
    # пустая строка
    ("", None, True),
    # непустая строка
    ("simple text", {'text': 'simple text'}, False)
]

# "parsed_response, rel_prop, node_prop, expected_output, exception"
ETRIPLETS_POSTPROCESS_TEST_CASES = [
    # пустой rel_prop
    ([('qwe', 'rfvbgt', 'asd')], dict(), {'k1': 'v1'}, [VALID_SIMPLE_TRIPLET8], False),
    # пустой node_prop
    ([('qazxsw', 'zxc', 'qazxsw')], {'k3': 'v3'}, dict(), [VALID_SIMPLE_TRIPLET7], False),
    # пустая subj-строка
    ([('', 'zxc', 'asd')], dict(), dict(), None, True),
    # пустая obj-строка
    ([('qwe', 'zxc', '')], dict(), dict(), None, True),
    # путся rel-строка
    ([('qwe', '', 'asd')], dict(), dict(), None, True),
    # несколько валидных триплетов
    ([('qwe', 'zxc', 'asd'), ('asd', 'zxc', 'uio')], {'k3': 'v3'}, {'k1': 'v1'},
     [VALID_SIMPLE_TRIPLET1, VALID_SIMPLE_TRIPLET2], False)
]
