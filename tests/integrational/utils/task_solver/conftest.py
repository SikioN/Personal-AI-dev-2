import pytest

import sys
# TO CHANGE
PROJECT_BASE_DIR = '../'
sys.path.insert(0, PROJECT_BASE_DIR)

from src.utils import AgentTaskSolver
from src.agents import AgentDriver, AgentDriverConfig
from src.agents.connectors.StubAgentConnector import DEFAULT_STUBAGENT_CONFIG

from src.pipelines.memorize.extractor.configs import DEFAULT_EXTRACT_THESISES_TASK_CONFIG, DEFAULT_EXTRACT_TRIPLETS_TASK_CONFIG
from src.pipelines.memorize.updator.configs import DEFAULT_REPLACE_SIMPLE_TASK_CONFIG, DEFAULT_REPLACE_THESIS_TASK_CONFIG
from src.pipelines.qa.answer_generator.configs import DEFAULT_ANSWER_GEN_TASK_CONFIG
from src.pipelines.qa.query_parser.configs import DEFAULT_KW_EXTRACTION_TASK_CONFIG

@pytest.fixture(scope='package')
def ag_solver():
    agent_conn = AgentDriver.connect(
        AgentDriverConfig(name='stub', agent_config=DEFAULT_STUBAGENT_CONFIG))
    return AgentTaskSolver(agent_conn, DEFAULT_ANSWER_GEN_TASK_CONFIG)

@pytest.fixture(scope='package')
def ethesises_solver():
    agent_conn = AgentDriver.connect(
        AgentDriverConfig(name='stub', agent_config=DEFAULT_STUBAGENT_CONFIG))
    return AgentTaskSolver(agent_conn, DEFAULT_EXTRACT_THESISES_TASK_CONFIG)


@pytest.fixture(scope='package')
def etriplets_solver():
    agent_conn = AgentDriver.connect(
        AgentDriverConfig(name='stub', agent_config=DEFAULT_STUBAGENT_CONFIG))
    return AgentTaskSolver(agent_conn, DEFAULT_EXTRACT_TRIPLETS_TASK_CONFIG)

@pytest.fixture(scope='package')
def kwe_solver():
    agent_conn = AgentDriver.connect(
        AgentDriverConfig(name='stub', agent_config=DEFAULT_STUBAGENT_CONFIG))
    return AgentTaskSolver(agent_conn, DEFAULT_KW_EXTRACTION_TASK_CONFIG)

@pytest.fixture(scope='package')
def replace_simple_solver():
    agent_conn = AgentDriver.connect(
        AgentDriverConfig(name='stub', agent_config=DEFAULT_STUBAGENT_CONFIG))
    return AgentTaskSolver(agent_conn, DEFAULT_REPLACE_SIMPLE_TASK_CONFIG)

@pytest.fixture(scope='package')
def replace_thesis_solver():
    agent_conn = AgentDriver.connect(
        AgentDriverConfig(name='stub', agent_config=DEFAULT_STUBAGENT_CONFIG))
    return AgentTaskSolver(agent_conn, DEFAULT_REPLACE_THESIS_TASK_CONFIG)
