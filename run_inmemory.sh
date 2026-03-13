#!/bin/bash
# run_inmemory.sh — Quick start: in-memory mode (data from full.txt)
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'; BOLD='\033[1m'; NC='\033[0m'
ok()   { echo -e "  ${GREEN}[OK]${NC}  $*"; }
warn() { echo -e "  ${YELLOW}[WARN]${NC} $*"; }
err()  { echo -e "  ${RED}[ERR]${NC}  $*"; exit 1; }

echo -e "\n${BOLD}====  run_inmemory.sh pre-launch checks  ====${NC}\n"

# 1. .venv
[[ -f ".venv/bin/python" ]] || err ".venv not found. Run: bash setup.sh"

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
        [[ -z "${YANDEX_API_KEY:-}" ]]    && err "YANDEX_API_KEY not set"
        [[ -z "${YANDEX_FOLDER_ID:-}" ]]  && err "YANDEX_FOLDER_ID not set"
        ok "LLM: YandexGPT credentials OK" ;;
    deepseek)
        [[ -z "${DEEPSEEK_API_KEY:-}" ]]  && err "DEEPSEEK_API_KEY not set"
        ok "LLM: DeepSeek API key OK" ;;
    gigachat)
        [[ -z "${GIGACHAT_CREDENTIALS:-}" ]] && err "GIGACHAT_CREDENTIALS not set"
        ok "LLM: GigaChat credentials OK" ;;
    openai|chatgpt)
        [[ -z "${OPENAI_API_KEY:-}" ]]    && err "OPENAI_API_KEY not set"
        ok "LLM: OpenAI API key OK" ;;
    qwen)
        [[ -z "${QWEN_API_KEY:-}" ]]      && err "QWEN_API_KEY not set"
        ok "LLM: Qwen API key OK" ;;
    ollama) ok "LLM: Ollama (no API key required)" ;;
    *) warn "Unknown LLM_BACKEND: $LLM" ;;
esac

# 5. KG data (full.txt) — required for in-memory mode
KG_DATA="${KG_DATA_PATH:-wikidata_big/kg}"
[[ -f "$KG_DATA/full.txt" ]] \
    || err "full.txt not found at: $KG_DATA/full.txt\n  Set KG_DATA_PATH in .env or place data there."
LINE_COUNT=$(wc -l < "$KG_DATA/full.txt" | tr -d ' ')
ok "full.txt: $LINE_COUNT lines ($KG_DATA/full.txt)"

# 6. E5 model (optional — falls back to HuggingFace download)
E5_PATH="${FINETUNED_MODEL_PATH:-models/wikidata_finetuned_remote/wikidata_finetuned}"
if [[ -f "$E5_PATH/config.json" ]]; then
    ok "E5 model: $E5_PATH"
else
    warn "E5 model not found locally at $E5_PATH — will download intfloat/multilingual-e5-small from HuggingFace"
fi

# 7. TComplEx (optional, warn only)
TCOMPLEX_CKPT="${TCOMPLEX_CHECKPOINT:-models/cronkgqa/tcomplex.ckpt}"
if [[ ! -f "$TCOMPLEX_CKPT" ]]; then
    warn "TComplEx checkpoint not found: $TCOMPLEX_CKPT (temporal scoring disabled)"
else
    ok "TComplEx checkpoint: $TCOMPLEX_CKPT"
fi

echo -e "\n${GREEN}All checks passed. Starting bot (in-memory mode)...${NC}\n"
export USE_INMEMORY=true
exec ".venv/bin/python" bot.py
