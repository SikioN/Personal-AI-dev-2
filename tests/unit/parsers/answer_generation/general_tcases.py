import sys
# TO CHANGE
PROJECT_BASE_DIR = '../'
sys.path.insert(0, PROJECT_BASE_DIR)
from src.utils import TripletCreator

from cases import VALID_SIMPLE_TRIPLET1, VALID_HYPER_TRIPLET1

AG_ONE_CONTEXT = f'- {TripletCreator.stringify(VALID_SIMPLE_TRIPLET1)[1]}'
AG_SEVERAL_CONTEXTS = '\n'.join(list(map(lambda triplet: f'- {TripletCreator.stringify(triplet)[1]}', [VALID_SIMPLE_TRIPLET1, VALID_HYPER_TRIPLET1])))

# "query, context_triplets, expected_output, exception"
AG_FORMATE_TEST_CASES = [
    # пустая query-строка
    ('', [VALID_SIMPLE_TRIPLET1, VALID_HYPER_TRIPLET1], None, True),
    # путой context_triplet-список
    ('simple query', [], {'q': 'simple query', 'c': 'Empty'}, False),
    # один элемент в context_triplets-списке
    ('simple query', [VALID_SIMPLE_TRIPLET1],
     {'q': 'simple query', 'c': AG_ONE_CONTEXT}, False),
    # несколько элементов в context_triplets-списке
    ('simple query', [VALID_SIMPLE_TRIPLET1, VALID_HYPER_TRIPLET1],
     {'q': 'simple query', 'c': AG_SEVERAL_CONTEXTS}, False)
]

# "parsed_response, lang, expected_output, exception"
AG_POSTPROCESS_TEST_CASES = [
    # пустая строка
    ("", None, True),
    # непустая строка
    ("simple answer", "simple answer", False),
]
