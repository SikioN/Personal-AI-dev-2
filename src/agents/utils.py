from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Dict

@dataclass
class AgentConnectorConfig:
    gen_strategy: Dict = field(default_factory=lambda: dict())
    credentials: Dict = field(default_factory=lambda: dict())
    ext_params: Dict = field(default_factory=lambda: dict())

    def to_str(self):
        str_genstrat = ";".join(list(map(lambda p: f"{p[0]}={p[1]}", sorted([(k, str(v)) for k, v in self.gen_strategy.items()], key=lambda p: p[0]))))
        str_creds = ";".join(list(map(lambda p: f"{p[0]}={p[1]}", sorted([(k, str(v)) for k, v in self.credentials.items()], key=lambda p: p[0]))))
        return f"{str_genstrat}|{str_creds}"

class AbstractAgentConnector:
    @abstractmethod
    def check_connection(self) -> bool:
        pass

    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str, assistant_prompt: str = None) -> str:
        pass

    @abstractmethod
    def close_connection(self) -> None:
        pass
