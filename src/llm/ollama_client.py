
import requests
import json
import logging
from typing import Dict, Any, Optional

class OllamaClient:
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
        You are an expert Named Entity Recognition (NER) system for a Temporal Knowledge Graph.
        Your task is to extract search parameters from a user's question.
        
        EXTRACT:
        1. entities: A list of ALL important subjects, objects, or concepts (e.g. ["Apple", "Steve Jobs"], ["Award", "Acting"]).
        2. relation: The relationship queried (e.g. "CEO", "received award").
        3. time: Specific year (e.g. "2011") or null.

        Output ONLY valid JSON:
        {
            "entities": ["Entity1", "Entity2"],
            "relation": "Relation Name",
            "time": "YYYY" or null
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
