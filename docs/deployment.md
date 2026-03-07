# Руководство по развёртыванию

## Предварительные требования

- Docker & Docker Compose ≥ 2.0
- Telegram Bot Token (получить у [@BotFather](https://t.me/BotFather))
- Сервер: минимум 8 GB RAM (E5-Small модель + Neo4j)
- Опционально: GPU с CUDA — для TComplEx скоринга

## Пошаговый запуск

### 1. Клонировать репозиторий

```bash
git clone <repo_url> && cd personal-ai
```

### 2. Настроить окружение

```bash
cp .env.example .env
# Отредактировать .env: TELEGRAM_BOT_TOKEN, LLM_BACKEND, API-ключи, NEO4J_PASSWORD
```

Ключевые переменные:

| Переменная | Описание |
|------------|----------|
| `TELEGRAM_BOT_TOKEN` | Токен от @BotFather |
| `LLM_BACKEND` | `ollama` \| `yandexgpt` \| `deepseek` \| `gigachat` \| `openai` \| `qwen` |
| `NEO4J_PASSWORD` | Пароль Neo4j |

### 3. Скачать модели (не входят в git)

```bash
# E5-Small finetuned
mkdir -p models/wikidata_finetuned_remote
# Скачать с HuggingFace/S3 → models/wikidata_finetuned_remote/wikidata_finetuned/

# TComplEx checkpoint
mkdir -p models/cronkgqa
# Скопировать: models/cronkgqa/tcomplex.ckpt
```

### 4. Подготовить данные KG

```bash
mkdir -p wikidata_big/kg/tkbc_processed_data/wikidata_big
# Скопировать: full.txt, wd_id2entity_text.txt, wd_id2relation_text.txt
# + ent_id, rel_id, ts_id, train.pickle (для TComplEx)
```

### 5. Запустить контейнеры

```bash
docker compose up --build -d
```

Для локального Ollama:

```bash
docker compose --profile ollama up --build -d
```

### 6. Проверить статус

```bash
docker compose ps
docker logs personal-ai-app-1 --tail=50
# В логах должно быть: "Bot started polling."
```

## Проверка компонентов

**Neo4j Browser:** http://localhost:7474
Логин: `neo4j` / (значение `NEO4J_PASSWORD` из .env)
Проверочный запрос: `MATCH (n) RETURN count(n)`

**ChromaDB API:** http://localhost:8000
```bash
curl http://localhost:8000/api/v1/heartbeat
```

**Telegram бот:**
Отправить `/status` в чат с ботом — должен вернуть статус всех компонентов.

## Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие и инструкция |
| `/ask <вопрос>` | Полный 7-стадийный пайплайн → текстовый ответ |
| `/facts <вопрос>` | Топ-N фактов с оценками confidence |
| `/graph <вопрос>` | 1-hop подграф → PNG изображение |
| `/settings` | Текущие настройки (top_k, confidence) |
| `/set top_k N` | Изменить top_k (1–15) |
| `/set confidence X` | Изменить min_confidence (0.0–1.0) |
| `/status` | Статус Neo4j, ChromaDB, LLM, устройства |
| `/help` | Список всех команд |

## Обновление без простоя

```bash
git pull
docker compose up --build -d --no-deps app
```
