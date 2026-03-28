# Personal AI — Knowledge Graph QA Navigator

[![Python 3.10](https://img.shields.io/badge/Python-3.10-blue.svg)](https://www.python.org/downloads/release/python-3100/)
[![License MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![KuzuDB](https://img.shields.io/badge/Graph_DB-KuzuDB-orange.svg)](https://kuzudb.com/)
[![ChromaDB](https://img.shields.io/badge/Vector_DB-ChromaDB-purple.svg)](https://www.trychroma.com/)
[![TComplEx](https://img.shields.io/badge/Temporal_Scorer-TComplEx-red.svg)](https://arxiv.org/abs/2005.07782)

Production-система вопросно-ответного поиска поверх графов знаний. Реализует гибридный RAG с темпоральным ранжированием: структурный поиск по графу + нейросетевой семантический поиск + математическая оценка правдоподобия фактов через TComplEx.

---

## Быстрый старт (3 команды)

```bash
git clone <repo-url> personal-ai && cd personal-ai
bash setup.sh                # создаёт .venv, устанавливает зависимости, копирует .env.example → .env
bash run_inmemory.sh         # запускает бота в in-memory режиме (без БД, без модели E5)
```

> In-memory режим работает без ChromaDB, KuzuDB и TComplEx — только `full.txt` + ключевой поиск.
> Для полноценной работы смотрите [Развёртывание](#развёртывание).

---

## Содержание

- [Архитектура](#архитектура)
- [Режимы работы](#режимы-работы)
- [Развёртывание](#развёртывание)
  - [1. Клонирование и окружение](#1-клонирование-и-окружение)
  - [2. E5-модель (обязательно)](#2-e5-модель-обязательно)
  - [3. TComplEx (опционально)](#3-tcomplex-опционально)
  - [4. Конфигурация .env](#4-конфигурация-env)
  - [5. Форматы данных](#5-форматы-данных)
  - [6. Первичная сборка KG](#6-первичная-сборка-kg)
  - [7. Запуск бота](#7-запуск-бота)
- [Добавление новых фактов в граф знаний](#добавление-новых-фактов-в-граф-знаний)
- [TComplEx: переобучение](#tcomplex-переобучение)
- [Команды Telegram-бота](#команды-telegram-бота)
- [Структура проекта](#структура-проекта)
- [Ключевые классы](#ключевые-классы)
- [Troubleshooting](#troubleshooting)

---

## Архитектура

Ядро системы — [`QAEngine`](src/pipelines/qa/qa_engine.py), реализующий 7-стадийный конвейер:

```
Запрос пользователя
        |
        v
+-----------------------------------------------------------------------+
|  Стадия 1 — Extraction  [stages/extraction.py]                        |
|  LLM извлекает сущности, тип вопроса (simple_time / before_after /    |
|  time_join / first_last) и временные рамки.                           |
+-----------------------------------------------------------------------+
        |
        v
+-----------------------------------------------------------------------+
|  Стадия 2 — Entity Resolution  [ingestion/entity_resolver.py]         |
|  5-уровневый каскад:                                                  |
|  L1: exact_id → L2: graph lookup → L2.5: rapidfuzz≥90                |
|  → L3: vector<0.25 → L4: LLM → L5: новый LOCAL_ id                   |
+-----------------------------------------------------------------------+
        |
        v
+-----------------------------------------------------------------------+
|  Стадия 3 — Graph Retrieval  [stages/retrieval.py]                    |
|  Соседи 1-го порядка вокруг разрешённых сущностей.                    |
|  Бэкенды: KuzuDB / Neo4j / InMemoryGraph.                             |
+-----------------------------------------------------------------------+
        |
        v
+-----------------------------------------------------------------------+
|  Стадия 4 — Vector Retrieval  [stages/retrieval.py]                   |
|  ChromaDB + finetuned multilingual-e5-small.                          |
|  "president" ~ "head of state", "СССР" ~ "Soviet Union".             |
+-----------------------------------------------------------------------+
        |  граф + вектор (объединение)
        v
+-----------------------------------------------------------------------+
|  Стадия 5 — Scoring (TComplEx)  [stages/scoring.py]                   |
|  Тензорная факторизация оценивает правдоподобие каждого факта.        |
|  Темпоральный фильтр отсекает факты вне диапазона запроса.            |
|  Alpha-вес адаптируется по типу вопроса.                              |
+-----------------------------------------------------------------------+
        |
        v
+-----------------------------------------------------------------------+
|  Стадия 6 — Selection (Confidence Gap)  [stages/scoring.py]           |
|  Оставляет только факты, чья оценка значимо превышает фоновый шум.    |
+-----------------------------------------------------------------------+
        |
        v
+-----------------------------------------------------------------------+
|  Стадия 7 — Generation (LLM)  [stages/generation.py]                  |
|  LLM формирует ответ строго по отобранным фактам.                     |
|  Поддержка 6 бэкендов: DeepSeek, YandexGPT, GigaChat, OpenAI,        |
|  Qwen, Ollama.                                                         |
+-----------------------------------------------------------------------+
        |
        v
    Ответ пользователю
```

---

## Режимы работы

| Режим | Переменные | Граф | Вектор | Когда использовать |
|---|---|---|---|---|
| **SimpleInMemory** | `USE_INMEMORY=true` + движок упал | `raw_quads` список | numpy E5 | Демо без данных, fallback при сбое |
| **Full + InMemoryGraph** | `USE_INMEMORY=true` + движок поднялся | `InMemoryGraphConnector` | /tmp ChromaDB | Разработка с full.txt, без сервера БД |
| **KuzuDB** | `USE_INMEMORY=false`<br>`GRAPH_BACKEND=kuzu` | KuzuDB (файловый) | ChromaDB (файловый) | **Production без сервера** |
| **Neo4j** | `USE_INMEMORY=false`<br>`GRAPH_BACKEND=neo4j` | Neo4j 5.x | ChromaDB (файловый) | Кластер, многопользовательский доступ |

**Рекомендуется KuzuDB** — не требует отдельного сервера, данные хранятся локально.

### Два sub-режима In-Memory

**SimpleInMemoryEngine** (fallback при сбое):
- Данные: `raw_quads` список из `full.txt` + numpy-эмбеддинги
- Ингестия через бота сохраняется в stash-файл JSON
- Нет ChromaDB, нет KuzuDB

**Full Engine + InMemoryGraphConnector** (основной `USE_INMEMORY=true`):
- `InMemoryGraphConnector` заполняется из `full.txt`
- ChromaDB в `/tmp/personalai_chroma/` (сбрасывается при перезапуске)
- Все стадии QAEngine работают в полном объёме

---

## Развёртывание

### 1. Клонирование и окружение

```bash
git clone <repo-url> personal-ai
cd personal-ai

# Python строго 3.10
python3.10 -m venv .venv
source .venv/bin/activate   # Linux / macOS

pip install --upgrade pip
pip install -r requirements.txt

# Создаёт папки, копирует .env.example → .env
bash setup.sh
```

> **Apple Silicon (M1/M2/M3):** PyTorch автоматически выбирает MPS. Доп. настройка не нужна.
>
> **CUDA GPU:**
> ```bash
> pip install torch --index-url https://download.pytorch.org/whl/cu121
> ```

---

### 2. E5-модель (обязательно)

```bash
mkdir -p models/wikidata_finetuned_remote/wikidata_finetuned
```

**Вариант A — базовая модель с HuggingFace:**
```bash
python -c "
from sentence_transformers import SentenceTransformer
SentenceTransformer('intfloat/multilingual-e5-small').save(
    'models/wikidata_finetuned_remote/wikidata_finetuned'
)
print('E5 saved.')
"
```

**Вариант B — finetuned-версия с сервера:**
```bash
scp -r user@server:/path/to/wikidata_finetuned \
    models/wikidata_finetuned_remote/wikidata_finetuned
```

После загрузки в директории должны быть:
```
models/wikidata_finetuned_remote/wikidata_finetuned/
├── config.json
├── tokenizer_config.json
├── tokenizer.json
└── pytorch_model.bin   (или model.safetensors)
```

---

### 3. TComplEx (опционально)

Чекпоинт `.ckpt` обязателен только для темпорального ранжирования (стадия 5). Без него система работает на 6 стадиях.

```bash
mkdir -p models/cronkgqa
# Скопировать с другого развёртывания:
scp user@server:/path/to/tcomplex.ckpt models/cronkgqa/
```

Обучить с нуля: используйте `kaggle_job/` (полный цикл tkbc).

---

### 4. Конфигурация .env

```bash
cp .env.example .env
```

#### Полная таблица переменных окружения

| Переменная | Тип | Default | Описание |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | str | — | **Обязательно.** Токен бота от @BotFather |
| `LLM_BACKEND` | str | `deepseek` | Бэкенд LLM: `deepseek` \| `yandexgpt` \| `gigachat` \| `openai` \| `qwen` \| `ollama` |
| `USE_INMEMORY` | bool | `true` | `true` = in-memory режим; `false` = KuzuDB/Neo4j |
| `GRAPH_BACKEND` | str | `neo4j` | При `USE_INMEMORY=false`: `kuzu` \| `neo4j` |
| `KG_DATA_PATH` | path | `wikidata_big/kg` | Путь к директории с `full.txt` |
| `FINETUNED_MODEL_PATH` | path | `models/wikidata_finetuned_remote/wikidata_finetuned` | Путь к E5-модели |
| `KUZU_PATH` | path | `data/kuzu_db` | Директория KuzuDB |
| `CHROMA_NODES_PATH` | path | `data/graph_structures/vectorized_nodes/default` | ChromaDB узлы |
| `CHROMA_QUADS_PATH` | path | `data/graph_structures/vectorized_quadruplets/default` | ChromaDB квадруплеты |
| `TCOMPLEX_CHECKPOINT` | path | `models/cronkgqa/tcomplex.ckpt` | Чекпоинт TComplEx |
| `TCOMPLEX_DATA_PATH` | path | `wikidata_big/kg/tkbc_processed_data/wikidata_big/` | Pickle-файлы для TComplEx |
| `NEO4J_HOST` | str | `localhost` | Neo4j хост |
| `NEO4J_PORT` | int | `7687` | Neo4j порт |
| `NEO4J_USER` | str | `neo4j` | Neo4j пользователь |
| `NEO4J_PASSWORD` | str | `password` | Neo4j пароль |
| `NEO4J_DB` | str | `neo4j` | Neo4j база данных |
| `QA_CONFIDENCE_GAP` | float | `0.20` | Порог Confidence Gap для отбора фактов |
| `QA_TCOMPLEX_THRESHOLD` | float | `-3.0` | Порог TComplEx логита |

#### LLM-бэкенды

```ini
# DeepSeek (2 переменные)
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_MODEL=deepseek-chat

# YandexGPT (3 переменные — обязательны все три)
YANDEX_API_KEY=...
YANDEX_FOLDER_ID=...
YANDEX_MODEL=yandexgpt

# GigaChat (Сбер) — OAuth2 credentials
GIGACHAT_CREDENTIALS=...
GIGACHAT_MODEL=GigaChat

# OpenAI / совместимые (OPENAI_BASE_URL пустой для api.openai.com)
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=

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
KUZU_PATH=/absolute/path/to/personal-ai/data/kuzu_db
CHROMA_NODES_PATH=/absolute/path/to/personal-ai/data/graph_structures/vectorized_nodes/default
CHROMA_QUADS_PATH=/absolute/path/to/personal-ai/data/graph_structures/vectorized_quadruplets/default
FINETUNED_MODEL_PATH=/absolute/path/to/personal-ai/models/wikidata_finetuned_remote/wikidata_finetuned
TCOMPLEX_CHECKPOINT=/absolute/path/to/personal-ai/models/cronkgqa/tcomplex.ckpt
TCOMPLEX_DATA_PATH=/absolute/path/to/personal-ai/wikidata_big/kg/tkbc_processed_data/wikidata_big
```

#### Режим In-Memory

```ini
USE_INMEMORY=true
KG_DATA_PATH=/absolute/path/to/personal-ai/wikidata_big/kg
```

---

### 5. Форматы данных

#### full.txt — основной датасет квадруплетов (TSV, 5 колонок)

```
Q76	P26	Q13133	+1961-01-00	+1975-01-00
Q76	P106	Q82955	+0000-01-01	+9999-01-01
```

Колонки: `subject_id`, `relation_id`, `object_id`, `time_start`, `time_end`.
Без временных меток используйте `+0000-01-01` / `+9999-01-01` как заглушки.

#### wd_id2entity_text.txt / wd_id2relation_text.txt (TSV, 2 колонки)

```
Q76	Barack Obama
P26	spouse
```

Используются для подстановки меток вместо Q/P-идентификаторов.

#### tkbc_processed_data/ — Pickle-файлы TComplEx

| Файл | Тип Python | Описание |
|---|---|---|
| `ent_id` | `dict[str, int]` | entity_id → числовой индекс |
| `rel_id` | `dict[str, int]` | relation_id → числовой индекс |
| `ts_id` | `dict[str, int]` | timestamp → числовой индекс |
| `train.pickle` | `list[tuple[int,int,int,int,int]]` | (s, r, o, ts, te) числовые индексы |

#### facts.json — формат для инкрементального добавления

```json
[
  {
    "subject": {"name": "Иван Петров", "id": null},
    "relation": "works_at",
    "object":   {"name": "Сбер",       "id": null},
    "time_start": "2020",
    "time_end":   null
  },
  {
    "subject": {"name": "Набоков",   "id": "Q2152"},
    "relation": "educated_at",
    "object":   {"name": "Кембридж", "id": "Q35794"},
    "time_start": "1919",
    "time_end":   "1922"
  }
]
```

- `id`: явный Wikidata Q-ID или `null` — система сгенерирует `LOCAL_` идентификатор
- `relation`: рекомендуется `snake_case`
- `time_end: null` означает «по настоящее время»

---

### 6. Первичная сборка KG

Выполняется **один раз** при первоначальном развёртывании.

```bash
bash setup.sh --build-kg
```

Скрипт загружает данные из `full.txt` в KuzuDB батчами по 1000 строк и строит векторные индексы ChromaDB. На полном датасете Wikidata (~2.9М квадруплетов) ожидайте несколько часов.

Верификация после сборки:
```bash
python scripts/check_chroma_counts.py   # количество векторов
python scripts/verify_ingestion.py       # состояние графа
python scripts/qa_test_subset.py         # быстрый тест QA
```

---

### 7. Запуск бота

```bash
# In-memory (без предварительной сборки БД):
bash run_inmemory.sh

# Production (KuzuDB + ChromaDB, после setup.sh --build-kg):
bash run_db.sh
```

#### Автозапуск через systemd (Linux)

`/etc/systemd/system/personal-ai-bot.service`:
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

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable personal-ai-bot
sudo systemctl start personal-ai-bot
sudo journalctl -u personal-ai-bot -f
```

---

## Интерфейс и интерпретация ответов

После запуска бота в Telegram, вы можете взаимодействовать с ним через команды `/ask`, `/status` и другие. Ниже приведено описание того, как читать и интерпретировать ответы системы.

### Команда `/ask`: Ответ на вопрос

При отправке вопроса (например, `/ask Сколько активных корпоративных клиентов?`), бот возвращает ответ следующего вида:

> **Ответ:** По состоянию на 2023 год у Сбера насчитывалось 3,2 миллиона активных корпоративных клиентов. [0.95]
> 
> _Топ-3 фактов:_
> 1. [0.95] Сбербанк → active_corporate_clients → 3.2M (+2023-01-01)
> 2. [0.42] Сбербанк → total_clients → 100M (+2023-01-01)
> 3. [0.15] Сбербанк → employees → 200k (+2023-01-01)

#### Как это читать:
1. **Текст ответа**: Сгенерированный LLM текст на основе найденных фактов.
2. **Confidence Score [0.95]**: Число в скобках после ответа — это оценка уверенности системы. 
   - `> 0.7`: Высокая уверенность, ответ надежен.
   - `0.4 - 0.7`: Средняя уверенность, стоит перепроверить факты ниже.
   - `< 0.4`: Низкая уверенность, система могла "галлюцинировать" или не найти точных данных.
3. **Топ-N фактов**: Список "сырых" данных из Графа Знаний, которые были переданы LLM для генерации ответа. Формат: `Субъект → Отношение → Объект (Время)`.

### Команда `/status`: Мониторинг системы

Позволяет проверить состояние всех компонентов. Пример вывода:

> **Статус системы**
> 
> Mode: `production`
> [OK] KuzuDB
> [OK] ChromaDB
> [OK] TComplEx
> LLM: `deepseek`
> **Device: `cuda`** (зеленый свет в логах)
> Graph: 1.2M | 2.9M квадруплетов

#### На что обратить внимание:
- **Device**: Показывает, на чем работают нейросетевые компоненты (E5-embeddings и TComplEx).
  - `cuda` / `mps` — **GPU ускорение активно**. Работа будет быстрой (зеленый цвет в консоли).
  - `cpu` — **GPU не найден**. В консоли появится ⚠️ **КРАСНОЕ ПРЕДУПРЕЖДЕНИЕ**. Работа может быть значительно медленнее.

---

## Добавление новых фактов в граф знаний

Система поддерживает 2 основных способа загрузки новых документов и фактов. В обоих случаях данные экстрактируются через LLM и атомарно записываются в графовую (Kuzu/Neo4j) и векторную (ChromaDB) базы с дедупликацией.

### Способ 1: Через Telegram-бота (UI)
Отправьте команду `/ingest` или просто перетащите документ (PDF/DOCX/PPTX/TXT) в окно чата. Бот асинхронно в фоне извлекает факты через LLM и добавляет их в граф, отправляя статус-сообщения.

### Способ 2: Через терминал (CLI-скрипты)
Процесс разделен на два этапа для гибкости (парсинг и загрузка):

**Этап 1. Экстракция: Извлечение фактов из PDF/Текста**
Срипт считывает папку с файлами и генерирует `facts.json` с помощью указанного в `.env` LLM-бэкенда.
```bash
source .venv/bin/activate
python extract/extract_quadruplets.py путь_к_папке_с_pdf --output new_facts.json
```

**Этап 2. Ингестия: Интеграция фактов в граф и векторную базу**
```bash
# Добавить извлеченные факты в граф и ChromaDB:
python scripts/incremental_update.py --input new_facts.json

# Добавить факты + переобучить TComplEx (очередь scoring):
python scripts/incremental_update.py \
    --input new_facts.json \
    --tkbc-dir wikidata_big/kg/tkbc_processed_data/wikidata_big/ \
    --force-retrain --retrain-epochs 50

# Только проверить формат json (dry run, без записи):
python scripts/incremental_update.py --input new_facts.json --dry-run
```

### Что обновляется в каждом режиме

| Компонент | SimpleInMemory | Full+InMemoryGraph | KuzuDB | Neo4j |
|---|:---:|:---:|:---:|:---:|
| Граф (узлы/рёбра) | — | InMemoryGraph (до перезапуска) | KuzuDB (постоянно) | Neo4j (постоянно) |
| ChromaDB векторы | — | /tmp (до перезапуска) | файловый (постоянно) | файловый (постоянно) |
| TComplEx pickles | — | — | при `--tkbc-dir` | при `--tkbc-dir` |
| Stash JSON | `/tmp/inmemory_stash.json` | — | — | — |

**SimpleInMemoryEngine** (USE_INMEMORY=true + движок упал): факты сохраняются в stash-файл JSON и загружаются при следующем старте.

**Full Engine + InMemoryGraphConnector** (USE_INMEMORY=true + движок поднялся): факты записываются в InMemoryGraph и ChromaDB в `/tmp`, но сбрасываются при перезапуске.

**KuzuDB / Neo4j** (USE_INMEMORY=false): факты сохраняются постоянно.

### Atomicity и восстановление после сбоя

`incremental_update.py` реализует атомарный протокол для pickle-файлов TComplEx:
1. **backup** — копирует `ent_id`, `rel_id`, `ts_id`, `train.pickle` → `.bak` файлы
2. **ingest** — записывает данные в граф и ChromaDB
3. При ошибке: **restore** — восстанавливает `.bak` обратно
4. При успехе: **delete backups** — удаляет `.bak`

Это гарантирует консистентность: либо все компоненты обновлены, либо ни один.

После ингестии перезапустите бота:
```bash
sudo systemctl restart personal-ai-bot   # systemd
# или Ctrl+C, затем python bot.py
```

---

## Пакетная загрузка документов (`ingest_directory.py`)

Скрипт принимает директорию, параллельно обрабатывает все файлы (PDF/DOCX/PPTX/TXT),
добавляет извлечённые факты в KuzuDB + ChromaDB и запускает переобучение TComplEx.

### Запуск

```bash
source .venv/bin/activate
python scripts/ingest_directory.py \
    --dir /path/to/documents \
    --tkbc-dir wikidata_big/kg/tkbc_processed_data/wikidata_big/
```

Или коротко (если `TCOMPLEX_DATA_PATH` задан в `.env`):

```bash
python scripts/ingest_directory.py --dir /path/to/documents
```

### Параметры

| Параметр | По умолчанию | Описание |
|---|---|---|
| `--dir` | **обязательный** | Директория с документами |
| `--tkbc-dir` | `$TCOMPLEX_DATA_PATH` | Путь к TKBC pickle-файлам для TComplEx |
| `--workers` | `min(32, cpu×4)` | Потоков для параллельной обработки файлов |
| `--epochs` | `50` | Эпох для переобучения TComplEx |
| `--lr` | `1e-3` | Learning rate |
| `--skip-retrain` | выкл | Пропустить переобучение TComplEx |
| `--no-amp` | выкл | Отключить BF16/FP16 (принудительно FP32) |
| `--reprocess` | выкл | Перезапустить извлечение для уже обработанных файлов |

### Адаптация под GPU

В начале скрипт определяет доступное устройство и выводит цветной баннер:

- **Зелёный `[GPU]`** — CUDA GPU найден, используется аппаратное ускорение
- **Красный `[CPU]`** — GPU не обнаружен, работа на процессоре (медленно)

Настройки автоматически выбираются по объёму VRAM:

| Тир | GPU | VRAM | Embed batch | AMP |
|---|---|---|---|---|
| `ultra` | A100 80 GB, H100 | ≥ 70 GB | 1024 | BF16 |
| `high` | A100 40 GB, A6000 | ≥ 36 GB | 512 | BF16 |
| `mid` | A30, A10G | ≥ 20 GB | 256 | BF16 |
| `low` | A4, T4, RTX 3070 | ≥ 8 GB | 128 | FP16 |
| `cpu` | — | — | 64 | — |

При нескольких GPU DataParallel включается автоматически. BF16 AMP (поддерживается на A100/H100/A30) значительно ускоряет переобучение TComplEx. FP16 используется на старших картах Ampere/Turing.

### Поведение при невалидных файлах

Файлы с неподдерживаемым расширением (`.xlsx`, `.json`, и т.д.) пропускаются с предупреждением — обработка остальных продолжается. Уже обработанные файлы пропускаются автоматически (кеш в `extract_data/processed_files.json`).

### Пример вывода

```
====  ingest_directory.py  ====

══════════════════════════════════════════════════════════
  [GPU]  NVIDIA A100-SXM4-80GB  80.0 GB VRAM
        tier=ultra  AMP=bf16  embed_batch=1024
══════════════════════════════════════════════════════════

  Found 12 supported file(s)  (skipped 2 unsupported)
  [WARN] Unsupported format — skipped: data.xlsx

[1/3] Extracting facts from 12 file(s)  (workers=32)
  [OK]  report_2023.pdf  →  47 facts
  [OK]  strategy.docx   →  23 facts
  ...
  [OK]  Extracted 312 total facts in 42s

[2/3] Writing 312 facts → KuzuDB + ChromaDB
  [OK]  Saved 298 facts  (14s)

[3/3] TComplEx retrain
  [OK]  Training rows: 3,104,512  epochs=50  lr=0.001  AMP=True
  [OK]  Retrain done in 183s — checkpoint saved
```

---

## TComplEx: переобучение

TComplEx — темпоральный скорер, присваивающий логиты квадруплетам. Переобучение нужно после значительного пополнения базы знаний, чтобы новые сущности корректно ранжировались на стадии Scoring.

### Когда нужно переобучать

- Добавлено >1000 новых сущностей или отношений
- Заметное снижение качества ответов на темпоральные вопросы
- После импорта нового датасета

### Файлы данных TComplEx

| Файл | Тип | Описание |
|---|---|---|
| `ent_id` | `dict[str, int]` | entity_id → числовой индекс |
| `rel_id` | `dict[str, int]` | relation_id → числовой индекс |
| `ts_id` | `dict[str, int]` | timestamp → числовой индекс |
| `train.pickle` | `list[tuple]` | (s, r, o, ts, te) числовые индексы |

### Формат checkpoint (.ckpt)

Файл `tcomplex.ckpt` — PyTorch state_dict тензорной модели TComplEx. Загружается через `TemporalScorer(checkpoint_path=...)`.

### Команда переобучения

```bash
source .venv/bin/activate

# Результат сохраняется туда же, куда смотрит TCOMPLEX_CHECKPOINT из .env:
python scripts/retrain_tcomplex.py \
    --tkbc-dir wikidata_big/kg/tkbc_processed_data/wikidata_big/ \
    --epochs 50 \
    --batch-size 1000 \
    --lr 1e-3

# Явно указать путь для сохранения:
python scripts/retrain_tcomplex.py \
    --tkbc-dir wikidata_big/kg/tkbc_processed_data/wikidata_big/ \
    --checkpoint-out models/cronkgqa/tcomplex_v2.ckpt \
    --epochs 50
```

Приоритет `--checkpoint-out`:
1. `--checkpoint-out` (явный аргумент)
2. `TCOMPLEX_CHECKPOINT` из `.env`
3. `models/cronkgqa/tcomplex.ckpt` (дефолт)

Что происходит:
1. Загружается существующий чекпоинт (`TCOMPLEX_CHECKPOINT` или `tcomplex.ckpt` в tkbc-dir)
2. Модель дообучается на обновлённом `train.pickle` (warm start)
3. Новый чекпоинт сохраняется по приоритету выше

### Hot-reload через /retrain

В Telegram-боте команда `/retrain` запускает переобучение без перезапуска процесса.

### Автоматический retrain через incremental_update.py

```bash
python scripts/incremental_update.py \
    --input new_facts.json \
    --tkbc-dir wikidata_big/kg/tkbc_processed_data/wikidata_big/ \
    --force-retrain \
    --retrain-epochs 50
```

---

## Команды Telegram-бота

| Команда | Действие |
|---|---|
| `/start` | Приветствие и краткая справка |
| `/help` | Полная справка по командам |
| `/ask <вопрос>` | Полный 7-стадийный QA-конвейер |
| `/facts <вопрос>` | Отладочная трассировка: факты, E5-сходства, TComplEx-логиты |
| `/dbg <вопрос>` | Расширенная отладка с промптами |
| `/graph <сущность>` | PNG-визуализация 1-hop подграфа |
| `/settings` | Текущие гиперпараметры: `top_k`, `confidence_gap` |
| `/set <param> <val>` | Изменить параметр сессии, например `/set top_k 15` |
| `/status` | Режим работы, число квадруплетов, LLM-бэкенд, устройство |
| `/ingest` | Загрузить документ (PDF/DOCX/PPTX/TXT) и добавить факты в граф |
| `/retrain` | Переобучить TComplEx (требует настроенного `TCOMPLEX_DATA_PATH`) |

---

## Структура проекта

```
personal-ai/
│
├── bot.py                                  # Точка входа — Telegram-бот (aiogram)
│
├── scripts/
│   ├── build_kg.py                         # Первичная сборка KG (вызывается setup.sh)
│   ├── ingest_directory.py                 # Пакетная загрузка документов + retrain
│   ├── incremental_update.py               # Атомарное добавление новых фактов
│   ├── retrain_tcomplex.py                 # Переобучение темпорального скорера
│   ├── verify_ingestion.py                 # Проверка состояния графа
│   ├── check_chroma_counts.py              # Проверка ChromaDB
│   ├── qa_test_subset.py                   # Быстрое тестирование QA
│   ├── merge_out_json.py                   # Объединение выгрузок
│   └── inspect_chroma.py                   # Инспекция ChromaDB
│
├── src/
│   ├── config/
│   │   └── qa_config.py                    # QAConfig — все гиперпараметры
│   │
│   ├── pipelines/
│   │   ├── qa/
│   │   │   ├── qa_engine.py                # QAEngine — 7-стадийный оркестратор
│   │   │   ├── benchmark.py                # BenchmarkRunner
│   │   │   └── stages/
│   │   │       ├── extraction.py           # ExtractionStage
│   │   │       ├── retrieval.py            # HybridRetriever
│   │   │       ├── scoring.py              # ScoringStage + Confidence Gap
│   │   │       └── generation.py           # GenerationStage
│   │   └── ingestion/
│   │       ├── temporal_kg_ingester.py     # TemporalKGIngester
│   │       ├── entity_resolver.py          # EntityResolver (5 уровней)
│   │       └── doc_ingestion_service.py    # Ингестия документов через бот
│   │
│   ├── kg_model/
│   │   ├── knowledge_graph_model.py        # KnowledgeGraphModel — контроллер БД
│   │   ├── embeddings_model.py             # EmbeddingsModel
│   │   ├── graph_model.py                  # GraphModel
│   │   └── temporal/
│   │       ├── temporal_model.py           # TemporalScorer (TComplEx)
│   │       └── tkbc_models.py              # TComplEx архитектура
│   │
│   ├── db_drivers/
│   │   ├── graph_driver/
│   │   │   └── connectors/
│   │   │       ├── KuzuConnector.py        # KuzuDB
│   │   │       ├── Neo4jConnector.py       # Neo4j (parameterized queries)
│   │   │       └── InMemoryConnector.py    # In-memory граф
│   │   └── vector_driver/                  # ChromaDB + embedders
│   │
│   ├── bot/
│   │   ├── engine_loader.py                # Singleton-фабрика движка
│   │   ├── handlers.py                     # Обработчики команд бота
│   │   ├── formatters.py                   # Форматирование ответов
│   │   └── graph_renderer.py               # PNG-рендер подграфов
│   │
│   ├── llm/                                # 6 LLM-клиентов
│   │   ├── deepseek_client.py
│   │   ├── yandex_gpt_client.py
│   │   ├── gigachat_client.py
│   │   ├── openai_client.py
│   │   ├── qwen_client.py
│   │   └── ollama_client.py
│   │
│   └── utils/
│       ├── data_structs.py                 # Node, Quadruplet dataclasses
│       ├── kg_utils.py                     # KGEntityMapper
│       ├── wikidata_utils.py               # WikidataMapper
│       ├── kg_navigator.py                 # KGNavigator (для /graph)
│       └── device_utils.py                 # CPU/MPS/CUDA detection
│
├── models/                                 # Не в git — создать вручную
│   ├── wikidata_finetuned_remote/
│   │   └── wikidata_finetuned/             # E5-small finetuned
│   └── cronkgqa/
│       └── tcomplex.ckpt
│
├── data/                                   # Создаётся автоматически
│   ├── kuzu_db/
│   └── graph_structures/
│       ├── vectorized_nodes/default/
│       └── vectorized_quadruplets/default/
│
├── wikidata_big/kg/                        # Не в git — разместить вручную
│   ├── full.txt
│   ├── wd_id2entity_text.txt
│   ├── wd_id2relation_text.txt
│   └── tkbc_processed_data/wikidata_big/
│       ├── train.pickle
│       ├── ent_id
│       ├── rel_id
│       └── ts_id
│
├── docs/
│   └── deployment_bare_metal.md            # Детальный гайд по развёртыванию
│
├── setup.sh                                # Первичная настройка окружения
├── run_db.sh                               # Запуск в режиме KuzuDB/Neo4j
├── run_inmemory.sh                         # Запуск в in-memory режиме
├── .env.example                            # Шаблон конфигурации
└── requirements.txt
```

---

## Ключевые классы

| Класс | Файл | Назначение |
|---|---|---|
| [`QAEngine`](src/pipelines/qa/qa_engine.py) | `src/pipelines/qa/qa_engine.py` | Оркестратор 7-стадийного конвейера |
| [`ExtractionStage`](src/pipelines/qa/stages/extraction.py) | `stages/extraction.py` | LLM-диспетчер: сущности + тип вопроса |
| [`HybridRetriever`](src/pipelines/qa/stages/retrieval.py) | `stages/retrieval.py` | Граф + вектор (объединённый поиск) |
| [`ScoringStage`](src/pipelines/qa/stages/scoring.py) | `stages/scoring.py` | TComplEx + Confidence Gap selection |
| [`GenerationStage`](src/pipelines/qa/stages/generation.py) | `stages/generation.py` | LLM-генерация финального ответа |
| [`EntityResolver`](src/pipelines/ingestion/entity_resolver.py) | `ingestion/entity_resolver.py` | 5-уровневое разрешение сущностей |
| [`TemporalKGIngester`](src/pipelines/ingestion/temporal_kg_ingester.py) | `ingestion/temporal_kg_ingester.py` | Загрузка квадруплетов в граф и ChromaDB |
| [`KnowledgeGraphModel`](src/kg_model/knowledge_graph_model.py) | `kg_model/knowledge_graph_model.py` | Единый контроллер KuzuDB + ChromaDB |
| [`QAConfig`](src/config/qa_config.py) | `src/config/qa_config.py` | Все гиперпараметры конвейера |
| [`load_engine`](src/bot/engine_loader.py) | `bot/engine_loader.py` | Singleton-фабрика: выбор режима работы |
| [`TemporalScorer`](src/kg_model/temporal/temporal_model.py) | `kg_model/temporal/temporal_model.py` | Загрузка и инференс TComplEx |
| [`KGNavigator`](src/utils/kg_navigator.py) | `utils/kg_navigator.py` | Обход графа для команды `/graph` |

---

## Troubleshooting

### Бот не запускается: `TELEGRAM_BOT_TOKEN` not set

```bash
# Проверить, что .env существует и содержит токен:
grep TELEGRAM_BOT_TOKEN .env
```

### Ошибка `ModuleNotFoundError: No module named 'kuzu'`

KuzuDB не установлен или версия Python не 3.10:
```bash
python --version   # должно быть 3.10.x
pip install kuzu
```

### Ошибка `AttributeError: 'QAConfig' object has no attribute 'chroma_host'`

Используется устаревший `incremental_update.py`. Обновите до текущей версии из репозитория.

### ChromaDB пустой после сборки

```bash
python scripts/check_chroma_counts.py
# Если 0 — перезапустите: bash setup.sh --build-kg
```

### TComplEx не загружается: `No such file or directory: 'models/cronkgqa/tcomplex.ckpt'`

Файл чекпоинта не размещён. Система продолжит работу на 6 стадиях (без TComplEx-скоринга). Для полного функционала разместите чекпоинт или обучите через `kaggle_job/`.

### Бот зависает при большом `full.txt` в in-memory режиме

SimpleInMemoryEngine загружает все квадруплеты в RAM + строит numpy-эмбеддинги. На 2.9М строк — требуется ~16GB RAM и несколько минут. Используйте режим KuzuDB (`USE_INMEMORY=false`).

### Ошибка Neo4j: `ServiceUnavailable`

```bash
# Проверить, запущен ли Neo4j:
curl http://localhost:7474

# Или переключиться на KuzuDB:
echo "GRAPH_BACKEND=kuzu" >> .env
```
