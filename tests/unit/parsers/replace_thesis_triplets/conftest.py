import pytest
import sys
# TO CHANGE
PROJECT_BASE_DIR = '../'
sys.path.insert(0, PROJECT_BASE_DIR)

from src.pipelines.memorize.updator.agent_tasks.replace_thesis_triplets.selector import AVAILABLE_REPLACE_THESIS_TCONFIGS

@pytest.fixture(scope='function')
def rthesis_tconfig(request):
    return AVAILABLE_REPLACE_THESIS_TCONFIGS[request.param]
