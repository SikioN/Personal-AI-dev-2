import os
import json
import pickle
import argparse
import numpy as np
import shutil

def main():
    parser = argparse.ArgumentParser(description="Merge out.json into tkbc wikidata dataset.")
    parser.add_argument("--baseline_dir", type=str, default="data/wikidata_big/kg/tkbc_processed_data/wikidata_big/", help="Path to baseline tkbc data.")
    parser.add_argument("--json_file", type=str, default="out.json", help="Path to out.json.")
    parser.add_argument("--out_dir", type=str, default="data/wikidata_extended/kg/tkbc_processed_data/wikidata_extended/", help="Output directory.")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    # Copy everything first, then we'll overwrite what we change
    for f in os.listdir(args.baseline_dir):
        src_f = os.path.join(args.baseline_dir, f)
        dst_f = os.path.join(args.out_dir, f)
        if os.path.isfile(src_f):
            shutil.copy(src_f, dst_f)

    # Load dictionaries
    with open(os.path.join(args.out_dir, "ent_id"), "rb") as f:
        ent_id = pickle.load(f)
    with open(os.path.join(args.out_dir, "rel_id"), "rb") as f:
        rel_id = pickle.load(f)
    with open(os.path.join(args.out_dir, "ts_id"), "rb") as f:
        ts_id = pickle.load(f)
    
    # Read original train.pickle
    with open(os.path.join(args.out_dir, "train.pickle"), "rb") as f:
        train_data = pickle.load(f)

    print(f"Original train size: {train_data.shape}")
    print(f"Original ent size: {len(ent_id)}")
    print(f"Original rel size: {len(rel_id)}")
    print(f"Original ts size: {len(ts_id)}")

    # Load JSON
    with open(args.json_file, "r", encoding="utf-8") as f:
        new_records = json.load(f)

    new_triples = []

    for r in new_records:
        s = r["s"]["id"]
        p = r["r"]["id"]
        o = r["o"]["id"]
        
        try:
            st = int(r["t"]["prop"]["start"])
            en = int(r["t"]["prop"]["end"])
        except ValueError:
            print(f"Skipping record due to bad year parsing: {r}")
            continue

        # Update ent_id
        if s not in ent_id:
            ent_id[s] = len(ent_id)
        if o not in ent_id:
            ent_id[o] = len(ent_id)
        
        # Update rel_id
        if p not in rel_id:
            rel_id[p] = len(rel_id)
            
        # Update ts_id 
        ts_start_tuple = (st, 0, 0)
        ts_end_tuple = (en, 0, 0)
        
        if ts_start_tuple not in ts_id:
            ts_id[ts_start_tuple] = len(ts_id)
        if ts_end_tuple not in ts_id:
            ts_id[ts_end_tuple] = len(ts_id)

        s_idx = ent_id[s]
        p_idx = rel_id[p]
        o_idx = ent_id[o]
        ts_start_idx = ts_id[ts_start_tuple]
        ts_end_idx = ts_id[ts_end_tuple]

        new_triples.append([s_idx, p_idx, o_idx, ts_start_idx, ts_end_idx])

    if new_triples:
        new_triples_np = np.array(new_triples, dtype=train_data.dtype)
        train_data_extended = np.vstack([train_data, new_triples_np])
    else:
        train_data_extended = train_data

    # Save
    with open(os.path.join(args.out_dir, "ent_id"), "wb") as f:
        pickle.dump(ent_id, f)
    with open(os.path.join(args.out_dir, "rel_id"), "wb") as f:
        pickle.dump(rel_id, f)
    with open(os.path.join(args.out_dir, "ts_id"), "wb") as f:
        pickle.dump(ts_id, f)
    with open(os.path.join(args.out_dir, "train.pickle"), "wb") as f:
        pickle.dump(train_data_extended, f)

    print(f"Extended train size: {train_data_extended.shape}")
    print(f"Extended ent size: {len(ent_id)}")
    print(f"Extended rel size: {len(rel_id)}")
    print(f"Extended ts size: {len(ts_id)}")
    
    print(f"Successfully saved to {args.out_dir}")

if __name__ == "__main__":
    main()
