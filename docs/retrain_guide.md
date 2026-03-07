# Переобучение TComplEx на новых данных

## Когда переобучать?

- После добавления > 1000 новых квадруплетов
- При значительном изменении временного диапазона данных
- Если temporal_score в `/facts` перестал коррелировать с правильными ответами

## Автоматическое переобучение (рекомендуется)

```bash
python scripts/incremental_update.py \
  --input facts.json \
  --tkbc-dir wikidata_big/kg/tkbc_processed_data/wikidata_big/ \
  --force-retrain \
  --retrain-epochs 100
```

## Ручное переобучение

```bash
python scripts/retrain_tcomplex.py \
  --tkbc-dir wikidata_big/kg/tkbc_processed_data/wikidata_big/ \
  --checkpoint models/cronkgqa/tcomplex.ckpt \
  --epochs 100 \
  --batch-size 1000
```

## Формат данных для TComplEx

Файлы генерируются автоматически `incremental_update.py`:

| Файл | Тип | Описание |
|------|-----|----------|
| `ent_id` | `dict[str, int]` | Имя сущности → числовой ID |
| `rel_id` | `dict[str, int]` | Имя отношения → числовой ID |
| `ts_id` | `dict[str, int]` | Временная метка → числовой ID |
| `train.pickle` | `list[tuple]` | `(s_id, r_id, o_id, ts_start_id, ts_end_id)` |

## Проверка качества переобучения

После переобучения отправьте в бот несколько вопросов с `/facts` и проверьте:
- `temporal_score` в топ-фактах должен быть > 0.5 для правильных ответов
- Факты с корректным временным диапазоном должны ранжироваться выше

## GPU ускорение

TComplEx автоматически использует CUDA при наличии GPU. Для принудительного использования CPU:

```bash
CUDA_VISIBLE_DEVICES="" python scripts/retrain_tcomplex.py ...
```
