"""OpenAI (and compatible) LLM client using the official openai SDK."""
import os
import json
from typing import Dict, Optional

from .base_client import BaseLLMClient


class OpenAIClient(BaseLLMClient):
    """
    Works with OpenAI and any OpenAI-compatible API (together.ai, local vLLM, etc.)

    Env vars:
        OPENAI_API_KEY   — API key (required)
        OPENAI_MODEL     — Model name (default: gpt-4o-mini)
        OPENAI_BASE_URL  — Optional custom base URL
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        try:
            from openai import OpenAI
        except ImportError as e:
            raise ImportError("openai package required: pip install openai>=1.12.0") from e

        self.model = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        resolved_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        resolved_base = base_url or os.environ.get("OPENAI_BASE_URL") or None

        kwargs = {"api_key": resolved_key}
        if resolved_base:
            kwargs["base_url"] = resolved_base
        self._client = OpenAI(**kwargs)

    def generate(self, prompt: str, system: Optional[str] = None, json_mode: bool = False) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        kwargs = {"model": self.model, "messages": messages}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            resp = self._client.chat.completions.create(**kwargs)
            return resp.choices[0].message.content or ""
        except Exception as e:
            print(f"[OpenAIClient] generate() failed: {e}")
            return ""

    def extract_search_parameters(self, question: str) -> Dict:
        system = """You are an expert NER system for a Temporal Knowledge Graph.

FIELDS TO EXTRACT:
1. entities: List of ALL subjects, objects, concepts mentioned.
2. relation: The relationship queried (e.g. "spouse", "president", "born").
3. time: Specific year (e.g. "2011") or null.
4. anchor_entity: (JOIN queries) Entity whose event determines the context time.
5. anchor_event: (JOIN queries) The event/relation to find the time.
6. type: One of [simple_entity, simple_time, before_after, first_last, time_join].
7. answer_type: "year" if the expected answer is a year/date, "entity" otherwise.

CLASSIFICATION RULES:
- simple_time: The ANSWER itself is a year or date. -> answer_type MUST be "year"
- simple_entity: The ANSWER is a person/place/organization/concept.
- before_after: Question asks for entity BEFORE or AFTER a specific year.
- first_last: Question asks for first/last in a sequence.
- time_join: Requires linking TWO events via temporal overlap.

Note: Input questions may be in Russian or English.
- Entity names of Russian organizations/persons: ALWAYS output in their native Cyrillic form, even if the question is in English (e.g. "Sber" -> "Сбер", "Sberbank" -> "Сбербанк").
- For Russian questions: extract the relation as a short Russian phrase (e.g. "чистая прибыль", "генеральный директор").
- For English questions about Russian entities: extract the relation in English.

Output ONLY valid JSON:
{"entities": ["Entity1"], "relation": "Relation", "time": "YYYY" or null, "anchor_entity": null, "anchor_event": null, "type": "question_type", "answer_type": "year" or "entity"}"""
        raw = self.generate(question, system=system, json_mode=True)
        try:
            return json.loads(raw)
        except Exception:
            import re
            try:
                match = re.search(r'```(?:json)?\s*([\s\S]*?)```', raw)
                if match:
                    return json.loads(match.group(1).strip())
                return json.loads(raw.strip())
            except Exception:
                return {"entities": [question], "relation": None, "time": None,
                        "type": "simple_entity", "answer_type": "entity"}
