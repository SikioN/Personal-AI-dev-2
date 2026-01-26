import pytest
from typing import Dict, List, Tuple

import sys
sys.path.insert(0, "../")
from src.utils import Triplet

from src.pipelines.memorize.extractor.agent_tasks.triplet_extraction.general_parsers import etriplets_custom_formate, etriplets_custom_postprocess

from v1_tcases import ETRIPLETS_PARSE_V1_TEST_CASES
from v2_tcases import ETRIPLETS_PARSE_V2_TEST_CASES
from general_tcases import ETRIPLETS_FORMATE_TEST_CASES, ETRIPLETS_POSTPROCESS_TEST_CASES

AVAILABLE_ETRIPLETS_VERSIONS = {
    'v1': ETRIPLETS_PARSE_V1_TEST_CASES,
    'v2': ETRIPLETS_PARSE_V2_TEST_CASES
}

ETRIPLETS_AGGREGATED_PARSE_TEST_CASES = []
for v_key, v_tcases in AVAILABLE_ETRIPLETS_VERSIONS.items():
    for tcase in v_tcases:
        ETRIPLETS_AGGREGATED_PARSE_TEST_CASES.append(tcase + (v_key,))

@pytest.mark.parametrize("raw_response, lang, expected_output, exception, etriplets_tconfig",
                         ETRIPLETS_AGGREGATED_PARSE_TEST_CASES, indirect=['etriplets_tconfig'])
def test_custom_parse(raw_response: str, lang: str, expected_output: List[Tuple[str, str, str]],
                      exception: bool, etriplets_tconfig):
    try:
        parsed_output = etriplets_tconfig[lang].parse_answer_func(raw_response)
    except Exception:
        assert exception
    else:
        assert not exception

    if not exception:
        assert expected_output == parsed_output

@pytest.mark.parametrize("text, expected_output, exception", ETRIPLETS_FORMATE_TEST_CASES)
def test_custom_formate(text: str, expected_output: Dict[str, str], exception: bool):
    try:
        formated_output = etriplets_custom_formate(text)
    except Exception:
        assert exception
    else:
        assert not exception

    if not exception:
        assert expected_output.keys() == formated_output.keys()
        for expected_key in expected_output.keys():
            assert expected_output[expected_key] == formated_output[expected_key]



@pytest.mark.parametrize("parsed_response, rel_prop, node_prop, expected_output, exception", ETRIPLETS_POSTPROCESS_TEST_CASES)
def test_custom_postprocess(parsed_response: List[Tuple[str, str, str]], rel_prop: Dict[str, object],
                            node_prop: Dict[str, object], expected_output: List[Triplet], exception: bool):
    try:
        triplets = etriplets_custom_postprocess(parsed_response, node_prop, rel_prop)
    except Exception:
        assert exception
    else:
        assert not exception

    if not exception:
        assert expected_output == triplets
