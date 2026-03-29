#!/bin/bash
# setup.sh — Bootstrap for KG Navigator bot
# Usage: bash setup.sh [--build-kg]
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

BUILD_KG=false
for arg in "$@"; do
    [[ "$arg" == "--build-kg" ]] && BUILD_KG=true
done

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

ok()   { echo -e "  ${GREEN}[OK]${NC}  $*"; }
warn() { echo -e "  ${YELLOW}[WARN]${NC} $*"; }
err()  { echo -e "  ${RED}[ERR]${NC}  $*"; }
info() { echo -e "  ${CYAN}[--]${NC}  $*"; }

echo -e "\n${BOLD}====  setup.sh  ====${NC}\n"

# ── GPU / CUDA detection ───────────────────────────────────────────────────────
GPU_NAME=""
CUDA_MAJOR=""
TORCH_INDEX_URL=""
if command -v nvidia-smi &>/dev/null && nvidia-smi &>/dev/null 2>&1; then
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1 || echo "Unknown GPU")
    CUDA_MAJOR=$(nvidia-smi 2>/dev/null | grep -oP 'CUDA Version: \K[0-9]+' | head -1 || echo "")
    if   [[ "${CUDA_MAJOR:-0}" -ge 12 ]]; then TORCH_INDEX_URL="https://download.pytorch.org/whl/cu121"
    elif [[ "${CUDA_MAJOR:-0}" -ge 11 ]]; then TORCH_INDEX_URL="https://download.pytorch.org/whl/cu118"
    fi
elif [[ "$(uname)" == "Darwin" && "$(uname -m)" == "arm64" ]]; then
    GPU_NAME="Apple Silicon (MPS)"
fi

# ── 1. Python 3.10+ ───────────────────────────────────────────────────────────
echo -e "${BOLD}[1] Python interpreter${NC}"
PYTHON=""
for candidate in python3.11 python3.10 python3; do
    if command -v "$candidate" &>/dev/null; then
        ver=$("$candidate" -c "import sys; print(sys.version_info[:2])")
        if "$candidate" -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" 2>/dev/null; then
            PYTHON="$candidate"
            ok "Found $candidate ($ver)"
            break
        fi
    fi
done
if [[ -z "$PYTHON" ]]; then
    err "Python 3.10+ not found. Install from https://www.python.org/downloads/"
    exit 1
fi

# ── 2. Virtual environment ────────────────────────────────────────────────────
echo -e "\n${BOLD}[2] Virtual environment (.venv)${NC}"
if [[ ! -d ".venv" ]]; then
    info "Creating .venv ..."
    "$PYTHON" -m venv .venv
    ok ".venv created"
else
    ok ".venv already exists"
fi
VENV_PYTHON=".venv/bin/python"
VENV_PIP=".venv/bin/pip"

# ── 3. Dependencies ───────────────────────────────────────────────────────────
echo -e "\n${BOLD}[3] Installing dependencies${NC}"
"$VENV_PIP" install --upgrade pip -q

# 3a. PyTorch — install GPU build first so requirements.txt doesn't downgrade it
if [[ -n "$TORCH_INDEX_URL" ]]; then
    info "GPU detected: $GPU_NAME (CUDA $CUDA_MAJOR) — installing torch+cu${CUDA_MAJOR} ..."
    "$VENV_PIP" install "torch>=2.0.0" --index-url "$TORCH_INDEX_URL" -q
    ok "torch installed (CUDA $CUDA_MAJOR)"
elif [[ "$GPU_NAME" == "Apple Silicon (MPS)" ]]; then
    info "Apple Silicon detected — installing torch with MPS support ..."
    "$VENV_PIP" install "torch>=2.0.0" -q
    ok "torch installed (MPS)"
else
    info "No GPU detected — installing CPU-only torch ..."
    "$VENV_PIP" install "torch>=2.0.0" -q
    ok "torch installed (CPU)"
