import requests
import json
import logging
import re
from typing import Dict, Any, Optional

from src.llm.base_client import BaseLLMClient


SYSTEM_PROMPT = """
You are an expert NER system for a Temporal Knowledge Graph.

FIELDS TO EXTRACT:
1. entities: List of ALL subjects, objects, concepts mentioned.
2. relation: The relationship queried (e.g. "spouse", "president", "born").
3. time: Specific year (e.g. "2011") or null.
4. anchor_entity: (JOIN queries) Entity whose event determines the context time.
5. anchor_event: (JOIN queries) The event/relation (INCLUDE THE VERB, e.g. "nominated for Nobel Prize").
6. type: One of [simple_entity, simple_time, before_after, first_last, time_join].
7. answer_type: "year" if the expected answer is a year/date, "entity" otherwise.

CLASSIFICATION RULES (CRITICAL):
- time_join: Requires finding a specific time from ONE event and applying it to ANOTHER.
  EXAMPLE: "Who was head of gov of USA when Nabokov was nominated for Nobel?"
  → type: "time_join", anchor_entity: "Vladimir Nabokov", anchor_event: "nominated for Nobel Prize in Literature"
- simple_time: The ANSWER itself is a year (e.g. "When did X happen?").
- simple_entity: The ANSWER is a person/place/concept.
- before_after: asks about facts BEFORE or AFTER a year.
- first_last: sequence ordering (first book, last award).

Note: Input questions may be in Russian or English. Preserve entity names in their original language in "entities" list. For Russian questions, extract the relation as a descriptive phrase in Russian (e.g. "чистая прибыль", "генеральный директор").

Output ONLY valid JSON:
{
    "entities": ["Entity1", "Entity2"],
    "relation": "Relation Name",
    "time": "YYYY" or null,
    "anchor_entity": "EntityName" or null,
    "anchor_event": "EventName" or null,
    "type": "question_type",
    "answer_type": "year" or "entity"
}
"""


class DeepSeekClient(BaseLLMClient):
    """
    Drop-in replacement for YandexGPTClient using DeepSeek API.
    Compatible with OpenAI-style chat completions endpoint.

    Usage:
        client = DeepSeekClient(api_key="sk-...")
    """

    API_URL = "https://api.deepseek.com/chat/completions"

    def __init__(
        self,
        api_key: str,
        model: str = "deepseek-chat",
        temperature: float = 0.1,
        max_tokens: int = 512,
    ):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.logger = logging.getLogger(__name__)

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        json_mode: bool = False,
    ) -> str:
        """
        Send a prompt to DeepSeek and return the text response.
        Mirrors YandexGPTClient.generate() signature exactly.
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(self.API_URL, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except (requests.RequestException, KeyError, IndexError) as e:
            self.logger.error(f"[DeepSeek] API error: {e}")
            return ""

    def extract_search_parameters(self, question: str) -> Dict[str, Any]:
        """
        Extract structured NER params from a natural language question.
        Returns: {'entities': [...], 'relation': '...', 'time': 'YYYY' or None}
        """
        prompt = f"Question: {question}"

        response = self.generate(prompt, system=SYSTEM_PROMPT, json_mode=True)
        if not response:
            return {}

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Fallback: strip markdown code blocks (```json ... ```)
            try:
                match = re.search(r'```(?:json)?\s*([\s\S]*?)```', response)
                if match:
                    return json.loads(match.group(1).strip())
                # Last resort: try parsing stripped response directly
                return json.loads(response.strip())
            except Exception:
                self.logger.error(f"[DeepSeek] Failed to parse JSON: {response}")
                return {}
