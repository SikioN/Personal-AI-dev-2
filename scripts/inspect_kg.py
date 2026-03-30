#!/usr/bin/env python3
"""
inspect_kg.py — Inspect quadruplets stored in KuzuDB and ChromaDB.

Usage:
    python scripts/inspect_kg.py                     # show first 20 quads
    python scripts/inspect_kg.py --limit 50          # show first 50 quads
    python scripts/inspect_kg.py --search "прибыль"  # filter by keyword
    python scripts/inspect_kg.py --stats             # counts only, no rows
    python scripts/inspect_kg.py --subject "Сбер"    # filter by subject name
"""
import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def main():
    parser = argparse.ArgumentParser(description="Inspect KuzuDB + ChromaDB contents")
    parser.add_argument("--limit", type=int, default=20, help="Max rows to display (default: 20)")
    parser.add_argument("--search", type=str, default=None, help="Filter: keyword in any field")
    parser.add_argument("--subject", type=str, default=None, help="Filter: subject node name contains")
    parser.add_argument("--stats", action="store_true", help="Show counts only, skip row output")
    parser.add_argument("--chroma", action="store_true", help="Also show ChromaDB documents")
    args = parser.parse_args()

    # ── Connect to KuzuDB ────────────────────────────────────────────────────
    import kuzu

    kuzu_path = os.environ.get("KUZU_PATH", "data/kuzu_db/graph.db")
    if not os.path.exists(os.path.dirname(kuzu_path) or "."):
        print(f"[ERR] KuzuDB parent dir not found: {kuzu_path}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  KuzuDB: {kuzu_path}")
    print(f"{'='*60}")

    db = kuzu.Database(kuzu_path, read_only=True)
    conn = kuzu.Connection(db)

    # ── Node counts ──────────────────────────────────────────────────────────
    for table in ("object", "time", "hyper", "episodic"):
        try:
            res = conn.execute(f"MATCH (n:{table}) RETURN count(n) AS cnt")
            df = res.get_as_df()
            cnt = df["cnt"].iloc[0] if not df.empty else 0
            print(f"  Nodes [{table:10s}]: {cnt:>8,}")
        except Exception:
            pass

    # ── Edge counts ──────────────────────────────────────────────────────────
    for rel_table in ("simple", "hyper_rel"):
        try:
            res = conn.execute(f"MATCH ()-[r:{rel_table}]->() RETURN count(r) AS cnt")
            df = res.get_as_df()
            cnt = df["cnt"].iloc[0] if not df.empty else 0
            print(f"  Edges [{rel_table:10s}]: {cnt:>8,}")
        except Exception:
            pass

    if args.stats:
        print()
        _chroma_stats()
        return

    # ── Fetch quadruplets ────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    keyword = args.search or ""
    subj_filter = args.subject or ""

    where_clauses = []
    if subj_filter:
        where_clauses.append(f"lower(n1.name) CONTAINS lower('{subj_filter}')")
    if keyword:
        where_clauses.append(
            f"(lower(n1.name) CONTAINS lower('{keyword}') OR "
            f"lower(r.name) CONTAINS lower('{keyword}') OR "
            f"lower(n2.name) CONTAINS lower('{keyword}'))"
        )
    where_str = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    query = f"""
        MATCH (n1:object)-[r:simple]->(n2:object)
        {where_str}
        RETURN n1.name AS subject, r.name AS relation, n2.name AS object,
               r.prop AS rel_prop
        LIMIT {args.limit}
    """

    try:
        res = conn.execute(query)
        df = res.get_as_df()
    except Exception as e:
        print(f"[ERR] Query failed: {e}")
        sys.exit(1)

    if df.empty:
        print("  No quadruplets found matching the filter.")
    else:
        label = f"  Quadruplets (showing up to {args.limit}"
        if subj_filter:
            label += f", subject~'{subj_filter}'"
        if keyword:
            label += f", keyword~'{keyword}'"
        label += "):"
        print(label)
        print()

        col_w = 35
        header = f"  {'#':>4}  {'Subject':<{col_w}}  {'Relation':<{col_w}}  {'Object':<{col_w}}  Time"
        print(header)
        print("  " + "-" * (len(header) - 2))

        for i, row in df.iterrows():
            subj = str(row["subject"])[:col_w]
            rel  = str(row["relation"])[:col_w]
            obj  = str(row["object"])[:col_w]
            # Extract time from rel_prop map
            try:
                prop = row["rel_prop"]
                time_str = prop.get("time_name", "") if isinstance(prop, dict) else ""
            except Exception:
                time_str = ""
            print(f"  {i+1:>4}  {subj:<{col_w}}  {rel:<{col_w}}  {obj:<{col_w}}  {time_str}")

    # ── ChromaDB ─────────────────────────────────────────────────────────────
    if args.chroma:
        print(f"\n{'='*60}")
        print("  ChromaDB documents (quadruplet embeddings)")
        print(f"{'='*60}")
        _chroma_stats(show_docs=True, limit=args.limit, keyword=keyword)

    print()


def _chroma_stats(show_docs: bool = False, limit: int = 10, keyword: str = ""):
    try:
        import chromadb
        nodes_path = os.environ.get(
            "CHROMA_NODES_PATH",
            "data/graph_structures/vectorized_nodes/default",
        )
        quads_path = os.environ.get(
            "CHROMA_QUADS_PATH",
            "data/graph_structures/vectorized_quadruplets/default",
        )

        for label, path in [("nodes", nodes_path), ("quadruplets", quads_path)]:
            if not os.path.exists(path):
                print(f"  ChromaDB [{label}]: not found at {path}")
                continue
            client = chromadb.PersistentClient(path=path)
            collections = client.list_collections()
            for col in collections:
                c = client.get_collection(col.name)
                cnt = c.count()
                print(f"  ChromaDB [{label}/{col.name}]: {cnt:>8,} vectors")

                if show_docs and cnt > 0:
                    results = c.get(limit=limit, include=["documents"])
                    docs = results.get("documents", [])
                    filtered = [d for d in docs if not keyword or keyword.lower() in d.lower()]
                    for j, doc in enumerate(filtered[:limit], 1):
                        print(f"    {j:>3}. {doc[:120]}")
    except Exception as e:
        print(f"  ChromaDB: {e}")


if __name__ == "__main__":
    main()
