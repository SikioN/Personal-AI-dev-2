"""Qwen (DashScope) LLM client — uses OpenAI-compatible endpoint."""
import os
import json
from typing import Dict, Optional

from .base_client import BaseLLMClient

_QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


class QwenClient(BaseLLMClient):
    """
    Qwen client via DashScope OpenAI-compatible API.

    Env vars:
        QWEN_API_KEY  — DashScope API key (required)
        QWEN_MODEL    — Model name (default: qwen-plus)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        try:
            from openai import OpenAI
        except ImportError as e:
            raise ImportError("openai package required: pip install openai>=1.12.0") from e

        self.model = model or os.environ.get("QWEN_MODEL", "qwen-plus")
        resolved_key = api_key or os.environ.get("QWEN_API_KEY", "")
        self._client = OpenAI(api_key=resolved_key, base_url=_QWEN_BASE_URL)

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
            print(f"[QwenClient] generate() failed: {e}")
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
