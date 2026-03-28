#!/bin/bash
# run_db.sh — Production launch: KuzuDB + ChromaDB
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
ok()   { echo -e "  ${GREEN}[OK]${NC}  $*"; }
warn() { echo -e "  ${YELLOW}[WARN]${NC} $*"; }
err()  { echo -e "  ${RED}[ERR]${NC}  $*"; exit 1; }

echo -e "\n${BOLD}====  run_db.sh pre-launch checks  ====${NC}\n"

# 1. .venv
[[ -f ".venv/bin/python" ]] || err ".venv not found. Run: bash setup.sh"

# ── Device banner ──────────────────────────────────────────────────────────────
TORCH_CUDA=$(".venv/bin/python" -c "import torch; print(torch.cuda.is_available())" 2>/dev/null || echo "False")
TORCH_VER=$(".venv/bin/python"  -c "import torch; print(torch.__version__)"         2>/dev/null || echo "?")
if [[ "$TORCH_CUDA" == "True" ]]; then
    GPU_DEV=$(".venv/bin/python" -c "import torch; print(torch.cuda.get_device_name(0))" 2>/dev/null || echo "?")
    VRAM=$(".venv/bin/python" -c "import torch; print(torch.cuda.get_device_properties(0).total_memory // 1024**3)" 2>/dev/null || echo "?")
    echo -e "  ${GREEN}${BOLD}[GPU]${NC}  ${GPU_DEV}  ${VRAM} GB VRAM  torch ${TORCH_VER}"
elif [[ "$(uname)" == "Darwin" && "$(uname -m)" == "arm64" ]]; then
    echo -e "  ${GREEN}${BOLD}[GPU]${NC}  Apple Silicon (MPS)  torch ${TORCH_VER}"
else
    echo -e "  ${RED}${BOLD}[CPU]${NC}  No GPU detected — torch ${TORCH_VER}  (embeddings will be slow)"
fi
echo ""

# 2. .env
[[ -f ".env" ]] || err ".env not found. Run: bash setup.sh"
set -a; source .env 2>/dev/null; set +a

# 3. Telegram token
[[ -z "${TELEGRAM_BOT_TOKEN:-}" || "$TELEGRAM_BOT_TOKEN" == "your_telegram_bot_token_here" ]] \
    && err "TELEGRAM_BOT_TOKEN not set in .env"
ok "TELEGRAM_BOT_TOKEN set"

# 4. LLM backend credentials
LLM="${LLM_BACKEND:-deepseek}"
case "$LLM" in
    yandexgpt)
        [[ -z "${YANDEX_API_KEY:-}" ]]       && err "YANDEX_API_KEY not set"
        [[ -z "${YANDEX_FOLDER_ID:-}" ]]     && err "YANDEX_FOLDER_ID not set"
        ok "LLM: YandexGPT credentials OK" ;;
    deepseek)
        [[ -z "${DEEPSEEK_API_KEY:-}" ]]     && err "DEEPSEEK_API_KEY not set"
        ok "LLM: DeepSeek API key OK" ;;
    gigachat)
        [[ -z "${GIGACHAT_CREDENTIALS:-}" ]] && err "GIGACHAT_CREDENTIALS not set"
        ok "LLM: GigaChat credentials OK" ;;
    openai|chatgpt)
        [[ -z "${OPENAI_API_KEY:-}" ]]       && err "OPENAI_API_KEY not set"
        ok "LLM: OpenAI API key OK" ;;
    qwen)
        [[ -z "${QWEN_API_KEY:-}" ]]         && err "QWEN_API_KEY not set"
        ok "LLM: Qwen API key OK" ;;
    ollama)
        ok "LLM: Ollama (no API key required)" ;;
    *) warn "Unknown LLM_BACKEND: $LLM" ;;
esac

# 5. E5 model
E5_PATH="${FINETUNED_MODEL_PATH:-models/wikidata_finetuned_remote/wikidata_finetuned}"
[[ -f "$E5_PATH/config.json" ]] \
    || err "E5 model not found at: $E5_PATH\n  Run: source .venv/bin/activate && python -c \"from sentence_transformers import SentenceTransformer; SentenceTransformer('intfloat/multilingual-e5-small').save('$E5_PATH')\""
ok "E5 model: $E5_PATH"

# 6. KuzuDB populated
KUZU_PATH="${KUZU_PATH:-data/kuzu_db}"
if [[ ! -d "$KUZU_PATH" ]] || [[ -z "$(ls -A "$KUZU_PATH" 2>/dev/null)" ]]; then
    err "KuzuDB not built at: $KUZU_PATH\n  Run: bash setup.sh --build-kg"
fi
ok "KuzuDB: $KUZU_PATH"

# 7. ChromaDB directories
NODES_PATH="${CHROMA_NODES_PATH:-data/graph_structures/vectorized_nodes/default}"
QUADS_PATH="${CHROMA_QUADS_PATH:-data/graph_structures/vectorized_quadruplets/default}"
[[ -d "$NODES_PATH" ]] || err "ChromaDB nodes path missing: $NODES_PATH\n  Run: bash setup.sh --build-kg"
[[ -d "$QUADS_PATH" ]] || err "ChromaDB quads path missing: $QUADS_PATH\n  Run: bash setup.sh --build-kg"
ok "ChromaDB paths: OK"

# 8. TComplEx (optional, warn only)
TCOMPLEX_CKPT="${TCOMPLEX_CHECKPOINT:-models/cronkgqa/tcomplex.ckpt}"
if [[ ! -f "$TCOMPLEX_CKPT" ]]; then
    warn "TComplEx checkpoint not found: $TCOMPLEX_CKPT (temporal scoring disabled)"
else
    ok "TComplEx checkpoint: $TCOMPLEX_CKPT"
fi

# 9. Key package imports
for mod in kuzu chromadb aiogram natasha; do
    ".venv/bin/python" -c "import $mod" 2>/dev/null \
        && ok "package: $mod" \
        || err "package '$mod' not importable — run: bash setup.sh"
done

# ── Status block ──────────────────────────────────────────────────────────────
TCOMPLEX_STATUS="disabled"
[[ -f "$TCOMPLEX_CKPT" ]] && TCOMPLEX_STATUS="loaded"

echo ""
echo -e "${BOLD}════════════════════════════════════════  STATUS  ═════${NC}"
echo -e "  Mode    : ${GREEN}production (KuzuDB + ChromaDB)${NC}"
echo -e "  LLM     : ${LLM}"
echo -e "  torch   : ${TORCH_VER}  CUDA=$([ "$TORCH_CUDA" == "True" ] && echo yes || echo no)"
echo -e "  KuzuDB  : ${KUZU_PATH}"
echo -e "  TComplEx: ${TCOMPLEX_STATUS}"
echo -e "${BOLD}════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}Starting bot...${NC}"
export USE_INMEMORY=false
export GRAPH_BACKEND=kuzu
exec ".venv/bin/python" bot.py
