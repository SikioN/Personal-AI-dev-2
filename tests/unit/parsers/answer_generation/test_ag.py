import sys
import pytest
from typing import List, Dict
from collections import defaultdict

# TO CHANGE
PROJECT_BASE_DIR = '../'
sys.path.insert(0, PROJECT_BASE_DIR)
from src.utils import Triplet
from src.pipelines.qa.kg_reasoning.weak_reasoner.answer_generator.agent_tasks.ag.general_parsers import ag_custom_formate, ag_custom_postprocess

from v1_tcases import AG_PARSE_V1_TEST_CASES
from v2_tcases import AG_PARSE_V2_TEST_CASES
from general_tcases import AG_FORMATE_TEST_CASES, AG_POSTPROCESS_TEST_CASES


AVAILABLE_AG_VERSIONS = {
    'v1': AG_PARSE_V1_TEST_CASES,
    'v2': AG_PARSE_V2_TEST_CASES
}

AG_AGGREGATED_PARSE_TEST_CASES = []
for v_key, v_tcases in AVAILABLE_AG_VERSIONS.items():
    for tcase in v_tcases:
        AG_AGGREGATED_PARSE_TEST_CASES.append(tcase + (v_key,))

@pytest.mark.parametrize("raw_response, lang, expected_output, exception, ag_tconfig", AG_AGGREGATED_PARSE_TEST_CASES, indirect=['ag_tconfig'])
def test_qa_parse(raw_response: str, lang: str, expected_output: Dict[str, str],
                  exception: bool, ag_tconfig: Dict[str, object]):
    try:
        parsed_output = ag_tconfig[lang].parse_answer_func(raw_response)
    except Exception:
        assert exception
    else:
        assert not exception

    if not exception:
        assert parsed_output == expected_output

@pytest.mark.parametrize("query, context_triplets, expected_output, exception", AG_FORMATE_TEST_CASES)
def test_qa_custom_formate(query: str, context_triplets: List[Triplet],
                           expected_output: Dict[str, str], exception: bool):
    try:
        formated_output = ag_custom_formate(query, context_triplets)
    except Exception:
        assert exception
    else:
        assert not exception

    if not exception:
        assert expected_output.keys() == formated_output.keys()
        for expected_key in expected_output.keys():
            assert expected_output[expected_key] == formated_output[expected_key]

@pytest.mark.parametrize("parsed_response, expected_output, exception", AG_POSTPROCESS_TEST_CASES)
def test_qa_postprocess(parsed_response: str, expected_output: str, exception: bool):
    try:
        real_answer = ag_custom_postprocess(parsed_response)
    except Exception:
        assert exception
    else:
        assert not exception

    if not exception:
        assert real_answer == expected_output
