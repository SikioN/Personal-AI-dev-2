"""GigaChat LLM client (Sber OAuth2 + OpenAI-compatible inference)."""
import os
import json
from typing import Dict, Optional, Union

import httpx

from .base_client import BaseLLMClient

_OAUTH_URL = "https://ngw.devices.sber.ru:9443/api/v2/oauth"
_API_URL = "https://gigachat.devices.sber.ru/api/v1/chat/completions"


class GigaChatClient(BaseLLMClient):
    """
    Env vars:
        GIGACHAT_CREDENTIALS  — Base64-encoded client credentials (required)
        GIGACHAT_MODEL        — Model name (default: GigaChat)
    """

    def __init__(
        self,
        credentials: Optional[str] = None,
        model: Optional[str] = None,
        verify_ssl: Union[bool, str] = True,
        # True = standard TLS verification; str = path to CA bundle (e.g. '/path/to/sber-ca.pem');
        # False = disable verification (insecure, do not use in prod)
    ):
        self.credentials = credentials or os.environ.get("GIGACHAT_CREDENTIALS", "")
        self.model = model or os.environ.get("GIGACHAT_MODEL", "GigaChat")
        self.verify_ssl = verify_ssl
        self._access_token: Optional[str] = None

    # ------------------------------------------------------------------

    def _get_token(self) -> str:
        """Fetch a fresh OAuth2 access token."""
        headers = {
            "Authorization": f"Basic {self.credentials}",
            "RqUID": "some-uuid",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        resp = httpx.post(
            _OAUTH_URL,
            headers=headers,
            data={"scope": "GIGACHAT_API_PERS"},
            verify=self.verify_ssl,
            timeout=10,
        )
        resp.raise_for_status()
        self._access_token = resp.json()["access_token"]
        return self._access_token

    def generate(self, prompt: str, system: Optional[str] = None, json_mode: bool = False) -> str:
        token = self._access_token or self._get_token()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {"model": self.model, "messages": messages}
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        try:
            resp = httpx.post(_API_URL, headers=headers, json=payload,
                              verify=self.verify_ssl, timeout=60)
            if resp.status_code == 401:
                # Token expired — refresh once
                token = self._get_token()
                headers["Authorization"] = f"Bearer {token}"
                resp = httpx.post(_API_URL, headers=headers, json=payload,
                                  verify=self.verify_ssl, timeout=60)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"[GigaChatClient] generate() failed: {e}")
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
