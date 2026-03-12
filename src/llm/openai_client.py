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
        system = (
            "You are an NLP assistant. Extract entities, relation, time, and question type "
            "from the user question. Respond with JSON only: "
            '{"entities": [], "relation": null, "time": null, "type": "simple", "answer_type": "entity"}'
        )
        raw = self.generate(question, system=system, json_mode=True)
        try:
            return json.loads(raw)
        except Exception:
            return {"entities": [question], "relation": None, "time": None,
                    "type": "simple", "answer_type": "entity"}
