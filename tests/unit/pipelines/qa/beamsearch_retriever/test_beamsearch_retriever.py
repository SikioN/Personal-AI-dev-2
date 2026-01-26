import pytest
import numpy as np
from typing import List, Tuple

import sys
sys.path.insert(0, "../")

from src.pipelines.qa.kg_reasoning.weak_reasoner.knowledge_retriever.BeamSearchTripletsRetriever import BeamSearchTripletsRetriever, TraversingPath

from cases import CALCULATE_TRIPLET_SCORE_TEST_CASES, EXTEND_TPATH_TEST_CASES

@pytest.mark.parametrize("raw_score, expected_value, exception",
                         CALCULATE_TRIPLET_SCORE_TEST_CASES)
def test_calculate_triplet_score(raw_score: float, expected_value: float, exception: bool) -> None:

    try:
        real_value = BeamSearchTripletsRetriever.calculate_triplet_score(raw_score)
    except ValueError:
        assert exception
    else:
        assert not exception
        assert np.abs(expected_value - real_value) < 10e-8

@pytest.mark.parametrize("pinfo, triplet_scores, expected_new_tpaths, exception",
                         EXTEND_TPATH_TEST_CASES)
def test_update_path_candidates(
    pinfo: TraversingPath, triplet_scores: List[Tuple[str, str, float]],
    expected_new_tpaths: List[TraversingPath], exception: bool) -> None:

    try:
        real_new_tpaths = BeamSearchTripletsRetriever.extend_tpath(pinfo, triplet_scores)
    except ValueError:
        assert exception
    else:
        assert not exception

        for i, c_path in enumerate(real_new_tpaths):
            assert c_path.path == expected_new_tpaths[i].path
            assert c_path.unique_nids == expected_new_tpaths[i].unique_nids
            assert c_path.unique_tids == expected_new_tpaths[i].unique_tids
            assert np.abs(c_path.accum_score-expected_new_tpaths[i].accum_score) < 10e-8