fi

# 3b. Remaining dependencies (torch already satisfied, pip won't downgrade it)
info "pip install -r requirements.txt ..."
"$VENV_PIP" install -r requirements.txt -q
ok "All dependencies installed"

# 3c. Verify critical imports
echo ""
info "Verifying critical packages..."
IMPORT_ERRORS=()
for pkg_check in \
    "torch" \
    "sentence_transformers" \
    "kuzu" \
    "chromadb" \
    "aiogram" \
    "natasha" \
    "pymupdf:fitz" \
    "neo4j" \
    "huggingface_hub"; do
    mod="${pkg_check##*:}"    # module name (part after colon, or whole string)
    label="${pkg_check%%:*}"  # display name (part before colon, or whole string)
    if "$VENV_PYTHON" -c "import ${mod}" 2>/dev/null; then
        ok "import $label"
    else
        err "import $label FAILED"
        IMPORT_ERRORS+=("$label")
    fi
done

# torch accelerator status
TORCH_CUDA=$("$VENV_PYTHON" -c "import torch; print(torch.cuda.is_available())" 2>/dev/null || echo "False")
TORCH_VER=$("$VENV_PYTHON"  -c "import torch; print(torch.__version__)"          2>/dev/null || echo "?")
if [[ "$TORCH_CUDA" == "True" ]]; then
    CUDA_DEV=$("$VENV_PYTHON" -c "import torch; print(torch.cuda.get_device_name(0))" 2>/dev/null || echo "?")
    ok "torch $TORCH_VER — CUDA available ($CUDA_DEV)"
elif [[ "$GPU_NAME" == "Apple Silicon (MPS)" ]]; then
    MPS_OK=$("$VENV_PYTHON" -c "import torch; print(torch.backends.mps.is_available())" 2>/dev/null || echo "False")
    [[ "$MPS_OK" == "True" ]] \
        && ok "torch $TORCH_VER — MPS available" \
        || warn "torch $TORCH_VER — MPS not available"
else
    warn "torch $TORCH_VER — CUDA not available (CPU only)"
fi

