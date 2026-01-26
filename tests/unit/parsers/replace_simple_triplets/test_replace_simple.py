import pytest
from typing import Dict, Set, List

import sys
sys.path.insert(0, "../")
from src.utils import Triplet

from src.pipelines.memorize.updator.agent_tasks.replace_simple_triplets.general_parsers import rs_custom_formate, rs_custom_postprocess
from general_tcases import REPLACESIMPLE_FORMATE_TEST_CASE, REPLACESIMPLE_POSTPROCESS_TEST_CASE
from v1_tcases import RSIMPLE_PARSE_V1_TEST_CASES

AVAILABLE_RSIMPLE_VERSIONS = {
    'v1': RSIMPLE_PARSE_V1_TEST_CASES,
}

RSIMPLE_AGGREGATED_PARSE_TEST_CASES = []
for v_key, v_tcases in AVAILABLE_RSIMPLE_VERSIONS.items():
    for tcase in v_tcases:
        RSIMPLE_AGGREGATED_PARSE_TEST_CASES.append(tcase + (v_key,))

@pytest.mark.parametrize("raw_response, lang, expected_output, exception, rsimple_tconfig",
                         RSIMPLE_AGGREGATED_PARSE_TEST_CASES, indirect=['rsimple_tconfig'])
def test_custom_parse(raw_response: str, lang: str, expected_output: Dict[str, Set[str]],
                      exception: bool, rsimple_tconfig: Dict[str, object]):
    try:
        real_output = rsimple_tconfig[lang].parse_answer_func(raw_response)
    except Exception:
        assert exception
    else:
        assert not exception

    if not exception:
        assert expected_output.keys() == real_output.keys()
        for expected_key in expected_output.keys():
            assert expected_output[expected_key] == real_output[expected_key]

@pytest.mark.parametrize("base_triplet, incident_triplets, expected_output, exception", REPLACESIMPLE_FORMATE_TEST_CASE)
def test_custom_foramte(base_triplet: Triplet, incident_triplets: List[Triplet],
                        expected_output: Dict[str, str], exception: bool):
    try:
        real_output = rs_custom_formate(base_triplet, incident_triplets)
    except Exception:
        assert exception
    else:
        assert not exception

    if not exception:
        assert expected_output.keys() == real_output.keys()
        for expected_key in expected_output.keys():
            assert expected_output[expected_key] == real_output[expected_key]

@pytest.mark.parametrize("parsed_response, base_triplet, incident_triplets, expected_output, exception", REPLACESIMPLE_POSTPROCESS_TEST_CASE)
def test_custom_postprocess(parsed_response: Dict[str, Set[str]], base_triplet: Triplet,
                            incident_triplets: List[Triplet], expected_output: List[str], exception: bool):
    try:
        real_output = rs_custom_postprocess(
            parsed_response, base_triplet, incident_triplets)
    except Exception:
        assert exception
    else:
        assert not exception

    if not exception:
        assert expected_output == real_output
