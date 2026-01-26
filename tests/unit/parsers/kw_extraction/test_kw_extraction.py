import pytest
from typing import Dict, List

import sys
sys.path.insert(0, "../")

from src.pipelines.qa.kg_reasoning.weak_reasoner.query_parser.agent_tasks.kw_extraction.general_parsers import kwe_custom_formate, kwe_custom_postprocess
from general_tcases import KWE_FORMATE_TEST_CASE, KWE_POSTPROCESS_TEST_CASES

from v1_tcases import KWE_PARSE_V1_TEST_CASES
from v2_tcases import KWE_PARSE_V2_TEST_CASES

AVAILABLE_KWE_VERSIONS = {
    'v1': KWE_PARSE_V1_TEST_CASES,
    'v2': KWE_PARSE_V2_TEST_CASES
}

KWE_AGGREGATED_PARSE_TEST_CASES = []
for v_key, v_tcases in AVAILABLE_KWE_VERSIONS.items():
    for tcase in v_tcases:
        KWE_AGGREGATED_PARSE_TEST_CASES.append(tcase + (v_key,))

@pytest.mark.parametrize("raw_response, lang, expected_output, exception, kwe_tconfig",
                         KWE_AGGREGATED_PARSE_TEST_CASES, indirect=['kwe_tconfig'])
def test_kw_parse(raw_response: str, lang: str, expected_output: List[str], exception: bool, kwe_tconfig: Dict[str, object]):
    try:
         parsed_output = kwe_tconfig[lang].parse_answer_func(raw_response)
    except Exception:
        assert exception
    else:
        assert not exception

    if not exception:
        assert expected_output == parsed_output

@pytest.mark.parametrize("query, expected_output, exception", KWE_FORMATE_TEST_CASE)
def test_custom_formate(query: str, expected_output: Dict[str, str], exception: bool):
    try:
         formated_output = kwe_custom_formate(query)
    except Exception:
        assert exception
    else:
        assert not exception

    if not exception:
        assert expected_output.keys() == formated_output.keys()
        for expected_key in expected_output.keys():
            assert expected_output[expected_key] == formated_output[expected_key]

@pytest.mark.parametrize("parsed_output, expected_output, exception", KWE_POSTPROCESS_TEST_CASES)
def test_kw_postprocess(parsed_output: List[str], expected_output: List[str], exception: bool):
    try:
         postprocessed_output = kwe_custom_postprocess(parsed_output)
    except Exception:
        assert exception
    else:
        assert not exception

    if not exception:
        assert expected_output == postprocessed_output
