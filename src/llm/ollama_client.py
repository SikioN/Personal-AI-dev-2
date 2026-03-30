
import requests
import json
import logging
from typing import Dict, Any, Optional

from src.llm.base_client import BaseLLMClient


class OllamaClient(BaseLLMClient):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3"):
        self.base_url = base_url
        self.model = model
        self.logger = logging.getLogger(__name__)

    def generate(self, prompt: str, system: Optional[str] = None, json_mode: bool = False) -> str:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        if system:
            payload["system"] = system
        if json_mode:
            payload["format"] = "json"

        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error communicating with Ollama: {e}")
            return ""

    def extract_search_parameters(self, question: str) -> Dict[str, Any]:
        """
        Extracts structured search parameters (Entity, Relation, Time) from a natural language question.
        Returns a dictionary with keys: 'entity', 'relation', 'time'.
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
        prompt = f"Question: {question}"

        response = self.generate(prompt, system=system_prompt, json_mode=True)
        if not response:
            return {}
            
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            self.logger.error(f"Failed to parse JSON from Ollama: {response}")
            try:
                # Fallback: simple cleanup
                clean = response.strip()
                if clean.startswith("```json"):
                    clean = clean[7:-3]
                return json.loads(clean)
            except:
                pass
            return {}
