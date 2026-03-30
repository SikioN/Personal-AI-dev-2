import requests
import json
import logging
from typing import Dict, Any, Optional

from src.llm.base_client import BaseLLMClient


class YandexGPTClient(BaseLLMClient):
    """
    Drop-in replacement for OllamaClient using Yandex Foundation Models API.
    Supports YandexGPT-4 (Pro) and any compatible model (QWEN etc.).

    Usage:
        client = YandexGPTClient(
            api_key="YOUR_YANDEX_CLOUD_API_KEY",
            folder_id="YOUR_FOLDER_ID",
            model_name="yandexgpt"   # or "yandexgpt-lite", "qwen" etc.
        )
    """

    # YandexGPT Foundation Models endpoint
    API_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

    def __init__(
        self,
        api_key: str,
        folder_id: str,
        model_name: str = "yandexgpt",
        temperature: float = 0.1,
        max_tokens: int = 512,
    ):
        self.api_key = api_key
        self.folder_id = folder_id
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.logger = logging.getLogger(__name__)

        # Build full model URI  e.g. gpt://folder_id/yandexgpt/latest
        self.model_uri = f"gpt://{self.folder_id}/{self.model_name}/latest"

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        json_mode: bool = False,
    ) -> str:
        """
        Send a prompt to YandexGPT and return the text response.
        Mirrors OllamaClient.generate() signature exactly.
        """
        messages = []
        if system:
            messages.append({"role": "system", "text": system})
        messages.append({"role": "user", "text": prompt})

        # If json_mode is requested, append a hint to the system/user message
        if json_mode:
            messages[0]["text"] += "\nOutput ONLY valid JSON. No extra text."

        payload = {
            "modelUri": self.model_uri,
            "completionOptions": {
                "stream": False,
                "temperature": self.temperature,
                "maxTokens": str(self.max_tokens),
            },
            "messages": messages,
        }

        headers = {
            "Authorization": f"Api-Key {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(self.API_URL, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            # Navigate standard YandexGPT response structure
            return data["result"]["alternatives"][0]["message"]["text"]
        except (requests.RequestException, KeyError, IndexError) as e:
            self.logger.error(f"[YandexGPT] API error: {e}")
            return ""

    def extract_search_parameters(self, question: str) -> Dict[str, Any]:
        """
        Extract structured NER params from a natural language question.
        Mirrors OllamaClient.extract_search_parameters() exactly.
        Returns: {'entities': [...], 'relation': '...', 'time': 'YYYY' or None}
        """
        system_prompt = """
You are an expert NER system for a Temporal Knowledge Graph.

FIELDS TO EXTRACT:
1. entities: List of ALL subjects, objects, concepts mentioned.
2. relation: The relationship queried (e.g. "spouse", "president", "born").
3. time: Specific year (e.g. "2011") or null.
4. anchor_entity: (JOIN queries) Entity whose event determines the time.
5. anchor_event: (JOIN queries) The event/relation to find the time.
6. type: One of [simple_entity, simple_time, before_after, first_last, time_join].
7. answer_type: "year" if the expected answer is a year/date, "entity" otherwise.

CLASSIFICATION RULES:
- simple_time: The ANSWER itself is a year or date (e.g. "When did X happen?")
  -> answer_type MUST be "year"
- simple_entity: The ANSWER is a person/place/organization/concept.
  -> Even if the question contains a year as a FILTER, it's still simple_entity!
- before_after: Question asks for entity BEFORE or AFTER a specific year.
- first_last: Question asks for first/last in a sequence.
- time_join: Requires linking TWO events via temporal overlap.

Note: Input questions may be in Russian. Preserve entity names in their original language in "entities" list.

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
        prompt = f"Question: {question}"

        response = self.generate(prompt, system=system_prompt, json_mode=True)
        if not response:
            return {}

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Fallback: strip markdown code blocks (```json ... ```)
            try:
                import re
                match = re.search(r'```(?:json)?\s*([\s\S]*?)```', response)
                if match:
                    return json.loads(match.group(1).strip())
                # Last resort: try parsing stripped response directly
                return json.loads(response.strip())
            except Exception:
                self.logger.error(f"[YandexGPT] Failed to parse JSON: {response}")
                return {}
