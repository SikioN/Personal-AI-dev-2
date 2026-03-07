# KG QA — Inference & Deployment Guide

## Quick start (Docker)

```bash
cp .env.example .env
# Edit .env with your API keys and Neo4j password

docker compose up --build
```

Open `http://localhost:8501` in your browser.

To also start Ollama (for local LLM):
```bash
docker compose --profile ollama up
```

---

## Choosing an LLM backend

Set `LLM_BACKEND` in `.env` to one of:

| Value | Provider | Required env vars |
|-------|----------|-------------------|
| `ollama` (default) | Local Ollama | `OLLAMA_URL`, `OLLAMA_MODEL` |
| `yandexgpt` | Yandex Cloud | `YANDEX_API_KEY`, `YANDEX_FOLDER_ID`, `YANDEX_MODEL` |
| `deepseek` | DeepSeek API | `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL` |
| `gigachat` | Sber GigaChat | `GIGACHAT_CREDENTIALS`, `GIGACHAT_MODEL` |
| `openai` | OpenAI / compatible | `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_BASE_URL` |
| `qwen` | Alibaba DashScope | `QWEN_API_KEY`, `QWEN_MODEL` |

---

## Adding new facts (incremental update)

1. Prepare `facts.json`:
```json
[
  {"subject": {"name": "Albert Einstein", "id": null},
   "relation": "born_in",
   "object":  {"name": "Ulm", "id": null},
   "time_start": "1879", "time_end": null}
]
```
- `id` can be a Wikidata QID, a custom string, or `null`.
- `time_end` can be `null` (point-in-time fact).

2. Run the incremental update script:
```bash
python scripts/incremental_update.py \
    --input facts.json \
    --tkbc-dir wikidata_big/kg/tkbc_processed_data/wikidata_big/ \
    [--force-retrain] [--retrain-epochs 50] [--dry-run]
```

Flags:
- `--dry-run` — validate and parse without writing to the KG
- `--force-retrain` — retrain TComplEx after ingestion
- `--retrain-epochs N` — number of fine-tuning epochs (default 50)

The script backs up tkbc pickle files before writing and restores them automatically if an error occurs.

---

## Retraining TComplEx separately

```bash
python scripts/retrain_tcomplex.py \
    --tkbc-dir wikidata_big/kg/tkbc_processed_data/wikidata_big/ \
    --epochs 50
```

The retrained checkpoint is saved as `tcomplex_retrained.ckpt` inside `--tkbc-dir`.

---

## Entity resolution levels (ingestion)

When adding new facts, entities are resolved in this priority order:

| Level | Method | Trigger condition |
|-------|--------|-------------------|
| L1 | Exact ID hint | `id` field provided and found in Neo4j |
| L2 | Exact Neo4j name match | Case-insensitive name lookup |
| L2.5 | Rapidfuzz lexical | `token_sort_ratio ≥ 90` vs top-10 candidates |
| L3 | ChromaDB ANN | Cosine distance `< 0.25` |
| L4 | LLM disambiguation | Distance `0.25–0.45` |
| L5 | New entity (LOCAL_) | No match found — deterministic `MD5(name+type)[:10]` |

Re-ingesting the same entity always yields the same `LOCAL_` ID (deduplication by name match), not a duplicate node.

---

## QA pipeline stages

The `engine.ask(question)` method runs 7 stages:

1. **ExtractionStage** — LLM extracts entities, question type, alpha, time filter
2. **Config** — ExtractionResult sets search parameters
3–4. **HybridRetriever** — HOP 1 entity resolution + Neo4j BFS + ChromaDB ANN
5. **ScoringStage** — E5 cosine + TComplEx scores; P3 confidence-gap selection
6. *(skipped)* — gap selection replaces the LLM fact-selection call
7. **GenerationStage** — anonymised question + context → LLM → answer

For visualisation only (Streamlit subgraph view), use `engine.get_ranked_results(query)`.

---

## Neo4j — useful Cypher queries

```cypher
-- Count nodes / quadruplets
MATCH (a) RETURN count(a) AS nodes;
MATCH ()-[r]->() RETURN count(r) AS quadruplets;

-- Search by entity name
MATCH (n) WHERE toLower(n.name) CONTAINS "einstein" RETURN n.name, n.str_id LIMIT 10;

-- Find quadruplets for an entity
MATCH (n {str_id: "Q937"})-[r]-(m)
OPTIONAL MATCH (t:time) WHERE t.str_id = r.time_node_id
RETURN n.name, r.name, m.name, t.name;

-- Search by alias
CALL db.index.fulltext.queryNodes("entity_name_aliases", "Einstein")
YIELD node RETURN node.name, node.str_id LIMIT 10;
```
