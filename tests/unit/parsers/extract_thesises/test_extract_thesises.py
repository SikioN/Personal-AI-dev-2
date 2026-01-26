import pytest
from typing import Dict, List, Set, Tuple

import sys
sys.path.insert(0, "../")
from src.utils.data_structs import Triplet
from src.pipelines.memorize.extractor.agent_tasks.thesis_extraction.general_parsers import \
    ethesises_custom_formate, ethesises_custom_postprocess

from v1_tcases import ETHESISES_PARSE_V1_TEST_CASES
from v2_tcases import ETHESISES_PARSE_V2_TEST_CASES
from general_tcases import ETHESISES_FORMATE_TEST_CASES, ETHESISES_POSTPROCESS_TEST_CASES

AVAILABLE_ETHESISES_VERSIONS = {
    'v1': ETHESISES_PARSE_V1_TEST_CASES,
    'v2': ETHESISES_PARSE_V2_TEST_CASES
}

ETHESISES_AGGREGATED_PARSE_TEST_CASES = []
for v_key, v_tcases in AVAILABLE_ETHESISES_VERSIONS.items():
    for tcase in v_tcases:
        ETHESISES_AGGREGATED_PARSE_TEST_CASES.append(tcase + (v_key,))

@pytest.mark.parametrize("raw_response, lang, expected_output, exception, ethesises_tconfig", ETHESISES_AGGREGATED_PARSE_TEST_CASES, indirect=['ethesises_tconfig'])
def test_custom_parse(raw_response: str, lang: str, expected_output: List[Tuple[str, str, str]],
                      exception: bool, ethesises_tconfig: Dict[str, object]):
    try:
        parsed_output = ethesises_tconfig[lang].parse_answer_func(raw_response)
    except Exception:
        assert exception
    else:
        assert not exception

    if not exception:
        assert expected_output == parsed_output

@pytest.mark.parametrize("text, expected_output, exception",  ETHESISES_FORMATE_TEST_CASES)
def test_custom_foramte(text: str, expected_output: Dict[str, str], exception: bool):
    try:
        formated_output = ethesises_custom_formate(text)
    except Exception:
        assert exception
    else:
        assert not exception

    if not exception:
        assert expected_output.keys() == formated_output.keys()
        for expected_key in expected_output.keys():
            assert expected_output[expected_key] == formated_output[expected_key]

# !!! TO ANALYZE TEST #0 AND #4 CASES !!!
@pytest.mark.parametrize("parsed_response, rel_prop, node_prop, expected_output, exception", ETHESISES_POSTPROCESS_TEST_CASES)
def test_custom_postprocess(parsed_response: List[Tuple[str, str, str]], rel_prop: Dict[str, object],
                            node_prop: Dict[str, object], expected_output: List[Triplet], exception: bool):
    try:
        triplets = ethesises_custom_postprocess(parsed_response, node_prop, rel_prop)
    except Exception:
        assert exception
    else:
        assert not exception

    if not exception:
        for t1, t2 in zip(triplets, expected_output):
            print(t1.id, t2.id)
            print(t1.start_node.id, t2.start_node.id)
            print(t1.relation.id, t2.relation.id)
            print(t1.end_node.id, t2.end_node.id)

            print(t1)
            print(t2)

        assert expected_output == triplets
