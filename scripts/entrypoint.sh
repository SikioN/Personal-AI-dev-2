#!/bin/bash
# entrypoint.sh — Railway/Docker entry point.
# Downloads model + KG data from HF, builds KuzuDB on first run. Idempotent.
set -ex
cd /app
echo "[entrypoint] Starting. KG_DATA_PATH=${KG_DATA_PATH} KUZU_PATH=${KUZU_PATH}"
ls /app/data 2>/dev/null || echo "[entrypoint] /app/data is empty or missing"

KG_DIR="${KG_DATA_PATH:-/app/data/wikidata_big/kg}"
MODEL_DIR="${FINETUNED_MODEL_PATH:-/app/data/models/wikidata_finetuned_remote/wikidata_finetuned}"
TCOMPLEX_CKPT="${TCOMPLEX_CHECKPOINT:-/app/data/models/cronkgqa/tcomplex.ckpt}"
KUZU_DIR="${KUZU_PATH:-/app/data/kuzu_db}"

# 1. KG raw data
if [[ ! -f "$KG_DIR/full.txt" ]]; then
    echo "[entrypoint] Downloading KG data from HF Hub (${HF_KG_DATA_REPO})..."
    python -c "
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id='${HF_KG_DATA_REPO}', repo_type='dataset',
    local_dir='${KG_DIR}', token='${HF_TOKEN:-}' or None
)
print('[entrypoint] KG data downloaded.')
"
fi

# 2. E5 model (warm-up save to local path — required by config.json check)
if [[ ! -f "$MODEL_DIR/config.json" ]]; then
    echo "[entrypoint] Downloading E5 model from HF Hub (${HF_MODEL_REPO})..."
    python -c "
from sentence_transformers import SentenceTransformer
SentenceTransformer('${HF_MODEL_REPO}').save('${MODEL_DIR}')
print('[entrypoint] E5 model saved locally.')
"
fi

# 3. TComplEx checkpoint (optional)
if [[ -n "${HF_TCOMPLEX_REPO:-}" && ! -f "$TCOMPLEX_CKPT" ]]; then
    echo "[entrypoint] Downloading TComplEx from HF Hub (${HF_TCOMPLEX_REPO})..."
    mkdir -p "$(dirname "$TCOMPLEX_CKPT")"
    python -c "
from huggingface_hub import hf_hub_download
hf_hub_download(
    repo_id='${HF_TCOMPLEX_REPO}', filename='tcomplex.ckpt',
    local_dir='$(dirname "${TCOMPLEX_CKPT}")', token='${HF_TOKEN:-}' or None
)
print('[entrypoint] TComplEx downloaded.')
"
fi

BUILD_KG_ARGS=""

# 3.5. Pre-built ChromaDB from HuggingFace (skips ~78h CPU embedding)
CHROMA_NODES_DIR="${CHROMA_NODES_PATH:-/app/data/graph_structures/vectorized_nodes/default}"
CHROMA_QUADS_DIR="${CHROMA_QUADS_PATH:-/app/data/graph_structures/vectorized_quadruplets/default}"
mkdir -p "$CHROMA_NODES_DIR" "$CHROMA_QUADS_DIR"
if [[ -n "${HF_CHROMA_REPO:-}" ]]; then
    if [[ ! -f "$CHROMA_NODES_DIR/chroma.sqlite3" || ! -f "$CHROMA_QUADS_DIR/chroma.sqlite3" ]]; then
        echo "[entrypoint] Downloading pre-built ChromaDB from HF (${HF_CHROMA_REPO})..."
        python -c "
import os, tarfile
from huggingface_hub import hf_hub_download
repo = '${HF_CHROMA_REPO}'
token = '${HF_TOKEN:-}' or None
for fname, dest in [
    ('vectorized_nodes_default.tar.gz',      '${CHROMA_NODES_DIR}'),
    ('vectorized_quadruplets_default.tar.gz', '${CHROMA_QUADS_DIR}'),
]:
    if not os.path.exists(os.path.join(dest, 'chroma.sqlite3')):
        f = hf_hub_download(repo_id=repo, filename=fname, repo_type='dataset', token=token)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with tarfile.open(f) as t: t.extractall(os.path.dirname(dest))
        print(f'[entrypoint] {fname} extracted to {dest}')
print('[entrypoint] ChromaDB ready.')
"
        BUILD_KG_ARGS="$BUILD_KG_ARGS --skip-chroma"
    else
        echo "[entrypoint] ChromaDB already present — skipping HF download."
        BUILD_KG_ARGS="$BUILD_KG_ARGS --skip-chroma"
    fi
fi

# 4. Build KuzuDB + ChromaDB (always run — build_kg.py is idempotent, skips if already populated)
# NOTE: KuzuDB expects a FILE path, not a directory — do NOT mkdir the kuzu path itself
mkdir -p "$(dirname "$KUZU_DIR")"
# KuzuDB needs a FILE path. Remove stale directory if present (from previous broken runs)
if [[ -d "$KUZU_DIR" ]]; then
    echo "[entrypoint] Removing stale kuzu_db directory (KuzuDB requires a file path)..."
    rm -rf "$KUZU_DIR"
fi
# Remove WAL file — Railway kills containers uncleanly, leaving a WAL that causes kuzu segfault
rm -f "${KUZU_DIR}.wal" 2>/dev/null || true

# Validate existing KuzuDB — detect Python-level corruption (not segfaults)
if [[ -e "$KUZU_DIR" ]]; then
    set +e
    python -c "
import kuzu, sys
try:
    db = kuzu.Database('${KUZU_DIR}')
    del db
    print('[entrypoint] KuzuDB OK.')
except Exception as e:
    print(f'[entrypoint] KuzuDB corrupted ({e}), removing for rebuild...')
    sys.exit(1)
"
    KUZU_EXIT=$?
    set -e
    if [[ $KUZU_EXIT -ne 0 ]]; then
        echo "[entrypoint] KuzuDB validation failed (exit $KUZU_EXIT), removing for rebuild..."
        rm -f "${KUZU_DIR}" "${KUZU_DIR}.wal" 2>/dev/null || true
    fi
fi

# Support BUILD_KG_FORCE=1 for manual clean rebuild (e.g. when KuzuDB is polluted)
if [[ "${BUILD_KG_FORCE:-0}" == "1" ]]; then
    echo "[entrypoint] BUILD_KG_FORCE=1 — forcing clean rebuild of KuzuDB + ChromaDB..."
    BUILD_KG_ARGS="$BUILD_KG_ARGS --force"
fi
echo "[entrypoint] Running build_kg.py (idempotent — skips if already populated)..."
python scripts/build_kg.py $BUILD_KG_ARGS
echo "[entrypoint] Build complete (or skipped — already populated)."

echo "[entrypoint] All checks passed. Starting bot..."
exec python bot.py
