import pytest
import sys
# TO CHANGE
PROJECT_BASE_DIR = '../'
sys.path.insert(0, PROJECT_BASE_DIR)

from src.pipelines.qa.kg_reasoning.weak_reasoner.answer_generator.agent_tasks.ag.selector import AVAILABLE_AG_TCONFIGS

@pytest.fixture(scope='function')
def ag_tconfig(request):
    return AVAILABLE_AG_TCONFIGS[request.param]
