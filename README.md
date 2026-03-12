# Personal AI — Knowledge Graph QA Navigator

[![Python 3.10](https://img.shields.io/badge/Python-3.10-blue.svg)](https://www.python.org/downloads/release/python-3100/)
[![License MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![KuzuDB](https://img.shields.io/badge/Graph_DB-KuzuDB-orange.svg)](https://kuzudb.com/)
[![ChromaDB](https://img.shields.io/badge/Vector_DB-ChromaDB-purple.svg)](https://www.trychroma.com/)
[![TComplEx](https://img.shields.io/badge/Temporal_Scorer-TComplEx-red.svg)](https://arxiv.org/abs/2005.07782)

Production-система вопросно-ответного поиска поверх графов знаний. Реализует гибридную архитектуру Retrieval-Augmented Generation (RAG) с темпоральным ранжированием: структурный поиск по графу совмещается с нейросетевым семантическим поиском и математической оценкой правдоподобия фактов через тензорную факторизацию TComplEx.

---

## Содержание

- [Архитектура конвейера](#архитектура-конвейера)
- [Структура проекта](#структура-проекта)
- [Режимы работы](#режимы-работы)
- [Развёртывание шаг за шагом](#развёртывание-шаг-за-шагом)
  - [1. Клонирование и окружение](#1-клонирование-и-окружение)
  - [2. Модели: E5 и TComplEx](#2-модели-e5-и-tcomplex)
  - [3. Данные: формат и расположение](#3-данные-формат-и-расположение)
  - [4. Конфигурация .env](#4-конфигурация-env)
  - [5. Первичная сборка KG: KuzuDB + ChromaDB](#5-первичная-сборка-kg-kuzudb--chromadb)
  - [6. Запуск бота](#6-запуск-бота)
- [Инкрементальное обновление](#инкрементальное-обновление)
- [Переобучение TComplEx](#переобучение-tcomplex)
- [Команды Telegram-бота](#команды-telegram-бота)
- [Ключевые классы](#ключевые-классы)

---

## Архитектура конвейера

Ядро системы — класс [`QAEngine`](src/pipelines/qa/qa_engine.py), реализующий 7-стадийный конвейер:

```
Запрос пользователя
        |
        v
+-----------------------------------------------------------------------+
|  Стадия 1 — Extraction  [src/pipelines/qa/stages/extraction.py]      |
|                                                                       |
|  LLM анализирует запрос: извлекает именованные сущности, определяет  |
|  тип вопроса (simple_time, before_after, time_join, first_last)       |
|  и временные рамки.                                                   |
+-----------------------------------------------------------------------+
        |
        v
+-----------------------------------------------------------------------+
|  Стадия 2 — Entity Resolution  [src/pipelines/ingestion/             |
|                                  entity_resolver.py]                  |
|                                                                       |
|  5-уровневый каскад:                                                  |
|  L1: exact_id  ->  L2: exact graph lookup  ->  L2.5: rapidfuzz >= 90 |
|  ->  L3: vector < 0.25  ->  L4: LLM  ->  L5: новый LOCAL_ id         |
+-----------------------------------------------------------------------+
        |
        v
+-----------------------------------------------------------------------+
|  Стадия 3 — Graph Retrieval  [src/pipelines/qa/stages/retrieval.py]  |
|                                                                       |
|  Соседи 1-го порядка вокруг разрешённых сущностей.                   |
|  Бэкенды: KuzuDB (рекомендуется) / Neo4j / in-memory.                |
+-----------------------------------------------------------------------+
        |
        v
+-----------------------------------------------------------------------+
|  Стадия 4 — Vector Retrieval  [src/pipelines/qa/stages/retrieval.py] |
|                                                                       |
|  ChromaDB + finetuned multilingual-e5-small.                         |
|  Семантический поиск преодолевает лексические разрывы:               |
|  "president" ~ "head of state", "СССР" ~ "Soviet Union".             |
+-----------------------------------------------------------------------+
        |  граф + вектор (объединение)
        v
+-----------------------------------------------------------------------+
|  Стадия 5 — Scoring (TComplEx)  [src/pipelines/qa/stages/scoring.py] |
|                                                                       |
|  Тензорная факторизация оценивает математическое правдоподобие        |
|  каждого факта. Темпоральный фильтр отсекает факты вне диапазона      |
|  запроса. Alpha-вес адаптируется по типу вопроса.                    |
+-----------------------------------------------------------------------+
        |
        v
+-----------------------------------------------------------------------+
|  Стадия 6 — Selection (Confidence Gap)                               |
|                               [src/pipelines/qa/stages/scoring.py]   |
|                                                                       |
|  Оставляет только факты, чья итоговая оценка значимо превышает       |
|  фоновый шум. Порог — разрыв (gap) относительно медианы.             |
+-----------------------------------------------------------------------+
        |
        v
+-----------------------------------------------------------------------+
|  Стадия 7 — Generation (LLM)  [src/pipelines/qa/stages/generation.py]|
|                                                                       |
|  LLM формирует ответ на естественном языке строго по отобранным      |
|  фактам. Поддержка 6 бэкендов: DeepSeek, YandexGPT, GigaChat,       |
|  OpenAI, Qwen, Ollama.                                                |
+-----------------------------------------------------------------------+
        |
        v
    Ответ пользователю
```

---

## Структура проекта

```
personal-ai/
|
+-- bot.py                                  # Точка входа — Telegram-бот (aiogram)
|
+-- scripts/
|   +-- ingest_full.py                      # Первичная загрузка KG из JSONL
|   +-- incremental_update.py               # Добавление новых фактов (JSON)
|   +-- retrain_tcomplex.py                 # Переобучение темпорального скорера
|   +-- verify_ingestion.py                 # Проверка состояния графа
|   +-- check_chroma_counts.py              # Проверка ChromaDB
|   +-- qa_test_subset.py                   # Быстрое тестирование QA
|   +-- merge_out_json.py                   # Объединение выгрузок
|   `-- inspect_chroma.py                   # Инспекция ChromaDB
|
+-- src/
|   +-- config/
|   |   `-- qa_config.py                    # QAConfig — все гиперпараметры
|   |
|   +-- pipelines/
|   |   +-- qa/
|   |   |   +-- qa_engine.py                # QAEngine — 7-стадийный оркестратор
|   |   |   +-- benchmark.py                # BenchmarkRunner
|   |   |   `-- stages/
|   |   |       +-- extraction.py           # ExtractionStage
|   |   |       +-- retrieval.py            # HybridRetriever
|   |   |       +-- scoring.py              # ScoringStage + Confidence Gap
|   |   |       `-- generation.py           # GenerationStage
|   |   `-- ingestion/
|   |       +-- temporal_kg_ingester.py     # TemporalKGIngester
|   |       +-- entity_resolver.py          # EntityResolver (5 уровней)
|   |       `-- doc_ingestion_service.py    # Ингестия документов через бот
|   |
|   +-- kg_model/
|   |   +-- knowledge_graph_model.py        # KnowledgeGraphModel — контроллер БД
|   |   `-- temporal/
|   |       `-- temporal_model.py           # TemporalScorer (TComplEx)
|   |
|   +-- db_drivers/
|   |   +-- graph_driver/connectors/
|   |   |   +-- KuzuConnector.py            # KuzuDB (рекомендуется)
|   |   |   `-- Neo4jConnector.py           # Neo4j (опционально)
|   |   `-- vector_driver/                  # ChromaDB (встроенный режим)
|   |
|   +-- bot/
|   |   +-- engine_loader.py                # Singleton-фабрика движка
|   |   +-- handlers.py                     # Обработчики команд бота
|   |   +-- formatters.py                   # Форматирование ответов
|   |   `-- graph_renderer.py               # PNG-рендер подграфов
|   |
|   +-- llm/                                # 6 LLM-клиентов
|   `-- utils/
|       +-- kg_utils.py                     # KGEntityMapper
|       +-- wikidata_utils.py               # WikidataMapper
|       `-- kg_navigator.py                 # KGNavigator
|
+-- models/                                 # Модели (не в git, нужно создать)
|   +-- wikidata_finetuned_remote/
|   |   `-- wikidata_finetuned/             # E5-small finetuned
|   `-- cronkgqa/
|       `-- tcomplex.ckpt                   # TComplEx чекпоинт
|
+-- data/                                   # Данные (не в git, создаются автоматически)
|   +-- kuzu_db/                            # KuzuDB файлы
|   `-- graph_structures/
|       +-- vectorized_nodes/default/       # ChromaDB узлы
|       `-- vectorized_quadruplets/default/ # ChromaDB квадруплеты
|
+-- wikidata_big/kg/                        # Сырые данные KG (не в git)
|   +-- full.txt
|   +-- wd_id2entity_text.txt
|   +-- wd_id2relation_text.txt
|   `-- tkbc_processed_data/wikidata_big/
|       +-- train.pickle
|       +-- ent_id
|       +-- rel_id
|       `-- ts_id
|
+-- .env.example
`-- requirements.txt
```

---

## Режимы работы

| Режим | Переменные | Граф | Вектор | Лучший выбор |
|---|---|---|---|---|
| **In-Memory** | `USE_INMEMORY=true` | Встроенный список | Встроенный E5 | Демо, без внешних сервисов |
| **KuzuDB** | `USE_INMEMORY=false`<br>`GRAPH_BACKEND=kuzu` | KuzuDB (встроенный) | ChromaDB (файловый) | **Production без сервера** |
| **Neo4j** | `USE_INMEMORY=false`<br>`GRAPH_BACKEND=neo4j` | Neo4j 5.x | ChromaDB (файловый) | Кластер, многопользовательский доступ |

**Рекомендуется режим KuzuDB** — не требует отдельного сервера, данные хранятся локально в `data/kuzu_db/`, ChromaDB запускается встроенно по файловому пути. Никакой инфраструктуры, кроме Python-процесса, не нужно.

---

## Развёртывание шаг за шагом

### 1. Клонирование и окружение

```bash
git clone <repo-url> personal-ai
cd personal-ai

# Python строго 3.10 (pinned transformers==4.40.2 + sentence-transformers==2.7.0)
python3.10 -m venv .venv
source .venv/bin/activate          # Linux / macOS
# .venv\Scripts\activate           # Windows

pip install --upgrade pip
pip install -r requirements.txt
```

> **Apple Silicon (M1/M2/M3):** PyTorch автоматически выбирает MPS, при отсутствии — CPU. Дополнительная настройка не требуется.
>
> **CUDA GPU:** Замените torch на CUDA-сборку при необходимости:
> ```bash
> pip install torch --index-url https://download.pytorch.org/whl/cu121
> ```

---

### 2. Модели: E5 и TComplEx

Модели не входят в репозиторий — нужно создать директории и поместить файлы вручную.

```bash
mkdir -p models/wikidata_finetuned_remote/wikidata_finetuned
mkdir -p models/cronkgqa
```

#### E5-small (эмбеддер, обязательно)

**Вариант A — скачать базовую модель с HuggingFace:**
```bash
source .venv/bin/activate
python -c "
from sentence_transformers import SentenceTransformer
SentenceTransformer('intfloat/multilingual-e5-small').save(
    'models/wikidata_finetuned_remote/wikidata_finetuned'
)
print('E5 model saved.')
"
```

**Вариант B — скопировать finetuned-версию с сервера:**
```bash
scp -r user@server:/path/to/wikidata_finetuned \
    models/wikidata_finetuned_remote/wikidata_finetuned
```

После загрузки в директории должны быть файлы:
```
models/wikidata_finetuned_remote/wikidata_finetuned/
+-- config.json
+-- tokenizer_config.json
+-- tokenizer.json
`-- pytorch_model.bin   (или model.safetensors)
```

#### TComplEx (темпоральный скорер, опционально)

Чекпоинт `.ckpt` обязателен только если нужно темпоральное ранжирование (стадия 5). Без него система работает на 6 стадиях.

Получить чекпоинт:
- Скопировать с другого развёртывания: `scp user@server:/path/to/tcomplex.ckpt models/cronkgqa/`
- Обучить с нуля через `kaggle_job/` (полный цикл tkbc на Kaggle)

```
models/cronkgqa/
`-- tcomplex.ckpt     <-- этот файл
```

---

### 3. Данные: формат и расположение

#### Сырые данные KG (Wikidata или собственный датасет)

```
wikidata_big/kg/
+-- full.txt                          # Квадруплеты: S\tR\tO\tts\tte
+-- wd_id2entity_text.txt             # Q-ID -> текстовое название
+-- wd_id2relation_text.txt           # P-ID -> текстовое название
`-- tkbc_processed_data/wikidata_big/ # Pickle-файлы для TComplEx
    +-- train.pickle
    +-- ent_id
    +-- rel_id
    `-- ts_id
```

Формат строки `full.txt` (разделитель — табуляция):
```
Q76	P26	Q13133	+1961-01-00	+1975-01-00
Q76	P106	Q82955	+0000-01-01	+9999-01-01
```

Если у вас данные без временных меток, используйте `+0000-01-01` / `+9999-01-01` как заглушки.

#### Формат входного JSON для ингестии новых фактов

```json
[
  {
    "subject": {"name": "Владимир Набоков", "id": null},
    "relation": "spouse",
    "object":   {"name": "Вера Набокова",   "id": null},
    "time_start": "1925",
    "time_end":   null
  },
  {
    "subject": {"name": "Набоков",    "id": "Q2152"},
    "relation": "educated_at",
    "object":   {"name": "Кембридж",  "id": "Q35794"},
    "time_start": "1919",
    "time_end":   "1922"
  }
]
```

- `id` — указать явно (`"Q2152"`) или `null` — система сгенерирует `LOCAL_` идентификатор
- `relation` — рекомендуется `snake_case`
- `time_end: null` — означает "по настоящее время"

---

### 4. Конфигурация .env

```bash
cp .env.example .env
```

Откройте `.env` и заполните нужные блоки.

#### Всегда обязательно

```ini
TELEGRAM_BOT_TOKEN=1234567890:ABCDEFabcdef...

LLM_BACKEND=deepseek   # deepseek | yandexgpt | gigachat | openai | qwen | ollama
```

#### LLM-бэкенд — выберите один блок

```ini
# DeepSeek
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_MODEL=deepseek-chat

# YandexGPT
YANDEX_API_KEY=...
YANDEX_FOLDER_ID=...
YANDEX_MODEL=yandexgpt

# GigaChat (Сбер)
GIGACHAT_CREDENTIALS=...
GIGACHAT_MODEL=GigaChat

# OpenAI / совместимые
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=            # пусто для api.openai.com

# Qwen (DashScope)
QWEN_API_KEY=...
QWEN_MODEL=qwen-plus

# Ollama (самохостинг)
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

#### Режим KuzuDB (рекомендуется)

```ini
USE_INMEMORY=false
GRAPH_BACKEND=kuzu

# KuzuDB — путь к директории БД (создаётся автоматически)
KUZU_PATH=/absolute/path/to/personal-ai/data/kuzu_db

# ChromaDB — файловые пути (создаются автоматически)
CHROMA_NODES_PATH=/absolute/path/to/personal-ai/data/graph_structures/vectorized_nodes/default
CHROMA_QUADS_PATH=/absolute/path/to/personal-ai/data/graph_structures/vectorized_quadruplets/default

# Путь к E5-модели
FINETUNED_MODEL_PATH=/absolute/path/to/personal-ai/models/wikidata_finetuned_remote/wikidata_finetuned

# TComplEx (опционально)
TCOMPLEX_CHECKPOINT=/absolute/path/to/personal-ai/models/cronkgqa/tcomplex.ckpt
TCOMPLEX_DATA_PATH=/absolute/path/to/personal-ai/wikidata_big/kg/tkbc_processed_data/wikidata_big
```

#### Режим In-Memory (быстрый старт, без БД)

```ini
USE_INMEMORY=true
KG_DATA_PATH=/absolute/path/to/personal-ai/wikidata_big/kg
MODEL_PATH=/absolute/path/to/personal-ai/models/wikidata_finetuned_remote/wikidata_finetuned
```

---

### 5. Первичная сборка KG: KuzuDB + ChromaDB

Этот раздел выполняется **один раз** при первоначальном развёртывании или при импорте нового датасета. Скрипт атомарно загружает данные в граф KuzuDB и строит векторные индексы ChromaDB.

#### Шаг 5.1 — Проверьте наличие данных

```bash
# Должны выводиться строки вида Q76\tP26\tQ13133\t+1961...
head -5 wikidata_big/kg/full.txt

# Должны выводиться строки вида Q76\tBarack Obama
head -5 wikidata_big/kg/wd_id2entity_text.txt
```

#### Шаг 5.2 — Запустите первичную ингестию

```bash
source .venv/bin/activate

python scripts/ingest_full.py
```

Скрипт использует `batch_size=5000` и поддерживает возобновление после прерывания через параметр `skip_lines` (задаётся прямо в файле). На полном датасете Wikidata (~2.9М квадруплетов) ожидайте несколько часов.

Пример вывода:
```
INFO  Batch 1/580: loaded 5000 quadruplets -> KuzuDB
INFO  ChromaDB: indexed 5000 node embeddings
...
INFO  Ingestion complete: added=2900000 skipped=0 errors=0
```

#### Шаг 5.3 — Убедитесь, что данные загружены

```bash
# Количество векторов в ChromaDB:
python scripts/check_chroma_counts.py

# Состояние графа KuzuDB:
python scripts/verify_ingestion.py

# Быстрый тест QA (без запуска бота):
python scripts/qa_test_subset.py
```

---

### 6. Запуск бота

```bash
source .venv/bin/activate
python bot.py
```

Ожидаемый вывод при старте в режиме KuzuDB:
```
INFO  Using KuzuDB at /path/to/data/kuzu_db
INFO  ChromaDB nodes: 2900000 vectors
INFO  ChromaDB quads: 2900000 vectors
INFO  TComplEx loaded from models/cronkgqa/tcomplex.ckpt
INFO  Production engine initialized successfully.
INFO  Bot started. Listening for updates...
```

#### Автозапуск через systemd (Linux)

Создайте `/etc/systemd/system/personal-ai-bot.service`:

```ini
[Unit]
Description=Personal AI KG Bot
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/absolute/path/to/personal-ai
EnvironmentFile=/absolute/path/to/personal-ai/.env
ExecStart=/absolute/path/to/personal-ai/.venv/bin/python bot.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable personal-ai-bot
sudo systemctl start personal-ai-bot
sudo journalctl -u personal-ai-bot -f
```

#### Автозапуск через launchd (macOS)

Создайте wrapper-скрипт `start_bot.sh` в корне проекта (launchd не читает `.env` напрямую):

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

Создайте `~/Library/LaunchAgents/com.personal-ai.bot.plist`:

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
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><true/>
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

## Инкрементальное обновление

Для добавления новых фактов без пересборки всего графа — скрипт `incremental_update.py`. Он атомарно записывает данные в KuzuDB, ChromaDB и при необходимости обновляет Pickle-файлы TComplEx. В случае ошибки — автоматически восстанавливает Pickle из резервных копий `.bak`.

#### Подготовьте файл с новыми фактами

```json
[
  {
    "subject": {"name": "Иван Петров", "id": null},
    "relation": "works_at",
    "object":   {"name": "Сбер",       "id": null},
    "time_start": "2020",
    "time_end":   null
  }
]
```

#### Запустите ингестию

```bash
source .venv/bin/activate

# Добавить факты в граф и ChromaDB (без переобучения TComplEx):
python scripts/incremental_update.py \
    --input new_facts.json

# Добавить факты + сразу переобучить TComplEx:
python scripts/incremental_update.py \
    --input new_facts.json \
    --tkbc-dir wikidata_big/kg/tkbc_processed_data/wikidata_big/ \
    --force-retrain \
    --retrain-epochs 50

# Только проверить формат без записи в БД:
python scripts/incremental_update.py \
    --input new_facts.json \
    --dry-run
```

Пример вывода при успешной ингестии:
```
INFO  Loaded 42 facts from new_facts.json
INFO  Backed up ent_id -> ent_id.bak
INFO  EntityResolver: resolved 38 known / 4 new LOCAL_ generated
INFO  KuzuDB: added 42 quadruplets
INFO  ChromaDB: indexed 42 node vectors + 42 quad vectors
INFO  Ingestion complete: added=42 skipped=0 errors=0 tkbc_updated=True
```

#### Перезапуск бота после обновления

Бот загружает данные в память при старте — после ингестии нужен перезапуск:

```bash
# systemd:
sudo systemctl restart personal-ai-bot

# launchd:
launchctl stop com.personal-ai.bot && launchctl start com.personal-ai.bot

# Вручную: Ctrl+C, затем python bot.py
```

---

## Переобучение TComplEx

TComplEx — темпоральный скорер, присваивающий математические логиты квадруплетам. Переобучение необходимо после значительного пополнения базы знаний, чтобы новые сущности корректно ранжировались на стадии Scoring.

```bash
source .venv/bin/activate

python scripts/retrain_tcomplex.py \
    --tkbc-dir wikidata_big/kg/tkbc_processed_data/wikidata_big/ \
    --epochs 50 \
    --batch-size 1000 \
    --lr 1e-3
```

Что происходит под капотом:
1. Загружается существующий чекпоинт (`TCOMPLEX_CHECKPOINT` из `.env` или `tcomplex.ckpt` в `tkbc-dir`)
2. Модель дообучается на обновлённом `train.pickle` (warm start, не с нуля)
3. Новый чекпоинт сохраняется как `tcomplex_retrained.ckpt` в `tkbc-dir`

После завершения обновите `.env`:

```ini
TCOMPLEX_CHECKPOINT=/absolute/path/to/wikidata_big/kg/tkbc_processed_data/wikidata_big/tcomplex_retrained.ckpt
```

И перезапустите бота.

> Если чекпоинт отсутствует, скрипт завершится с ошибкой и предложит пройти полный цикл обучения через `kaggle_job/`. Fine-tune работает только при наличии базового `.ckpt`.

---

## Команды Telegram-бота

| Команда | Действие |
|---|---|
| `/ask <вопрос>` | Полный 7-стадийный QA-конвейер, ответ на естественном языке |
| `/facts <вопрос>` | Отладочная трассировка: сырые факты, E5-сходства, TComplEx-логиты |
| `/graph <сущность>` | PNG-визуализация 1-hop подграфа |
| `/settings` | Текущие гиперпараметры: `top_k`, `confidence_gap` |
| `/set <param> <val>` | Изменить параметр текущей сессии, например `/set top_k 15` |
| `/status` | Режим работы, число квадруплетов, LLM-бэкенд, устройство (CPU/MPS/CUDA) |
| `/ingest` | Загрузить документ (PDF/DOCX/PPTX/TXT) и добавить извлечённые факты в граф |
| `/help` | Справка по всем командам |

---

## Ключевые классы

| Класс | Файл | Назначение |
|---|---|---|
| [`QAEngine`](src/pipelines/qa/qa_engine.py) | `src/pipelines/qa/qa_engine.py` | Оркестратор 7-стадийного конвейера |
| [`ExtractionStage`](src/pipelines/qa/stages/extraction.py) | `src/pipelines/qa/stages/extraction.py` | LLM-диспетчер: сущности + тип вопроса |
| [`HybridRetriever`](src/pipelines/qa/stages/retrieval.py) | `src/pipelines/qa/stages/retrieval.py` | Граф + вектор (объединённый поиск) |
| [`ScoringStage`](src/pipelines/qa/stages/scoring.py) | `src/pipelines/qa/stages/scoring.py` | TComplEx + Confidence Gap selection |
| [`GenerationStage`](src/pipelines/qa/stages/generation.py) | `src/pipelines/qa/stages/generation.py` | LLM-генерация финального ответа |
| [`EntityResolver`](src/pipelines/ingestion/entity_resolver.py) | `src/pipelines/ingestion/entity_resolver.py` | 5-уровневое разрешение сущностей |
| [`TemporalKGIngester`](src/pipelines/ingestion/temporal_kg_ingester.py) | `src/pipelines/ingestion/temporal_kg_ingester.py` | Загрузка квадруплетов в граф и ChromaDB |
| [`KnowledgeGraphModel`](src/kg_model/knowledge_graph_model.py) | `src/kg_model/knowledge_graph_model.py` | Единый контроллер KuzuDB + ChromaDB |
| [`QAConfig`](src/config/qa_config.py) | `src/config/qa_config.py` | Все гиперпараметры конвейера |
| [`load_engine`](src/bot/engine_loader.py) | `src/bot/engine_loader.py` | Singleton-фабрика: выбор режима работы |
| [`KGNavigator`](src/utils/kg_navigator.py) | `src/utils/kg_navigator.py` | Обход графа для команды `/graph` |
| [`TemporalScorer`](src/kg_model/temporal/temporal_model.py) | `src/kg_model/temporal/temporal_model.py` | Загрузка и инференс TComplEx |
