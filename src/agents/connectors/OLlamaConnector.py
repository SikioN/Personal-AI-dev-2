from ..utils import AbstractAgentConnector, AgentConnectorConfig
from ollama import Client

DEFAULT_OLLAMA_CONFIG = AgentConnectorConfig(
    gen_strategy={'num_predict': 2048, 'seed': 42, 'top_k': 1, 'temperature': 0.0},
    credentials={'model': 'llama3.2'},
    ext_params={'host': 'localhost', 'port': 11434, 'timeout': 560, 'keep_alive': -1})

# available models
# llama3.2 (3B)
# mistral (7B)
# gemma2 (9B)

class OLlamaConnector(AbstractAgentConnector):
    def __init__(self, config: AgentConnectorConfig = DEFAULT_OLLAMA_CONFIG) -> None:
        self.config = config
        self.open_connection()

    def open_connection(self):
        self.client = Client(
            host=f"http://{self.config.ext_params['host']}:{self.config.ext_params['port']}",
            timeout=self.config.ext_params['timeout'])

    def check_connection(self) -> bool:
        pass

    def close_connection(self):
        del self.client

    def generate(self, system_prompt: str, user_prompt: str, assistant_prompt: str = None) -> str:

        msgs = [{'role':'system', 'content': system_prompt}, {'role':'user', 'content':user_prompt}]
        if assistant_prompt is not None:
            msgs.append({'role':'assistant', 'content': assistant_prompt})

        raw_output = self.client.chat(
            model=self.config.credentials['model'],
            options=self.config.gen_strategy,
            messages=msgs,
            keep_alive=self.config.ext_params['keep_alive'])

        response = raw_output['message']['content']
        return response
