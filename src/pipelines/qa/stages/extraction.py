from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.llm.base_client import BaseLLMClient
    from src.config.qa_config import QAConfig


@dataclass
class ExtractionResult:
    entities: List[str]
    query_time: Optional[str]
    anchor_entity: Optional[str]
    anchor_event: Optional[str]
    q_type: str           # simple_entity|simple_time|before_after|first_last|time_join
    answer_type: str      # "entity" | "year"
    alpha: float          # from QAConfig.alpha_by_type[q_type]
    filter_temporal: bool
    raw: Dict


class ExtractionStage:
    """Stage 1: LLM-based question parsing."""

    def __init__(self, llm_client: "BaseLLMClient", config: "QAConfig") -> None:
        self.llm = llm_client
        self.config = config

    def run(self, question: str) -> ExtractionResult:
        ext = self.llm.extract_search_parameters(question)

        entities = ext.get('entities', [])
        if isinstance(entities, str):
            entities = [entities]

        q_type = ext.get('type', 'simple_entity')
        answer_type = ext.get('answer_type', 'entity')

        # Default answer_type to 'year' for simple_time if LLM didn't set it
        if q_type == 'simple_time' and answer_type == 'entity':
            answer_type = 'year'

        alpha = self.config.alpha_by_type.get(q_type, self.config.alpha_default)
        filter_temporal = q_type in ('before_after', 'time_join')

        return ExtractionResult(
            entities=entities,
            query_time=ext.get('time'),
            anchor_entity=ext.get('anchor_entity'),
            anchor_event=ext.get('anchor_event'),
            q_type=q_type,
            answer_type=answer_type,
            alpha=alpha,
            filter_temporal=filter_temporal,
            raw=ext,
        )
