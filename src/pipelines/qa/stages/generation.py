from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, TYPE_CHECKING

from src.utils.data_structs import Quadruplet

if TYPE_CHECKING:
    from src.llm.base_client import BaseLLMClient
    from src.config.qa_config import QAConfig
    from src.utils.wikidata_utils import WikidataMapper
    from src.pipelines.qa.stages.extraction import ExtractionResult
    from src.pipelines.qa.stages.retrieval import RetrievalResult


@dataclass
class GenerationResult:
    answer: Optional[str]  # None when LLM call failed (5.1)
    raw_llm_output: str
    decoded_qid: Optional[str]
    context_used: str


class GenerationStage:
    """Stage 7: anonymized Q-ID generation + answer_type-aware decoding."""

    def __init__(
        self,
        llm_client: "BaseLLMClient",
        mapper: "WikidataMapper",
        config: "QAConfig",
    ) -> None:
        self.llm = llm_client
        self.mapper = mapper
        self.config = config

    def _anonymize_question(
        self,
        question: str,
        resolved_entities: List,  # List[Tuple[orig, resolved_name, wd_id]]
    ) -> str:
        """Replace entity names in question with Q-IDs."""
        anon_q = question
        for orig, resolved_name, wd_id in resolved_entities:
            if wd_id:
                for name in (resolved_name, orig):
                    if name and name in anon_q:
                        anon_q = anon_q.replace(name, wd_id)
        return anon_q

    _MAX_CTX_CHARS = 6000  # conservative limit (~8k tokens)

    def _build_anon_ctx(self, quads: List[Quadruplet]) -> str:
        """Build anonymized context using Wikidata Q/P IDs only."""
        lines, seen = [], set()
        for q in quads:
            s = q.start_node.prop.get('wd_id') or q.start_node.id or '?'
            r = q.relation.prop.get('wd_id') or q.relation.id or '?'
            o = q.end_node.prop.get('wd_id') or q.end_node.id or '?'
            t = q.time.name if q.time else 'Always'
            sig = f'{s}-{r}-{o}-{t}'
            if sig not in seen:
                seen.add(sig)
                lines.append(f'- {s} --[{r}]--> {o} (Time: {t})')
        ctx = '\n'.join(lines)
        if len(ctx) > self._MAX_CTX_CHARS:
            ctx = ctx[:self._MAX_CTX_CHARS] + "\n... [context truncated]"
        return ctx

    @staticmethod
    def _decode_qid(raw: str) -> Optional[str]:
        m = re.search(r'([QP]\d+)', raw)
        return m.group(1) if m else None

    @staticmethod
    def _extract_year(raw: str) -> Optional[str]:
        """Extract a 4-digit year or range like '1925 - 1950' from LLM output."""
        # Range first
        m = re.search(r'(\d{4})\s*[-–]\s*(\d{4})', raw)
        if m:
            return f"{m.group(1)} - {m.group(2)}"
        m = re.search(r'(\d{4})', raw)
        return m.group(1) if m else None

    def run(
        self,
        question: str,
        selected_quads: List[Quadruplet],
        extraction: "ExtractionResult",
        retrieval: "RetrievalResult",
    ) -> GenerationResult:
        anon_q = self._anonymize_question(question, retrieval.resolved_entities)
        ctx = self._build_anon_ctx(selected_quads)

        answer_type = extraction.answer_type
        q_type = extraction.q_type

        if answer_type == 'year' or q_type == 'simple_time':
            answer_hint = 'ANSWER (year or date range only, e.g. "1925" or "1899 - 1917"):'
        else:
            answer_hint = 'ANSWER (Q-ID only, e.g. Q123):'

        user_msg = (
            f"QUESTION: {anon_q}\n"
            f"TIME CONTEXT: {retrieval.resolved_time}\n"
            f"FACTS:\n{ctx}\n"
            f"{answer_hint}"
        )

        try:
            raw_ans = self.llm.generate(user_msg, system=self.config.anon_system_prompt)
            if extraction.debug:
                print(f"  [GEN] raw_llm_output={raw_ans!r}")
                print(f"  [GEN] context_used (lines)={len(ctx.splitlines())}")
        except Exception as e:
            # 5.1: return None answer so handlers can show a proper user-facing message
            import logging as _logging
            _logging.getLogger(__name__).error("[GenerationStage] LLM call failed: %s", e)
            return GenerationResult(
                answer=None,
                raw_llm_output=str(e),
                decoded_qid=None,
                context_used=ctx,
            )

        if answer_type == 'year' or q_type == 'simple_time':
            year = self._extract_year(raw_ans)
            if year:
                answer = year
            else:
                # Fallback: try to decode Q-ID and look up its label (might be a year node)
                qid = self._decode_qid(raw_ans)
                if qid:
                    label = self.mapper.get_label(qid)
                    year2 = self._extract_year(label)
                    answer = year2 or label
                else:
                    answer = raw_ans.strip() or 'Unknown'
        else:
            qid = self._decode_qid(raw_ans)
            if qid:
                label = self.mapper.get_label_with_id(qid)
                answer = label if label else qid
            elif 'null' in raw_ans.lower():
                answer = 'Unknown'
            else:
                answer = raw_ans.strip() or 'Unknown'


        decoded_qid = self._decode_qid(raw_ans)
        return GenerationResult(
            answer=answer,
            raw_llm_output=raw_ans,
            decoded_qid=decoded_qid,
            context_used=ctx,
        )
