from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

import numpy as np

from src.utils.data_structs import Quadruplet, QuadrupletCreator

if TYPE_CHECKING:
    from src.config.qa_config import QAConfig
    from src.pipelines.qa.stages.retrieval import RetrievalResult
    from src.pipelines.qa.stages.extraction import ExtractionResult


@dataclass
class ScoredResult:
    quad: Quadruplet
    conf: float   # final combined score
    e5: float     # E5 cosine similarity (from ChromaDB/read_embbeddings)
    tp: float     # TComplEx sigmoid [0,1]
    tl: float     # TComplEx raw logit


@dataclass
class ScoringResult:
    all_scored: List[ScoredResult]
    selected_quads: List[Quadruplet]


def _parse_years(quad: Quadruplet) -> Tuple[Optional[int], Optional[int]]:
    if not quad.time or quad.time.name in ('Always', 'Unknown'):
        return None, None
    years = sorted(int(y) for y in re.findall(r'(\d{4})', quad.time.name))
    if not years:
        return None, None
    return years[0], years[-1]


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + np.exp(-x))


def select_by_confidence_gap(
    results_sorted: List[ScoredResult],
    min_f: int = 2,
    max_f: int = 7,
    gap: float = 0.20,
) -> List[ScoredResult]:
    """
    Gap-based fact selection (replaces LLM fact-selection stage).
    Keeps adding facts until a confidence gap > `gap` is detected,
    subject to min_f/max_f bounds.
    """
    if not results_sorted:
        return []

    top_conf = results_sorted[0].conf
    selected = []
    for r in results_sorted[:max_f]:
        if len(selected) >= min_f and (top_conf - r.conf) > gap:
            break
        selected.append(r)

    return selected


class ScoringStage:
    """
    Stage 5: E5 + TComplEx hybrid scoring.
    E5 scores come from RetrievalResult.candidate_e5_scores (no re-encoding here).
    """

    def __init__(self, embeddings_struct, temporal_scorer, config: "QAConfig") -> None:
        self.embeddings_struct = embeddings_struct
        self.temporal_scorer = temporal_scorer
        self.config = config

    def run(
        self,
        question: str,
        retrieval: "RetrievalResult",
        extraction: "ExtractionResult",
    ) -> ScoringResult:
        # 2.3: guard against empty retrieval — return empty result immediately
        if not retrieval.unique_candidates:
            import logging as _logging
            _logging.getLogger(__name__).warning(
                "[ScoringStage] No candidates — returning empty result"
            )
            return ScoringResult(all_scored=[], selected_quads=[])

        candidates = retrieval.unique_candidates
        e5_scores = retrieval.candidate_e5_scores
        resolved_time = retrieval.resolved_time
        alpha = extraction.alpha

        # Collect TComplEx logits to decide adaptive alpha (P1)
        raw_logits: List[float] = []
        tcomplex_map: Dict[str, float] = {}

        if resolved_time and self.temporal_scorer:
            for quad in candidates:
                sid = quad.start_node.prop.get('wd_id') or quad.start_node.id
                rid = quad.relation.prop.get('wd_id') or quad.relation.id
                oid = quad.end_node.prop.get('wd_id') or quad.end_node.id
                if sid and rid and oid:
                    try:
                        logit = float(self.temporal_scorer.score(sid, rid, oid, str(resolved_time)))
                        tcomplex_map[quad.id] = logit
                        raw_logits.append(logit)
                    except Exception:
                        pass

        # P1: adaptive alpha gate
        use_tcomplex = (
            len(raw_logits) >= self.config.min_tl_count
            and max(raw_logits) > self.config.tcomplex_threshold
        )

        # P2: min-max normalise TComplEx logits
        if use_tcomplex and raw_logits:
            lo, hi = min(raw_logits), max(raw_logits)
            rng = hi - lo if hi != lo else 1.0
        else:
            lo = hi = rng = 1.0

        scored: List[ScoredResult] = []
        for quad in candidates:
            e5 = e5_scores.get(quad.id, 0.0)
            tl = tcomplex_map.get(quad.id, float('-inf'))
            tp = 0.0

            if use_tcomplex and quad.id in tcomplex_map:
                # min-max normalise instead of raw sigmoid
                tp = (tcomplex_map[quad.id] - lo) / rng
                conf = (1.0 - alpha) * e5 + alpha * tp
            else:
                conf = e5

            # NOTE: removed 'final += 1.0' temporal boost from old production code
            scored.append(ScoredResult(quad=quad, conf=conf, e5=e5, tp=tp, tl=tl))

        scored.sort(key=lambda x: x.conf, reverse=True)
        top_scored = scored[:retrieval.search_k]

        # first_last post-sort by year
        if extraction.q_type == 'first_last':
            timed = [((_parse_years(r.quad)[0] or 9999), r) for r in top_scored]
            timed.sort(key=lambda x: x[0])
            is_first = any(
                w in question.lower()
                for w in ('first', 'earliest', 'oldest', 'initial')
            )
            top_scored = [c[1] for c in (timed[:5] if is_first else timed[-5:])]

        # P3: gap-based selection — notebook-aligned
        # temporal_bucket passes through directly (no boost);
        # gap-select only extra facts outside the bucket
        tb_ids = {q.id for q in retrieval.temporal_bucket}
        extra_scored = [r for r in top_scored if r.quad.id not in tb_ids]
        n_max_extra = max(self.config.min_facts,
                          self.config.max_facts - len(retrieval.temporal_bucket))
        gap_selected = select_by_confidence_gap(
            extra_scored,
            min_f=self.config.min_facts,
            max_f=n_max_extra,
            gap=self.config.confidence_gap,
        )
        selected_quads = retrieval.temporal_bucket + [r.quad for r in gap_selected]

        return ScoringResult(all_scored=scored, selected_quads=selected_quads)
