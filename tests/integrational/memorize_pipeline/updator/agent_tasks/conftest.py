import pytest
import sys

# TO CHANGE
PROJECT_BASE_DIR = '../'
sys.path.insert(0, PROJECT_BASE_DIR)

from src.pipelines.memorize.updator.configs import DEFAULT_REPLACE_THESIS_TASK_CONFIG, DEFAULT_REPLACE_SIMPLE_TASK_CONFIG
from src.agents.connectors.StubAgentConnector import StubAgentConnector
from src.utils import AgentTaskSolver

@pytest.fixture(scope='package')
def replace_simple_agent_solver():
    return AgentTaskSolver(agent=StubAgentConnector(), config=DEFAULT_REPLACE_SIMPLE_TASK_CONFIG)

@pytest.fixture(scope='package')
def replace_thesis_agent_solver():
    return AgentTaskSolver(agent=StubAgentConnector(), config=DEFAULT_REPLACE_THESIS_TASK_CONFIG)
