#!/bin/bash
# batch_rebuild.sh — Full reconstruction of KuzuDB and ChromaDB on server.
# This script wipes existing data and rebuilds from full.txt.

set -e

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="$PROJECT_DIR/.venv/bin/python"
ENV_FILE="$PROJECT_DIR/.env"

echo "===================================================="
echo "🚀 KG BATCH REBUILD STARTED!"
echo "===================================================="

# Check virtualenv
if [ ! -f "$PYTHON_BIN" ]; then
    echo "❌ [ERR] Virtualenv not found at $PYTHON_BIN"
    echo "Please run: python3.10 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Load .env
if [ -f "$ENV_FILE" ]; then
    echo "📌 Loading environment from $ENV_FILE ..."
    set -a
    source "$ENV_FILE"
    set +a
else
    echo "⚠️ [WARN] .env file not found. Using system environment."
fi

# Dry run / Help
if [[ "$1" == "--help" ]]; then
    echo "Usage: bash scripts/batch_rebuild.sh [--force] [--skip-chroma]"
    exit 0
fi

echo "📂 Project Directory: $PROJECT_DIR"
echo "🛠 Building KuzuDB + ChromaDB..."

# Run build script
# --force ensures old data is wiped if polluted
"$PYTHON_BIN" "$PROJECT_DIR/scripts/build_kg.py" "$@"

echo ""
echo "===================================================="
echo "✅ REBUILD COMPLETED SUCCESSFULLY!"
echo "===================================================="
echo "Next steps:"
echo "1. Verify data with: $PYTHON_BIN scripts/check_chroma_counts.py"
echo "2. Restart bot: sudo systemctl restart personal-ai-bot (if using systemd)"
echo "3. Update TComplEx: $PYTHON_BIN scripts/retrain_tcomplex.py"
echo "===================================================="
