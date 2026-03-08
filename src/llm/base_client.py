from abc import ABC, abstractmethod
from typing import Dict, Optional


class BaseLLMClient(ABC):
    """Abstract base class for all LLM backends."""

    @abstractmethod
    def generate(self, prompt: str, system: Optional[str] = None, json_mode: bool = False) -> str:
        """Send a prompt and return the text response."""
        ...

    @abstractmethod
    def extract_search_parameters(self, question: str) -> Dict:
        """
        Extract structured NER parameters from a natural language question.
        Returns dict with keys: entities, relation, time, anchor_entity, anchor_event,
        type (question type), answer_type ('year' or 'entity').
        """
        ...
