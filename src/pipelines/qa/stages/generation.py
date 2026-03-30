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
    """Stage 7: readable-name context generation + answer_type-aware decoding."""

    # Pattern matching raw entity/relation IDs that are not human-readable
    _ID_RE = re.compile(r'^(Q\d+|P\d+|CQ_\d+|LOCAL_\w+)$', re.IGNORECASE)

    def __init__(
        self,
        llm_client: "BaseLLMClient",
        mapper: "WikidataMapper",
        config: "QAConfig",
    ) -> None:
        self.llm = llm_client
        self.mapper = mapper
        self.config = config

    def _get_display_name(self, node) -> str:
        """Return a human-readable name for a node.

        Priority:
        1. node.name if it is not an ID-format string (already readable).
        2. Try mapper.get_label() on node.name and/or prop['wd_id'].
        3. Fallback: return node.name as-is (CQ_ or LOCAL_ ID).
        """
        name = (node.name or '').strip()
        if name and not self._ID_RE.match(name):
            return name  # already readable ("Сбер", "1508 млрд руб")
        # Try to resolve via mapper
        for candidate in (name, (node.prop or {}).get('wd_id', '')):
            if candidate:
                label = self.mapper.get_label(str(candidate))
                if label and not self._ID_RE.match(str(label)):
                    return label
        return name or node.id or '?'

    _MAX_CTX_CHARS = 6000  # conservative limit (~8k tokens)

    def _build_anon_ctx(self, quads: List[Quadruplet]) -> str:
        """Build readable context from quadruplets for the LLM."""
        lines, seen = [], set()
        for q in quads:
            s = self._get_display_name(q.start_node)
            r = (q.relation.name or '').strip() or '?'
            o = self._get_display_name(q.end_node)
            t = q.time.name if q.time else 'Always'
            sig = f'{s}|{r}|{o}|{t}'
            if sig not in seen:
                seen.add(sig)
                lines.append(f'- {s} → {r} → {o} (Year: {t})')
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
        try:
            ctx = self._build_anon_ctx(selected_quads)

            answer_type = extraction.answer_type
            q_type = extraction.q_type

            if answer_type == 'year' or q_type == 'simple_time':
                answer_hint = 'ОТВЕТ (только год или диапазон лет, например "2024" или "2020 - 2024"):'
            else:
                answer_hint = 'ОТВЕТ (конкретное значение, число или краткая фраза из ФАКТОВ выше):'

            user_msg = (
                f"ВОПРОС: {question}\n"
                f"ВРЕМЕННОЙ КОНТЕКСТ: {retrieval.resolved_time}\n"
                f"ФАКТЫ:\n{ctx}\n"
                f"{answer_hint}"
            )

            raw_ans = self.llm.generate(user_msg, system=self.config.anon_system_prompt)

            if hasattr(self.config, 'debug') and self.config.debug:
                print(f"  [GEN] raw_llm_output={raw_ans!r}")
                print(f"  [GEN] context_used (lines)={len(ctx.splitlines())}")

            if not raw_ans:
                return GenerationResult(
                    answer=None,
                    raw_llm_output='',
                    decoded_qid=None,
                    context_used=ctx,
                )

            _null_tokens = {'null', 'нет', 'не найдено', 'неизвестно', 'unknown'}

            def _is_null(text: str) -> bool:
                t = text.strip().lower()
                return not t or any(tok in t for tok in _null_tokens)

            if answer_type == 'year' or q_type == 'simple_time':
                if _is_null(raw_ans):
                    answer = 'Unknown'
                else:
                    year = self._extract_year(raw_ans)
                    if year:
                        answer = year
                    else:
                        answer = raw_ans.strip() or 'Unknown'
            else:
                stripped = raw_ans.strip()
                if _is_null(stripped):
                    answer = 'Unknown'
                else:
                    # If LLM returned a raw Wikidata Q-ID (legacy fallback), decode it
                    qid = self._decode_qid(stripped)
                    if qid:
                        label = self.mapper.get_label_with_id(qid)
                        if label and not self._ID_RE.match(label):
                            answer = label
                        else:
                            answer = stripped
                    else:
                        answer = stripped

            decoded_qid = self._decode_qid(raw_ans)
            return GenerationResult(
                answer=answer,
                raw_llm_output=raw_ans,
                decoded_qid=decoded_qid,
                context_used=ctx,
            )
        except Exception as e:
            import logging as _logging
            _logging.getLogger(__name__).error("[GenerationStage] Execution failed: %s", e, exc_info=True)
            return GenerationResult(
                answer=None,
                raw_llm_output=str(e),
                decoded_qid=None,
                context_used=ctx if 'ctx' in locals() else '',
            )
