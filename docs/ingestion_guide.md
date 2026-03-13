# Руководство по заполнению Neo4j и ChromaDB

## Первичная загрузка данных

Подготовьте файл `facts.json` в формате S-R-O-T (см. [data_format.md](data_format.md)), затем:

```bash
python scripts/incremental_update.py \
  --input facts.json \
  --tkbc-dir wikidata_big/kg/tkbc_processed_data/wikidata_big/
```

## Что происходит при загрузке

1. **EntityResolver** сопоставляет каждую сущность с существующими в Neo4j (5 уровней: exact_id → exact_neo4j → rapidfuzz ≥ 90 → vector < 0.25 → LLM → LOCAL_)
2. **Backup** .pickle файлов TComplEx (→ .bak)
3. Факты → **Neo4j** (MERGE-запросы, атомарно, без SQL-инъекций)
4. Факты → **ChromaDB** (эмбеддинги E5-Small для узлов и квадруплетов)
5. При ошибке → автоматический **откат** .bak → исходные .pickle

## Варианты запуска

```bash
# Базовое добавление
python scripts/incremental_update.py --input facts.json \
  --tkbc-dir wikidata_big/kg/tkbc_processed_data/wikidata_big/

# С автоматическим переобучением TComplEx
python scripts/incremental_update.py --input facts.json \
  --tkbc-dir wikidata_big/kg/tkbc_processed_data/wikidata_big/ \
  --force-retrain --retrain-epochs 100

# Dry-run (валидация без записи в БД)
python scripts/incremental_update.py --input facts.json --dry-run
```

## Проверка после загрузки

**Neo4j (Cypher):**
```cypher
-- Количество узлов по типам
MATCH (n) RETURN labels(n), count(n)

-- Количество связей по типам
MATCH ()-[r]->() RETURN type(r), count(r)
```

**ChromaDB (Python):**
```python
import chromadb
client = chromadb.PersistentClient(path="data/chroma_nodes")
col = client.get_collection("nodes")
print(f"Nodes in ChromaDB: {col.count()}")
```

**Через Telegram бот:**
```
/status
```
Покажет количество узлов и квадруплетов из Neo4j.

## Важные ограничения

- `relation` не должен содержать пробелы (Neo4j Cypher ограничение). Скрипт автоматически заменяет пробелы на `_`.
- Если сущность уже существует в Neo4j с другим написанием, EntityResolver создаст alias (хранится в `n.aliases`).
- Fulltext-индекс Neo4j (`entity_name_aliases`) ищет по `n.name` и `n.aliases` — синонимы работают автоматически.
