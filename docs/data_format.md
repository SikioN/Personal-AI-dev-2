# Формат входных данных: S-R-O-T квадруплеты

Система принимает **темпоральные квадруплеты** (Subject–Relation–Object–Time) в формате JSON.

## Структура файла

```json
[
  {
    "subject": {
      "name": "Альберт Эйнштейн",
      "id": "Q937"
    },
    "relation": "lived_in",
    "object": {
      "name": "США",
      "id": "Q30"
    },
    "time_start": "1933",
    "time_end": "1955"
  },
  {
    "subject": {
      "name": "Apple Vision Pro",
      "id": null
    },
    "relation": "released_in",
    "object": {
      "name": "2024",
      "id": null
    },
    "time_start": "2024",
    "time_end": null
  }
]
```

## Правила

| Поле | Обязательно | Описание |
|------|-------------|----------|
| `subject.name` | Да | Имя субъекта (любая строка) |
| `subject.id` | Нет | Wikidata ID (напр. `Q937`). Если `null` → система генерирует `LOCAL_<hash>` |
| `relation` | Да | `snake_case` или `CamelCase` **без пробелов**. Пример: `lived_in`, `memberOf`. Строки с пробелами вызовут ошибку Cypher в Neo4j. `incremental_update.py` автоматически заменяет пробелы на `_` |
| `object.name` | Да | Имя объекта |
| `object.id` | Нет | Wikidata ID или `null` |
| `time_start` | Нет | Год `"YYYY"` или дата `"YYYY-MM-DD"` или `null` (неизвестно) |
| `time_end` | Нет | `null` означает «по сей день» |

## Дедупликация сущностей

Система автоматически дедуплицирует сущности через 5-уровневый `EntityResolver`:

1. **L1 exact_id** — совпадение по Wikidata ID
2. **L2 exact_neo4j** — точное совпадение имени в Neo4j
3. **L2.5 lexical** — rapidfuzz ≥ 90% (опечатки, разные написания)
4. **L3 vector** — косинусное расстояние < 0.25 (семантически близкие)
5. **L4 LLM** — уточнение через языковую модель
6. **L5 new** — создать новую сущность с ID `LOCAL_<hash>`

Одно и то же имя всегда получает один ID — дубликатов не возникает.

## Пример минимального факта

```json
[
  {
    "subject": {"name": "Пушкин", "id": null},
    "relation": "wrote",
    "object": {"name": "Евгений Онегин", "id": null},
    "time_start": "1823",
    "time_end": "1831"
  }
]
```
