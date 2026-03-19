"""
kg_utils.py — Generic KG entity mapper (not Wikidata-specific).

KGEntityMapper works with any knowledge graph, not just Wikidata.
It supersedes WikidataMapper as the preferred abstraction.

WikidataMapper in wikidata_utils.py is kept as a backward-compatible alias.
"""
import os
from typing import Optional, List


class KGEntityMapper:
    """
    Entity/relation label mapper for any KG backend.

    Primary mode: Neo4j-backed — all lookups go to Neo4j with LRU cache.
    Fallback mode: file-based — loads id2entity text files into RAM dicts.

    Pass a Neo4jConnector instance to use Neo4j mode; pass a file path string
    to use the legacy file mode.  Both modes expose the same public interface.
    """

    def __init__(self, source, cache_size: int = 10_000):
        """
        :param source: Either an open Neo4jConnector instance (Neo4j mode)
                       or a file-system path string (legacy file mode).
        :param cache_size: Max entries per LRU cache (Neo4j mode only).
        """
        if isinstance(source, str):
            self._init_from_files(source)
        else:
            self._init_from_neo4j(source, cache_size)

    # ------------------------------------------------------------------
    # Init helpers
    # ------------------------------------------------------------------

    def _init_from_files(self, kg_path: str) -> None:
        """Legacy: load entity/relation files into RAM dicts."""
        self._mode = 'file'
        self.id2name: dict = {}
        self.name2id: dict = {}
        self._db = None

        for filename in ("wd_id2entity_text.txt", "wd_id2relation_text.txt"):
            fpath = os.path.join(kg_path, filename)
            if os.path.exists(fpath):
                with open(fpath, 'r', encoding='utf-8') as f:
                    for line in f:
                        parts = line.strip().split('\t')
                        if len(parts) >= 2:
                            ent_id, name = parts[0], parts[1]
                            self.id2name[ent_id] = name
                            self.name2id[name.lower()] = ent_id
            else:
                print(f"[KGEntityMapper] File not found (skipping): {fpath}")

    def _init_from_neo4j(self, connector, cache_size: int) -> None:
        """Neo4j mode: queries DB at runtime with bounded LRU caches."""
        self._mode = 'neo4j'
        self._db = connector
        self.id2name = {}
        self.name2id = {}

        try:
            from cachetools import LRUCache
            self._id2name_cache = LRUCache(maxsize=cache_size)
            self._name2id_cache = LRUCache(maxsize=cache_size)
        except ImportError:
            print("[KGEntityMapper] cachetools not installed — using unbounded dicts.")
            self._id2name_cache = {}
            self._name2id_cache = {}

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_id(self, name: str) -> Optional[str]:
        """Name → str_id (exact match, case-insensitive)."""
        if self._mode == 'file':
            return self.name2id.get(name.lower())

        key = name.lower()
        if key in self._name2id_cache:
            return self._name2id_cache[key]

        # Sort by length: shortest matches first (prefer "United States" over "United States senator")
        result = self._db.execute_query(
            'MATCH (n) WHERE lower(n.name) = lower($name) RETURN n.str_id AS str_id, n.name AS name LIMIT 10',
            params={'name': name}
        )
        if result:
            result.sort(key=lambda x: len(x.get('name', '')))
            str_id = result[0]['str_id']
        else:
            str_id = None

        self._name2id_cache[key] = str_id
        return str_id

    def get_label(self, str_id: str) -> Optional[str]:
        """str_id → human label. Returns None if not found (unlike WikidataMapper which returned str_id)."""
        if self._mode == 'file':
            return self.id2name.get(str_id)

        if str_id in self._id2name_cache:
            cached = self._id2name_cache[str_id]
            return cached if cached != str_id else None

        result = self._db.execute_query(
            'MATCH (n) WHERE n.str_id = $str_id RETURN n.name AS name LIMIT 1',
            params={'str_id': str_id}
        )
        name = result[0]['name'] if result else None
        self._id2name_cache[str_id] = name if name else str_id
        return name

    def get_label_with_id(self, str_id: str) -> str:
        """Returns 'Label (str_id)', or just str_id if label not found."""
        label = self.get_label(str_id)
        return f"{label} ({str_id})" if label else str_id

    def search_names(self, query: str, limit: int = 10) -> List[str]:
        """
        Fuzzy name search.
        Neo4j mode: fulltext index (preferred) with CONTAINS fallback.
        File mode: linear scan over in-memory name dict.
        """
        if self._mode == 'file':
            q = query.lower()
            matches = []
            for name in self.name2id.keys():
                if q in name:
                    matches.append(name)
                    if len(matches) >= limit:
                        break
            return matches

        # Neo4j mode — try fulltext index first
        try:
            result = self._db.execute_query(
                'CALL db.index.fulltext.queryNodes("entity_name_aliases", $query) '
                'YIELD node RETURN node.name AS name LIMIT $limit',
                params={'query': query, 'limit': limit}
            )
            if result:
                return [r['name'] for r in result]
        except Exception:
            pass

        # Fallback: contains scan (Kuzu-safe)
        result = self._db.execute_query(
            'MATCH (n) WHERE lower(n.name) contains lower($query) '
            'RETURN n.name AS name LIMIT $limit',
            params={'query': query, 'limit': limit}
        )
        return [r['name'] for r in result] if result else []
