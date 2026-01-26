from cases import VALID_SIMPLE_TRIPLET1, VALID_SIMPLE_TRIPLET2, VALID_SIMPLE_TRIPLET3,\
      REPLACE_SIMPLE_2AND3, REPLACE_SIMPLE_1, REPLACE_SIMPLE_2, VALID_SIMPLE_TRIPLET4,\
          VALID_SIMPLE_TRIPLET5, VALID_SIMPLE_TRIPLET6, REPLACE_SIMPLE_PARSE_OUTPUT2

# "base_triplet, incident_triplets, expected_output, exception"
REPLACESIMPLE_FORMATE_TEST_CASE = [
    # 1. корректные base_triplet и incident_triplets (несколько)
    (VALID_SIMPLE_TRIPLET1, [VALID_SIMPLE_TRIPLET2, VALID_SIMPLE_TRIPLET3],
     {'ex_triplets': REPLACE_SIMPLE_2AND3, 'new_triplets': REPLACE_SIMPLE_1}, False),
    # 2. корректные base_triplet и incident_triplets (один)
    (VALID_SIMPLE_TRIPLET1, [VALID_SIMPLE_TRIPLET2],
     {'ex_triplets': REPLACE_SIMPLE_2, 'new_triplets': REPLACE_SIMPLE_1}, False),
    # 3. корректный base_triplet и  пустой incident_triplets
    (VALID_SIMPLE_TRIPLET1, [], None, True)
]

# "parsed_response, base_triplet, incident_triplets, expected_output, exception"
REPLACESIMPLE_POSTPROCESS_TEST_CASE = [
    # 1. разобранный new-triplet = base_triplet и разобранные existing-triplets содержатся в incident_triplets
    (REPLACE_SIMPLE_PARSE_OUTPUT2, VALID_SIMPLE_TRIPLET4, [VALID_SIMPLE_TRIPLET5, VALID_SIMPLE_TRIPLET6],
      [VALID_SIMPLE_TRIPLET5.id, VALID_SIMPLE_TRIPLET6.id], False),
    # 2. разобранный new-triplet != base_triplet
    (REPLACE_SIMPLE_PARSE_OUTPUT2, VALID_SIMPLE_TRIPLET5, [VALID_SIMPLE_TRIPLET6],
     [], False),
    # 3. разобранный new-triplet = base_triplet, но часть разобранных existing-triplets не содержится в incident_triplets
    (REPLACE_SIMPLE_PARSE_OUTPUT2, VALID_SIMPLE_TRIPLET4, [VALID_SIMPLE_TRIPLET5],
     [VALID_SIMPLE_TRIPLET5.id], False)
]
