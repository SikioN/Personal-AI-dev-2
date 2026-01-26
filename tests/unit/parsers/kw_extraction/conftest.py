import pytest
import sys
# TO CHANGE
PROJECT_BASE_DIR = '../'
sys.path.insert(0, PROJECT_BASE_DIR)

from src.pipelines.qa.kg_reasoning.weak_reasoner.query_parser.agent_tasks.kw_extraction.selector import AVAILABLE_KWE_TCONFIGS

@pytest.fixture(scope='function')
def kwe_tconfig(request):
    return AVAILABLE_KWE_TCONFIGS[request.param]
