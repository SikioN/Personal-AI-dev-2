#!/bin/bash
# setup.sh — Bootstrap for Personal-AI KG Navigator
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

echo -e "\n${BOLD}====  Personal-AI setup.sh  ====${NC}\n"

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
info "pip install -r requirements.txt ..."
"$VENV_PIP" install --upgrade pip -q
"$VENV_PIP" install -r requirements.txt -q
ok "Dependencies installed"

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
if [[ -f "$FULL_TXT" ]]; then
    LINE_COUNT=$(wc -l < "$FULL_TXT" | tr -d ' ')
    ok "full.txt found — $LINE_COUNT lines ($FULL_TXT)"
else
    warn "full.txt not found at: $FULL_TXT"
    warn "Place your KG data there or set KG_DATA_PATH in .env"
fi

# ── 7. E5 model check ─────────────────────────────────────────────────────────
echo -e "\n${BOLD}[7] E5 embedder model${NC}"
E5_PATH="${FINETUNED_MODEL_PATH:-models/wikidata_finetuned_remote/wikidata_finetuned}"
if [[ -f "$E5_PATH/config.json" ]]; then
    ok "E5 model found: $E5_PATH"
else
    warn "E5 model not found at: $E5_PATH"
    info "Download with:"
    echo "    source .venv/bin/activate"
    echo "    python -c \""
    echo "    from sentence_transformers import SentenceTransformer"
    echo "    SentenceTransformer('intfloat/multilingual-e5-small').save('$E5_PATH')"
    echo "    \""
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
    info "Without TComplEx, the pipeline runs 6 stages (no temporal scoring)"
fi

# ── 9. --build-kg ─────────────────────────────────────────────────────────────
if $BUILD_KG; then
    echo -e "\n${BOLD}[9] Building KuzuDB + ChromaDB${NC}"
    if [[ ! -f "$FULL_TXT" ]]; then
        err "Cannot build KG: full.txt not found at $FULL_TXT"
        exit 1
    fi
    info "Running scripts/build_kg.py ..."
    "$VENV_PYTHON" scripts/build_kg.py
    ok "KuzuDB + ChromaDB built"
fi

# ── 10. Summary ───────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}  Setup complete. Next steps:${NC}"
echo -e "${BOLD}════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${CYAN}1. Fill in .env (required fields):${NC}"
echo ""
echo "   TELEGRAM_BOT_TOKEN=<your token>"
echo ""
echo "   LLM_BACKEND=<backend>   # choose one:"
echo ""
echo "   # DeepSeek (recommended):"
echo "   DEEPSEEK_API_KEY=sk-..."
echo ""
echo "   # YandexGPT:"
echo "   YANDEX_API_KEY=...   YANDEX_FOLDER_ID=...   YANDEX_MODEL=yandexgpt"
echo ""
echo "   # GigaChat:"
echo "   GIGACHAT_CREDENTIALS=..."
echo ""
echo "   # OpenAI:"
echo "   OPENAI_API_KEY=sk-..."
echo ""
echo "   # Qwen:"
echo "   QWEN_API_KEY=...   QWEN_MODEL=qwen-plus"
echo ""
echo "   # Ollama (local):"
echo "   OLLAMA_URL=http://localhost:11434   OLLAMA_MODEL=llama3.2"
echo ""
echo -e "${CYAN}2. Start the bot:${NC}"
echo ""
echo "   # Quick start (no DB, data loaded from full.txt into RAM):"
echo "   bash run_inmemory.sh"
echo ""
echo "   # Production (KuzuDB + ChromaDB, requires --build-kg first):"
echo "   bash setup.sh --build-kg    # one-time build"
echo "   bash run_db.sh"
echo ""
echo -e "${BOLD}════════════════════════════════════════════════════════${NC}"
echo ""
