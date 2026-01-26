from .connectors.GigaChatConnector import GigaChatConnector, DEFAULT_GIGACHAT_CONFIG
from .connectors.OLlamaConnector import OLlamaConnector, DEFAULT_OLLAMA_CONFIG
from .connectors.OpenAIConnector import OpenAIConnector, GPT4OMINI_CONFIG
from .connectors.LocalAgentConnector import LocalAgentConnector, DEFAULT_LOCALAGENT_CONFIG
from .connectors.StubAgentConnector import StubAgentConnector, DEFAULT_STUBAGENT_CONFIG

DEFAULT_AGENT_CONFIGS = {
    'local_agent':  DEFAULT_LOCALAGENT_CONFIG,
    'ollama': DEFAULT_OLLAMA_CONFIG,
    'gigachat':  DEFAULT_GIGACHAT_CONFIG,
    'openai': GPT4OMINI_CONFIG,
    'stub': DEFAULT_STUBAGENT_CONFIG
}

AVAILABLE_AGENT_CONNECTORS = {
    'local_agent': LocalAgentConnector,
    'ollama': OLlamaConnector,
    'gigachat': GigaChatConnector,
    'openai': OpenAIConnector,
    'stub': StubAgentConnector
}
