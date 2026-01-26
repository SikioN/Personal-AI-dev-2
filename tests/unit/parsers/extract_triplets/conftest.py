import pytest
import sys
# TO CHANGE
PROJECT_BASE_DIR = '../'
sys.path.insert(0, PROJECT_BASE_DIR)

from src.pipelines.memorize.extractor.agent_tasks.triplet_extraction.selector import AVAILABLE_TRIPLET_EXTRACT_TCONFIGS

@pytest.fixture(scope='function')
def etriplets_tconfig(request):
    return AVAILABLE_TRIPLET_EXTRACT_TCONFIGS[request.param]
