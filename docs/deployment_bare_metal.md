# Bare-Metal Deployment Guide

This guide covers running the Personal AI Knowledge Graph system directly on the host (no Docker).
For Docker-based deployment see [deployment.md](deployment.md).

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | **3.10.x** | Strictly 3.10 — `transformers==4.40.2` + `sentence-transformers==2.7.0` pinned |
| pip | ≥23 | `pip install --upgrade pip` |
| git | any | |
| Neo4j | 5.x Community | **Only for** Mode C (`GRAPH_BACKEND=neo4j`) |
| Ollama | latest | **Only for** `LLM_BACKEND=ollama` |
| ≥8 GB RAM | — | For E5 encoding of large KG in in-memory mode |
| ≥4 GB disk | — | For models + KuzuDB / ChromaDB data |

---

## Three Deployment Modes

| Mode | Graph DB | Vector DB | Best for |
|---|---|---|---|
| **A: In-Memory** | Built-in list | Built-in E5 | Quick demo, no server deps |
| **B: KuzuDB** | KuzuDB (embedded) | ChromaDB (embedded) | Serverless production |
| **C: Neo4j** | Neo4j 5.x | ChromaDB (embedded) | Full production |

ChromaDB runs **embedded** (file-based) in all modes — no ChromaDB server needed.

---

## Step 1 — Clone & Virtualenv

```bash
git clone <repo-url> personal-ai
cd personal-ai

# Python 3.10 virtualenv
python3.10 -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows

pip install --upgrade pip
pip install -r requirements.txt
```

> **Apple Silicon (M1/M2/M3):** PyTorch MPS is auto-selected, falls back to CPU. No extra setup needed.

> **CUDA GPU:** Replace the default CPU-safe torch with a CUDA build if needed:
> ```bash
> pip install torch --index-url https://download.pytorch.org/whl/cu121
> ```

---

## Step 2 — Environment Configuration

```bash
cp .env.example .env
```

Edit `.env`. Required fields depend on the chosen mode and LLM backend.

### Always required

```env
TELEGRAM_BOT_TOKEN=1234567890:ABCDEFabcdef...   # from @BotFather
LLM_BACKEND=deepseek    # or: yandexgpt | gigachat | openai | qwen | ollama
```

### LLM credentials — choose one block

```env
# DeepSeek
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_MODEL=deepseek-chat

# YandexGPT
YANDEX_API_KEY=...
YANDEX_FOLDER_ID=...
YANDEX_MODEL=yandexgpt

# GigaChat (Sber)
GIGACHAT_CREDENTIALS=...
GIGACHAT_MODEL=GigaChat

# OpenAI / compatible
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=                 # leave blank for api.openai.com

# Qwen (DashScope)
QWEN_API_KEY=...
QWEN_MODEL=qwen-plus

# Ollama (self-hosted)
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

### Mode A: In-Memory (default — no DB needed)

```env
USE_INMEMORY=true
KG_DATA_PATH=/absolute/path/to/wikidata_big/kg
MODEL_PATH=/absolute/path/to/models/wikidata_finetuned_remote/wikidata_finetuned
```

`KG_DATA_PATH` must contain `full.txt`, `wd_id2entity_text.txt`, and `wd_id2relation_text.txt`.

### Mode B: KuzuDB (embedded, no server)

```env
USE_INMEMORY=false
GRAPH_BACKEND=kuzu
KUZU_PATH=/absolute/path/to/data/kuzu_db

CHROMA_NODES_PATH=/absolute/path/to/data/graph_structures/vectorized_nodes/default
CHROMA_QUADS_PATH=/absolute/path/to/data/graph_structures/vectorized_quadruplets/default

FINETUNED_MODEL_PATH=/absolute/path/to/models/wikidata_finetuned_remote/wikidata_finetuned
```

All paths are created automatically on first run.

### Mode C: Neo4j (full production)

```env
USE_INMEMORY=false
GRAPH_BACKEND=neo4j
NEO4J_HOST=localhost
NEO4J_PORT=7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_secure_password
NEO4J_DB=neo4j

CHROMA_NODES_PATH=/absolute/path/to/data/graph_structures/vectorized_nodes/default
CHROMA_QUADS_PATH=/absolute/path/to/data/graph_structures/vectorized_quadruplets/default

FINETUNED_MODEL_PATH=/absolute/path/to/models/wikidata_finetuned_remote/wikidata_finetuned

