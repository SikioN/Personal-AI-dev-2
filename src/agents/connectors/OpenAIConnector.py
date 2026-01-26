import os
from openai import OpenAI

from ..utils import AbstractAgentConnector, AgentConnectorConfig


DEEPSEEK_KEY = 'YOUR_DEEPSEEK_KEY'
DEEPSEEK_CONFIG = AgentConnectorConfig(
    gen_strategy={'seed': 42, 'top_p': 10e-16, 'temperature': 0.0, 'frequency_penalty':0, 'presence_penalty':0},
    credentials={'token': DEEPSEEK_KEY, 'model': 'deepseek-chat', 'base_url': 'https://api.deepseek.com'},
    ext_params={'timeout': 560, 'max_retries': 5})

GPT4OMINI_KEY = "YOUR_OPENAI_KEY"
GPT4OMINI_CONFIG = AgentConnectorConfig(
    gen_strategy={'seed': 42, 'top_p': 10e-16, 'temperature': 0.0, 'frequency_penalty':0, 'presence_penalty':0},
    credentials={'token': GPT4OMINI_KEY, 'model': 'gpt-4o-mini', 'base_url': None},
    ext_params={'timeout': 560, 'max_retries': 5})


class OpenAIConnector(AbstractAgentConnector):
    def __init__(self, config: AgentConnectorConfig = GPT4OMINI_KEY) -> None:
        self.config = config
        base_url = None if config.credentials['base_url'] == 'None' else config.credentials['base_url']
        self.config.credentials['base_url'] = base_url
        
        self.client = OpenAI(
            api_key=os.environ.get("OPENAI_API_KEY", config.credentials['token']),
            base_url=config.credentials['base_url'])

    def check_connection(self):
        # TODO
        pass

    def close_connection(self):
        self.client.close()

    def generate(self, system_prompt: str, user_prompt: str, assistant_prompt: str = None) -> str:
        msgs = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
        if assistant_prompt is not None:
            msgs.append({"role": "assistant", "content": assistant_prompt})

        completion = self.client.chat.completions.create(
            model=self.config.credentials['model'],
            messages=msgs, **self.config.gen_strategy)

        return completion.choices[0].message.content