if [[ ${#IMPORT_ERRORS[@]} -gt 0 ]]; then
    err "Failed imports: ${IMPORT_ERRORS[*]}"
    err "Try: .venv/bin/pip install -r requirements.txt --force-reinstall"
    exit 1
fi

# ── Device banner ──────────────────────────────────────────────────────────────
echo ""
if [[ "$TORCH_CUDA" == "True" ]]; then
    CUDA_DEV_BANNER=$("$VENV_PYTHON" -c "import torch; print(torch.cuda.get_device_name(0))" 2>/dev/null || echo "?")
    VRAM_BANNER=$("$VENV_PYTHON" -c "import torch; print(torch.cuda.get_device_properties(0).total_memory // 1024**3)" 2>/dev/null || echo "?")
    echo -e "  ${GREEN}${BOLD}[GPU]${NC}  ${CUDA_DEV_BANNER}  ${VRAM_BANNER} GB VRAM  torch ${TORCH_VER}"
elif [[ "$GPU_NAME" == "Apple Silicon (MPS)" ]]; then
    echo -e "  ${GREEN}${BOLD}[GPU]${NC}  Apple Silicon (MPS)  torch ${TORCH_VER}"
else
    echo -e "  ${RED}${BOLD}[CPU]${NC}  No GPU detected — torch ${TORCH_VER}  (embeddings will be slow)"
fi
echo ""

# ── 4. Directories ────────────────────────────────────────────────────────────
echo -e "\n${BOLD}[4] Creating required directories${NC}"
DIRS=(
    "extract_data"
    "extract/new_docs"
    "data/graph_structures/vectorized_nodes/default"
    "data/graph_structures/vectorized_quadruplets/default"
    "logs"
)
for d in "${DIRS[@]}"; do
    mkdir -p "$d"
    ok "$d"
done

# ── 5. .env ───────────────────────────────────────────────────────────────────
echo -e "\n${BOLD}[5] Environment file (.env)${NC}"
if [[ ! -f ".env" ]]; then
    cp .env.example .env
    ok ".env created from .env.example"
    warn "Fill in .env before running the bot (see summary below)"
else
    ok ".env already exists"
fi

# Load .env for checks below
set -a
# shellcheck disable=SC1091
source .env 2>/dev/null || true
set +a

# ── 6. KG data check ──────────────────────────────────────────────────────────
echo -e "\n${BOLD}[6] KG data (full.txt)${NC}"
KG_DATA_PATH="${KG_DATA_PATH:-wikidata_big/kg}"
FULL_TXT="$KG_DATA_PATH/full.txt"
LINE_COUNT=0
if [[ -f "$FULL_TXT" ]]; then
    LINE_COUNT=$(wc -l < "$FULL_TXT" | tr -d ' ')
    ok "full.txt found — $LINE_COUNT lines ($FULL_TXT)"
else
    warn "full.txt not found at: $FULL_TXT"
    warn "Place your KG data there or set KG_DATA_PATH in .env"
fi

# ── 7. E5 model ───────────────────────────────────────────────────────────────
echo -e "\n${BOLD}[7] E5 embedder model${NC}"
E5_PATH="${FINETUNED_MODEL_PATH:-models/e5}"
if [[ -f "$E5_PATH/config.json" ]]; then
    ok "E5 model found: $E5_PATH"
else
    info "E5 model not found — downloading intfloat/multilingual-e5-small ..."
    mkdir -p "$E5_PATH"
    "$VENV_PYTHON" -c "
from sentence_transformers import SentenceTransformer
SentenceTransformer('intfloat/multilingual-e5-small').save('$E5_PATH')
" && ok "E5 model saved to $E5_PATH" || { err "E5 download failed"; exit 1; }
fi

# ── 8. TComplEx check ─────────────────────────────────────────────────────────
echo -e "\n${BOLD}[8] TComplEx temporal scorer (optional)${NC}"
TCOMPLEX_DATA="${TCOMPLEX_DATA_PATH:-wikidata_big/kg/tkbc_processed_data/wikidata_big}"
TCOMPLEX_CKPT="${TCOMPLEX_CHECKPOINT:-models/cronkgqa/tcomplex.ckpt}"
TCOMPLEX_OK=true
for f in train.pickle ent_id rel_id ts_id; do
    if [[ ! -f "$TCOMPLEX_DATA/$f" ]]; then
        warn "TComplEx: $TCOMPLEX_DATA/$f not found"
        TCOMPLEX_OK=false
    fi
done
if [[ ! -f "$TCOMPLEX_CKPT" ]]; then
    warn "TComplEx checkpoint not found: $TCOMPLEX_CKPT"
    TCOMPLEX_OK=false
fi
if $TCOMPLEX_OK; then
    ok "TComplEx data and checkpoint ready"
else
    info "Without TComplEx, temporal scoring is disabled (pipeline still works)"
fi

# ── 9. --build-kg ─────────────────────────────────────────────────────────────
if $BUILD_KG; then
    echo -e "\n${BOLD}[9] Building KG (extract → KuzuDB + ChromaDB + TComplEx)${NC}"
    INGEST_DIR="${INGEST_DIR:-extract/new_docs}"
    TKBC_DIR="${TCOMPLEX_DATA_PATH:-wikidata_big/kg/tkbc_processed_data/wikidata_big}"
    if [[ ! -d "$INGEST_DIR" ]]; then
        err "INGEST_DIR not found: $INGEST_DIR\n  Place documents (PDF/DOCX/PPTX/TXT) there or set INGEST_DIR in .env"
        exit 1
    fi
    AVAIL_KB=$(df -k "$SCRIPT_DIR" 2>/dev/null | awk 'NR==2{print $4}' || echo 9999999)
    if [[ "$AVAIL_KB" -lt 2097152 ]]; then
        warn "Low disk space: $(( AVAIL_KB / 1024 )) MB available. Building KG may require ≥2 GB."
    fi
    info "Running scripts/ingest_directory.py --dir $INGEST_DIR ..."
    "$VENV_PYTHON" scripts/ingest_directory.py \
        --dir "$INGEST_DIR" \
        --tkbc-dir "$TKBC_DIR" \
        --epochs "${RETRAIN_EPOCHS:-50}"
    ok "KG build complete"
fi

# ── 10. Status summary ────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}  Setup status${NC}"
echo -e "${BOLD}════════════════════════════════════════════════════════${NC}"
echo ""

# Hardware block
echo -e "${BOLD}Hardware:${NC}"
if [[ -n "$GPU_NAME" && "$GPU_NAME" != "Apple Silicon (MPS)" ]]; then
    echo -e "  GPU   : $GPU_NAME  (CUDA $CUDA_MAJOR)"
    [[ "$TORCH_CUDA" == "True" ]] \
        && echo -e "  torch : ${GREEN}CUDA enabled${NC}  ($TORCH_VER)" \
        || echo -e "  torch : ${YELLOW}CUDA not active in torch${NC}  ($TORCH_VER)"
elif [[ "$GPU_NAME" == "Apple Silicon (MPS)" ]]; then
    echo -e "  GPU   : Apple Silicon (MPS)"
    echo -e "  torch : $TORCH_VER (MPS)"
else
    echo -e "  GPU   : ${YELLOW}none detected — CPU mode${NC}"
    echo -e "  torch : $TORCH_VER (CPU)"
fi
TOTAL_RAM_MB=$(( $(awk '/^MemTotal:/{print $2}' /proc/meminfo 2>/dev/null || \
                  sysctl -n hw.memsize 2>/dev/null | awk '{print int($1/1024)}' || \
                  echo 0) / 1024 ))
[[ "$TOTAL_RAM_MB" -gt 0 ]] && echo -e "  RAM   : ${TOTAL_RAM_MB} MB total"
echo ""

# Data block
echo -e "${BOLD}Data:${NC}"
[[ -f "$FULL_TXT" ]] \
    && echo -e "  full.txt  : ${GREEN}OK${NC}  ($LINE_COUNT lines)" \
    || echo -e "  full.txt  : ${YELLOW}missing${NC}"
[[ -f "$E5_PATH/config.json" ]] \
    && echo -e "  E5 model  : ${GREEN}OK${NC}" \
    || echo -e "  E5 model  : ${YELLOW}missing${NC}"
$TCOMPLEX_OK \
    && echo -e "  TComplEx  : ${GREEN}OK${NC}" \
    || echo -e "  TComplEx  : ${YELLOW}optional — not found${NC}"
KUZU_DIR="${KUZU_PATH:-data/kuzu_db}"
[[ -d "$KUZU_DIR" && -n "$(ls -A "$KUZU_DIR" 2>/dev/null)" ]] \
    && echo -e "  KuzuDB    : ${GREEN}built${NC}" \
    || echo -e "  KuzuDB    : ${YELLOW}not built — run: bash setup.sh --build-kg${NC}"
echo ""

# Next steps
echo -e "${BOLD}Next steps:${NC}"
echo -e "  1. Fill in ${BOLD}.env${NC}  (TELEGRAM_BOT_TOKEN + LLM credentials)"
echo -e "  2a. Quick test : ${CYAN}bash run_inmemory.sh${NC}"
echo -e "  2b. Production : ${CYAN}cp /path/to/docs/* extract/new_docs/${NC}"
echo -e "                   ${CYAN}bash setup.sh --build-kg${NC}  then  ${CYAN}bash run_db.sh${NC}"
echo ""
echo -e "${BOLD}════════════════════════════════════════════════════════${NC}"
echo ""