# Optional — TComplEx temporal scoring:
TCOMPLEX_CHECKPOINT=/absolute/path/to/models/cronkgqa/tcomplex.ckpt
TCOMPLEX_DATA_PATH=/absolute/path/to/wikidata_big/kg/tkbc_processed_data/wikidata_big
```

---

## Step 3 — Neo4j Setup (Mode C only)

### macOS (Homebrew)

```bash
brew install neo4j
neo4j-admin dbms set-initial-password your_secure_password
brew services start neo4j
```

### Linux (Debian/Ubuntu)

```bash
wget -O - https://debian.neo4j.com/neotechnology.gpg.key | sudo apt-key add -
echo 'deb https://debian.neo4j.com stable 5' | sudo tee /etc/apt/sources.list.d/neo4j.list
sudo apt update && sudo apt install neo4j
sudo neo4j-admin dbms set-initial-password your_secure_password
sudo systemctl enable --now neo4j
```

### Create fulltext index (required for entity resolution)

Run in Neo4j Browser or `cypher-shell`:

```cypher
CREATE FULLTEXT INDEX entity_name_aliases IF NOT EXISTS
  FOR (n:Entity) ON EACH [n.name, n.aliases];
```

### Verify

```bash
cypher-shell -u neo4j -p your_secure_password "RETURN 1"
```

---

## Step 4 — Ollama Setup (`LLM_BACKEND=ollama` only)

### macOS

```bash
brew install ollama
ollama serve &
ollama pull llama3.2
```

### Linux

```bash
curl -fsSL https://ollama.com/install.sh | sh
sudo systemctl enable --now ollama
ollama pull llama3.2
```

---

## Step 5 — Models Setup

Models are not in git. Two options:

### Option A: Download base model from HuggingFace

```bash
mkdir -p models/wikidata_finetuned_remote
python -c "
from sentence_transformers import SentenceTransformer
SentenceTransformer('intfloat/multilingual-e5-small').save(
    'models/wikidata_finetuned_remote/wikidata_finetuned'
)
"
```

### Option B: Copy from an existing deployment

```bash
scp -r user@server:/path/to/models ./models
```

---

## Step 6 — Run

```bash
source .venv/bin/activate

# Telegram bot (primary):
python bot.py

# Streamlit web UI (secondary, in a separate terminal):
streamlit run app.py --server.port 8501
```

Expected startup log lines:
- Mode A: `Starting SimpleInMemoryEngine` → `Embeddings ready: shape=...`
- Mode B: `Using KuzuDB at ...`
- Mode C: `Connected to Neo4j`

---

## Step 7 — Process Management

### Linux — systemd

Create `/etc/systemd/system/personal-ai-bot.service`:

```ini
[Unit]
Description=Personal AI Knowledge Graph Bot
After=network.target neo4j.service
Wants=neo4j.service

[Service]
Type=simple
User=YOUR_USERNAME
Group=YOUR_USERNAME
WorkingDirectory=/absolute/path/to/personal-ai
EnvironmentFile=/absolute/path/to/personal-ai/.env
ExecStart=/absolute/path/to/personal-ai/.venv/bin/python bot.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=personal-ai-bot

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable personal-ai-bot
sudo systemctl start personal-ai-bot
sudo journalctl -u personal-ai-bot -f   # tail logs
```

### macOS — launchd

Because launchd does not natively read `.env` files, use a wrapper script.

Create `start_bot.sh` in the project root:

```bash
#!/bin/bash
set -a
source /absolute/path/to/personal-ai/.env
set +a
exec /absolute/path/to/personal-ai/.venv/bin/python /absolute/path/to/personal-ai/bot.py
```

```bash
chmod +x start_bot.sh
```

Create `~/Library/LaunchAgents/com.personal-ai.bot.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.personal-ai.bot</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>/absolute/path/to/personal-ai/start_bot.sh</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/absolute/path/to/personal-ai</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/personal-ai-bot.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/personal-ai-bot-err.log</string>
</dict>
</plist>
```

```bash
launchctl load ~/Library/LaunchAgents/com.personal-ai.bot.plist
launchctl start com.personal-ai.bot
tail -f /tmp/personal-ai-bot.log
```

---

## Step 8 — Incremental Data Updates

```bash
source .venv/bin/activate

# Add new facts from JSON:
python scripts/incremental_update.py --input data/new_facts.json

# Ingest via bot: upload PDF/DOCX/PPTX/TXT → /ingest runs automatically

# Retrain TComplEx after significant data additions:
python scripts/retrain_tcomplex.py
```

---

## Step 9 — Verification Checklist

```bash
# 1. Bot health: send /status → shows mode, quadruplets count, LLM name, device

# 2. Neo4j connectivity (Mode C):
python scripts/check_neo4j_status.py

# 3. ChromaDB counts:
python scripts/check_chroma_counts.py

# 4. Quick QA: send /ask Who was the president of France in 2010?

# 5. Ingest test: upload a .txt file → check /status shows increased fact count
```
