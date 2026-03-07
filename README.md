# Personal-AI KG QA Navigator (Production Engine v3)

Готовая к production система вопросно-ответного поиска поверх графов знаний (Knowledge Graphs) с гибридным Retrieval (Neo4j + ChromaDB), 5-уровневой дедупликацией сущностей (Entity Resolution) и темпоральным скорингом (TComplEx). Система поддерживает произвольные данные и безопасное инкрементальное обновление. Интерфейс — **Telegram-бот**.

## Архитектура системы

Проект реализует **7-уровневый пайплайн** ответов на вопросы:
1. **Extraction**: Извлечение сущностей, типов вопросов и временных рамок с использованием LLM.
2. **Resolution**: 5-уровневое разрешение сущностей (Exact ID → Exact Neo4j → Lexical RapidFuzz → Vector ChromaDB → LLM Disambiguation → Новая сущность `LOCAL_`).
3. **Retrieval**: Поиск соседей в графе (hop 1) для найденных сущностей.
4. **Vector Fallback**: Использование ChromaDB, если в графе ничего не найдено.
5. **Scoring**: Гибридное ранжирование (E5 cosine similarity + Temporal Scorer Pytorch).
6. **Selection**: Отбор релевантных фактов на основе "разрыва уверенности" (Confidence Gap).
7. **Generation**: Генерация финального ответа LLM на базе отобранных "анонимизированных" фактов.

---

## Быстрый старт

```bash
# 1. Клонировать репозиторий
git clone <repo_url> && cd personal-ai

# 2. Настроить окружение
cp .env.example .env
# Указать TELEGRAM_BOT_TOKEN, LLM_BACKEND, NEO4J_PASSWORD и нужные API-ключи

# 3. Запустить через Docker Compose
docker compose up --build -d
```

Подробнее: [docs/deployment.md](docs/deployment.md)

---

## Команды Telegram-бота

| Команда | Действие |
|---------|----------|
| `/ask <вопрос>` | Полный 7-стадийный пайплайн → текстовый ответ |
| `/facts <вопрос>` | Топ-N фактов с оценками confidence |
| `/graph <вопрос>` | 1-hop подграф → PNG изображение |
| `/settings` | Текущие настройки (top_k, confidence) |
| `/set top_k N` | Изменить top_k (1–15) |
| `/set confidence X` | Изменить min_confidence (0.0–1.0) |
| `/status` | Статус Neo4j, ChromaDB, LLM-бэкенда |
| `/help` | Список команд |

---

## Инкрементальное обновление данных

Подготовьте `facts.json` в формате S-R-O-T (см. [docs/data_format.md](docs/data_format.md)):

```bash
python scripts/incremental_update.py --input facts.json \
  --tkbc-dir wikidata_big/kg/tkbc_processed_data/wikidata_big/
```

Подробнее: [docs/ingestion_guide.md](docs/ingestion_guide.md) | [docs/retrain_guide.md](docs/retrain_guide.md)

---

## Структура проекта

```
bot.py                    — точка входа (Telegram-бот)
src/
  bot/
    engine_loader.py      — инициализация QAEngine (singleton)
    handlers.py           — aiogram handlers (/ask, /facts, /graph, ...)
    formatters.py         — форматирование ответов для Telegram MarkdownV2
    graph_renderer.py     — NetworkX + matplotlib → PNG
  llm/                    — клиенты для 6 LLM-бэкендов
  db_drivers/             — Neo4j и ChromaDB коннекторы
  pipelines/qa/           — 7-ступенчатый QA пайплайн (QAEngine)
  pipelines/ingestion/    — EntityResolver, TemporalKGIngester
  config/qa_config.py     — QAConfig (все гиперпараметры)
  utils/kg_navigator.py   — KGNavigator (подграф)
scripts/
  incremental_update.py   — атомарное добавление фактов
  retrain_tcomplex.py     — переобучение TComplEx
docs/
  data_format.md          — формат S-R-O-T квадруплетов
  deployment.md           — развёртывание
  ingestion_guide.md      — заполнение Neo4j/ChromaDB
  retrain_guide.md        — переобучение модели
```

## LLM-бэкенды

Установить переменную `LLM_BACKEND` в `.env`:

| Значение | Переменные |
|----------|-----------|
| `ollama` | `OLLAMA_URL`, `OLLAMA_MODEL` |
| `yandexgpt` | `YANDEX_API_KEY`, `YANDEX_FOLDER_ID`, `YANDEX_MODEL` |
| `deepseek` | `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL` |
| `gigachat` | `GIGACHAT_CREDENTIALS`, `GIGACHAT_MODEL` |
| `openai` | `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_BASE_URL` |
| `qwen` | `QWEN_API_KEY`, `QWEN_MODEL` |
