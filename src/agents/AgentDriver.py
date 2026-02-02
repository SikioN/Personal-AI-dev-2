from dataclasses import dataclass, field

from .utils import AgentConnectorConfig, AbstractAgentConnector
from .configs import DEFAULT_AGENT_CONFIGS, AVAILABLE_AGENT_CONNECTORS

@dataclass
class AgentDriverConfig:
    name: str = 'ollama'
    agent_config: AgentConnectorConfig = field(default_factory=lambda: DEFAULT_AGENT_CONFIGS['ollama'])

    def to_str(self):
        return f"{self.name}|{self.agent_config.to_str()}"

class AgentDriver:
    @staticmethod
    def connect(config: AgentDriverConfig = AgentDriverConfig()) -> AbstractAgentConnector:
        return AVAILABLE_AGENT_CONNECTORS[config.name](config.agent_config)
