import pytest
import sys
# TO CHANGE
PROJECT_BASE_DIR = '../'
sys.path.insert(0, PROJECT_BASE_DIR)

from src.pipelines.memorize.extractor.agent_tasks.thesis_extraction.selector import AVAILABLE_THESIS_EXTRACT_TCONFIGS

@pytest.fixture(scope='function')
def ethesises_tconfig(request):
    return AVAILABLE_THESIS_EXTRACT_TCONFIGS[request.param]
