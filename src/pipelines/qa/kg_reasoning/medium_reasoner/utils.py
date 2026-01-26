from dataclasses import dataclass, field
from typing import List

@dataclass
class SearchPlanInfo:
    base_query: str 
    search_steps: List[str] = field(default_factory=lambda: list())
    steps_answers: List[str] = field(default_factory=lambda: list())

    def to_str(self):
        return f"{self.base_query}|{self.search_steps}|{self.steps_answers}"