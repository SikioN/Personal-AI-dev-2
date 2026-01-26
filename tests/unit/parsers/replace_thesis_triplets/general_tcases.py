from cases import VALID_HYPER_TRIPLET4, VALID_HYPER_TRIPLET5, VALID_HYPER_TRIPLET6
from cases import VALID_HYPER_TRIPLET1, VALID_HYPER_TRIPLET2, VALID_HYPER_TRIPLET3,\
      REPLACE_THESISES_2AND3, REPLACE_THESISES_1, REPLACE_THESISES_2, REPLACE_THESISES_PARSE_OUTPUT2

# "base_triplet, incident_triplets, expected_output, exception"
REPLACETHESIS_FORMATE_TEST_CASE = [
    # 1. корректные base_triplet и incident_triplets (несколько)
    (VALID_HYPER_TRIPLET1, [VALID_HYPER_TRIPLET2, VALID_HYPER_TRIPLET3],
     {'ex_thesises': REPLACE_THESISES_2AND3, 'new_thesises': REPLACE_THESISES_1}, False),
    # 2. корректные base_triplet и incident_triplets (один)
    (VALID_HYPER_TRIPLET1, [VALID_HYPER_TRIPLET2],
     {'ex_thesises': REPLACE_THESISES_2, 'new_thesises': REPLACE_THESISES_1}, False),
    # 3. корректный base_triplet и  пустой incident_triplets
    (VALID_HYPER_TRIPLET1, [], None, True),
]

# ""parsed_response, base_triplet, incident_triplets, expected_output, exception"
REPLACETHESIS_POSTPROCESS_TEST_CASE = [
    # 1. разобранный new-triplet = base_triplet и разобранные existing-triplets содержатся в incident_triplets
    (REPLACE_THESISES_PARSE_OUTPUT2, VALID_HYPER_TRIPLET4, [VALID_HYPER_TRIPLET5, VALID_HYPER_TRIPLET6],
      [VALID_HYPER_TRIPLET5.id, VALID_HYPER_TRIPLET6.id], False),
    # 2. разобранный new-triplet != base_triplet
    (REPLACE_THESISES_PARSE_OUTPUT2, VALID_HYPER_TRIPLET5, [VALID_HYPER_TRIPLET6],
     [], False),
    # 3. разобранный new-triplet = base_triplet, но часть разобранных existing-triplets не содержится в incident_triplets
    (REPLACE_THESISES_PARSE_OUTPUT2, VALID_HYPER_TRIPLET4, [VALID_HYPER_TRIPLET5],
     [VALID_HYPER_TRIPLET5.id], False)
]
