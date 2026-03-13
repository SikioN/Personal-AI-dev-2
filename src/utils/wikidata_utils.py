"""
wikidata_utils.py — Backward-compatible wrapper around KGEntityMapper.

WikidataMapper is kept as an alias so existing code continues to work.
New code should import KGEntityMapper from src.utils.kg_utils directly.
"""
from typing import Optional

from .kg_utils import KGEntityMapper


class WikidataMapper(KGEntityMapper):
    """
    Drop-in replacement for the old WikidataMapper.

    Extends KGEntityMapper with the Wikidata-flavoured `get_label()` that
    returns the wd_id itself when no label is found (legacy behaviour).
    """

    def get_label(self, wd_id: str) -> str:
        """wd_id → human label. Returns wd_id itself if not found (legacy behaviour)."""
        label = super().get_label(wd_id)
        return label if label is not None else wd_id

    def get_label_with_id(self, wd_id: str) -> str:
        """Returns 'Label (wd_id)', or just wd_id if label equals wd_id."""
        label = self.get_label(wd_id)
        return f"{label} ({wd_id})" if label != wd_id else wd_id
