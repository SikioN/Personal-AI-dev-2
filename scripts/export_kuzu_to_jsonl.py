#!/usr/bin/env python3
"""
export_kuzu_to_jsonl.py — Export quadruplets from KuzuDB to JSONL for TComplEx training.

Usage:
    python scripts/export_kuzu_to_jsonl.py
    python scripts/export_kuzu_to_jsonl.py --kuzu-path data/kuzu_db/graph.db --out extract_data/quadruplets.jsonl
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--kuzu-path", default=os.environ.get("KUZU_PATH", "data/kuzu_db/graph.db"))
    parser.add_argument("--out", default="extract_data/quadruplets.jsonl")
    args = parser.parse_args()

    import kuzu

    print(f"Opening KuzuDB: {args.kuzu_path}")
    db = kuzu.Database(args.kuzu_path)
    conn = kuzu.Connection(db)

    out = []
    for rel_table in ("simple", "hyper_rel", "episodic_rel"):
        try:
            res = conn.execute(
                f"MATCH (s)-[r:{rel_table}]->(o) "
                f"RETURN s.str_id, r.str_id, r.name, r.t_id, r.prop, o.str_id"
            )
            count = 0
            while res.has_next():
                row = res.get_next()
                s_id, r_id, r_name, t_id, r_prop, o_id = row
                prop = dict(r_prop) if r_prop else {}
                start = prop.get("start", "") or prop.get("year", "")
                end   = prop.get("end", "") or start
                out.append({
                    "s": {"id": s_id},
                    "r": {"id": r_id or r_name},
                    "o": {"id": o_id},
                    "t": {"prop": {"start": start, "end": end}},
                })
                count += 1
            print(f"  {rel_table}: {count} quadruplets")
        except Exception as e:
            print(f"  [WARN] {rel_table}: {e}")

    if not out:
        print("ERROR: No quadruplets exported. Check KuzuDB path.")
        sys.exit(1)

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for q in out:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")

    print(f"\nExported {len(out)} quadruplets → {args.out}")
    print("Next step:")
    print(f"  .venv/bin/python scripts/retrain_tcomplex.py \\")
    print(f"      --from-scratch --jsonl {args.out} \\")
    print(f"      --tkbc-dir data/local_tcomplex/ \\")
    print(f"      --rank 128 --epochs 100 \\")
    print(f"      --checkpoint-out models/cronkgqa/tcomplex.ckpt")


if __name__ == "__main__":
    main()
