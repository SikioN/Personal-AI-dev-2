"""
entity_resolver.py — 5-level entity resolution with deduplication-safe ID generation.

Resolution levels:
  L1: wd_id_hint provided and already in Neo4j            → exact_id
  L2: mapper.get_id(name) exact Neo4j match               → exact_neo4j
  L2.5: rapidfuzz token_sort_ratio >= 90 vs top candidates → lexical
  L3: ChromaDB ANN distance < 0.25                        → vector
  L4: LLM disambiguation (distance 0.25–0.45)             → llm
  L5: UniqueIDGenerator.make_unique()                     → new (LOCAL_xxxxx)
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# UniqueIDGenerator
# ---------------------------------------------------------------------------

class UniqueIDGenerator:
    """Generates deterministic LOCAL_ IDs and protects against false collisions."""

    PREFIX = "LOCAL_"

    def make_id(self, name: str, node_type: str = "") -> str:
        """Deterministic ID: MD5(name + node_type)[:10]."""
        seed = f"{name.lower().strip()}|{node_type}"
        return self.PREFIX + hashlib.md5(seed.encode()).hexdigest()[:10]

    def make_unique(self, name: str, node_type: str, mapper) -> str:
        """
        Returns a canonical LOCAL_ ID for *name*.

        - If no node exists with base_id → return base_id (new entity).
        - If a node exists with the same label (case-insensitive) → same object,
          return base_id for deduplication.
        - If a node exists with a *different* label → true hash collision,
          try suffixes -1, -2, ... up to 99.

        :param mapper: KGEntityMapper (Neo4j mode preferred for live lookup).
        :raises RuntimeError: if 100 candidates are all occupied by different entities.
        """
        base_id = self.make_id(name, node_type)
        existing_label = mapper.get_label(base_id)

        if existing_label is None:
            return base_id

        if existing_label.lower() == name.lower().strip():
            return base_id

        for i in range(1, 100):
            candidate = f"{base_id}-{i}"
            existing = mapper.get_label(candidate)
            if existing is None or existing.lower() == name.lower().strip():
                return candidate

        raise RuntimeError(
            f"[UniqueIDGenerator] Cannot generate unique ID for '{name}' after 100 attempts"
        )


# ---------------------------------------------------------------------------
# ResolutionResult
# ---------------------------------------------------------------------------

@dataclass
class ResolutionResult:
    canonical_id: str
    canonical_name: str
    input_name: str
    is_new: bool
    confidence: float
    method: str  # exact_id | exact_neo4j | lexical | vector | llm | new


# ---------------------------------------------------------------------------
# EntityResolver
# ---------------------------------------------------------------------------

class EntityResolver:
    """
    Resolves an entity name to a canonical KG node ID via a 5-level cascade.

    Parameters
    ----------
    mapper : KGEntityMapper
        Used for name ↔ id lookups (L2).
    vector_db : optional
        ChromaDB collection for ANN search (L3). Pass None to skip.
    llm_client : optional
        BaseLLMClient for disambiguation (L4). Pass None to skip.
    rapidfuzz_threshold : float
        Minimum token_sort_ratio for lexical match (L2.5). Default 90.
    vector_threshold : float
        Maximum cosine distance for vector match (L3). Default 0.25.
    llm_threshold : float
        Maximum distance to attempt LLM disambiguation (L4). Default 0.45.
    """

    def __init__(
        self,
        mapper,
        vector_db=None,
        llm_client=None,
        rapidfuzz_threshold: float = 90.0,
        vector_threshold: float = 0.25,
        llm_threshold: float = 0.45,
    ):
        self.mapper = mapper
        self.vector_db = vector_db
        self.llm_client = llm_client
        self.rf_threshold = rapidfuzz_threshold
        self.v_threshold = vector_threshold
        self.llm_threshold = llm_threshold
        self._id_gen = UniqueIDGenerator()

    def resolve(
        self,
        name: str,
        node_type: str = "object",
        wd_id_hint: Optional[str] = None,
    ) -> ResolutionResult:
        """
        Resolve *name* to a canonical (id, name) pair.

        Parameters
        ----------
        name : str
            Raw input entity name.
        node_type : str
            KG node type (used for LOCAL_ ID generation if L5 is reached).
        wd_id_hint : str, optional
            Pre-computed ID hint (e.g. from Wikidata). Skips all levels if valid.
        """
        # L1: wd_id_hint provided and already in Neo4j
        if wd_id_hint:
            label = self.mapper.get_label(wd_id_hint)
            if label is not None:
                return ResolutionResult(
                    canonical_id=wd_id_hint,
                    canonical_name=label,
                    input_name=name,
                    is_new=False,
                    confidence=1.0,
                    method="exact_id",
                )

        # L2: exact Neo4j name match
        str_id = self.mapper.get_id(name)
        if str_id:
            label = self.mapper.get_label(str_id) or name
            return ResolutionResult(
                canonical_id=str_id,
                canonical_name=label,
                input_name=name,
                is_new=False,
                confidence=1.0,
                method="exact_neo4j",
            )

        # L2.5: rapidfuzz lexical match
        result = self._resolve_lexical(name)
        if result:
            return result

        # L3: ChromaDB ANN
        result = self._resolve_vector(name, node_type)
        if result:
            return result

        # L4: LLM disambiguation (only if vector distance is in [v_threshold, llm_threshold])
        result = self._resolve_llm(name, node_type)
        if result:
            return result

        # L5: create new LOCAL_ entity
        new_id = self._id_gen.make_unique(name, node_type, self.mapper)
        return ResolutionResult(
            canonical_id=new_id,
            canonical_name=name,
            input_name=name,
            is_new=True,
            confidence=0.0,
            method="new",
        )

    # ------------------------------------------------------------------
    # L2.5 — rapidfuzz lexical
    # ------------------------------------------------------------------

    def _resolve_lexical(self, name: str) -> Optional[ResolutionResult]:
        try:
            from rapidfuzz import fuzz
        except ImportError:
            return None

        candidates = self.mapper.search_names(name, limit=10)
        best_score, best_name = 0.0, None
        for cand in candidates:
            score = fuzz.token_sort_ratio(name.lower(), cand.lower())
            if score > best_score:
                best_score, best_name = score, cand

        if best_name and best_score >= self.rf_threshold:
            str_id = self.mapper.get_id(best_name)
            if str_id:
                return ResolutionResult(
                    canonical_id=str_id,
                    canonical_name=best_name,
                    input_name=name,
                    is_new=False,
                    confidence=best_score / 100.0,
                    method="lexical",
                )
        return None

    # ------------------------------------------------------------------
    # L3 — ChromaDB ANN
    # ------------------------------------------------------------------

    def _resolve_vector(self, name: str, node_type: str) -> Optional[ResolutionResult]:
        if self.vector_db is None:
            return None
        try:
            results = self.vector_db.query(query_texts=[name], n_results=1)
            if not results or not results.get("ids"):
                return None
            distance = results["distances"][0][0]
            if distance > self.llm_threshold:
                return None
            if distance <= self.v_threshold:
                matched_id = results["ids"][0][0]
                matched_name = (results.get("documents") or [[name]])[0][0]
                label = self.mapper.get_label(matched_id) or matched_name
                return ResolutionResult(
                    canonical_id=matched_id,
                    canonical_name=label,
                    input_name=name,
                    is_new=False,
                    confidence=1.0 - distance,
                    method="vector",
                )
            # distance in (v_threshold, llm_threshold] → save for L4
            self._last_vector_candidate = results
        except Exception as e:
            logger.debug("[EntityResolver] L3 vector search failed: %s", e)
        return None

    # ------------------------------------------------------------------
    # L4 — LLM disambiguation
    # ------------------------------------------------------------------

    def _resolve_llm(self, name: str, node_type: str) -> Optional[ResolutionResult]:
        if self.llm_client is None:
            return None
        candidates = self.mapper.search_names(name, limit=5)
        if not candidates:
            return None

        cand_list = "\n".join(f"- {c}" for c in candidates)
        prompt = (
            f"Which of the following entities best matches '{name}'?\n"
            f"{cand_list}\n"
            "Reply with the exact name of the best match, or 'NONE' if none fit."
        )
        try:
            answer = self.llm_client.generate(prompt).strip()
            if answer == "NONE" or not answer:
                return None
            str_id = self.mapper.get_id(answer)
            if str_id:
                label = self.mapper.get_label(str_id) or answer
                return ResolutionResult(
                    canonical_id=str_id,
                    canonical_name=label,
                    input_name=name,
                    is_new=False,
                    confidence=0.6,
                    method="llm",
                )
        except Exception as e:
            logger.debug("[EntityResolver] L4 LLM disambiguation failed: %s", e)
        return None
