import pytest
import numpy as np
from typing import List, Tuple, Dict

import sys
sys.path.insert(0, "../")

from src.pipelines.qa.kg_reasoning.weak_reasoner.knowledge_retriever.BeamSearchTripletsRetriever import BeamSearchTripletsRetriever, \
    TraversingPath, GraphBeamSearchConfig, TraversedPath
from src.kg_model import KnowledgeGraphModel
from src.utils import Logger

from cases import POPULATED_CALCULATE_PSCORE_TEST_CASES, POPULATED_GET_AVAILABLE_NIDS_TEST_CASES, \
    POPULATED_GET_AVAILABLE_RINFO_TEST_CASES, POPULATED_GET_TRIPLET_SCORES_TEST_CASES, POPULATED_FILTER_PATHS_TEST_CASES

@pytest.mark.parametrize("path_len, accum_score, expected_score, exception, search_config, log, kg_model",
                         POPULATED_CALCULATE_PSCORE_TEST_CASES, indirect=['kg_model'])
def test_calculate_path_score(
    path_len: int, accum_score: float, expected_score: float, exception: bool,
    search_config: GraphBeamSearchConfig, log: Logger, kg_model: KnowledgeGraphModel):

    bm_retriever = BeamSearchTripletsRetriever(kg_model, log, search_config)

    try:
        real_score = bm_retriever.calculate_path_score(path_len, accum_score)
    except ValueError:
        assert exception
    else:
        assert not exception
        assert np.abs(real_score-expected_score) < 10e-8


@pytest.mark.parametrize("base_nid, cur_path_idx, traversing_paths, prev_nid, expected_adjn, exception, search_config, log, kg_model",
                         POPULATED_GET_AVAILABLE_NIDS_TEST_CASES, indirect=['kg_model'])
def get_available_nids(base_nid: str, cur_path_idx: int, traversing_paths: List[TraversingPath], prev_nid: str,
                       expected_adjn: List[str], exception: bool, search_config: GraphBeamSearchConfig,
                       log: Logger, kg_model: KnowledgeGraphModel):
    bm_retriever = BeamSearchTripletsRetriever(kg_model, log, search_config)

    try:
        real_adjn = bm_retriever.get_available_nids(base_nid, cur_path_idx, traversing_paths, prev_nid)
    except ValueError:
        assert exception
    else:
        assert not exception
        assert set(real_adjn) == set(expected_adjn)

def test_get_available_rinfo(
        base_nid: str, adj_nids: List[str], cur_path_idx: int,
        traversing_paths: List[TraversingPath],
        expected_shared_tinfo: Dict[str,str], expected_ridstotids_map: Dict[str, List[str]],
        exception: bool,  search_config: GraphBeamSearchConfig,
        log: Logger, kg_model: KnowledgeGraphModel):

    bm_retriever = BeamSearchTripletsRetriever(kg_model, log, search_config)

    try:
        real_shared_tinfo, real_ridstotids_map = bm_retriever.get_available_rinfo(base_nid, adj_nids, cur_path_idx, traversing_paths)
    except ValueError:
        assert exception
    else:
        assert not exception

        assert len(real_shared_tinfo) == len(expected_shared_tinfo)
        assert set(real_shared_tinfo.keys()) == set(expected_shared_tinfo.keys())

        for k in expected_shared_tinfo.keys():
            assert real_shared_tinfo[k] == expected_shared_tinfo[k]

        assert len(real_ridstotids_map) == len(expected_ridstotids_map)
        assert set(real_ridstotids_map.keys()) == set(expected_ridstotids_map.keys())

        for k in expected_ridstotids_map.keys():
            assert set(real_ridstotids_map[k]) == set(real_ridstotids_map[k])

def test_get_triplet_scores():
    # TODO
    pass

@pytest.mark.parametrize("ended_paths, continuous_paths, expected_paths, exception, search_config, log, kg_model",
                         POPULATED_FILTER_PATHS_TEST_CASES, indirect=['kg_model'])
def test_filter_paths(ended_paths: List[TraversedPath], continuous_paths: List[TraversedPath],
                      expected_paths: List[TraversedPath], exception: bool,
                      search_config: GraphBeamSearchConfig, log: Logger,
                      kg_model: KnowledgeGraphModel):

    bm_retriever = BeamSearchTripletsRetriever(kg_model, log, search_config)

    try:
        real_paths = bm_retriever.filter_paths(ended_paths, continuous_paths)
    except ValueError:
        assert exception
    else:
        assert not exception
        assert expected_paths == real_paths
