# Запуск Personal-AI на Mac: Краткая инструкция

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
# Создать виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# Установить зависимости для Mac
pip install -r deployment/requirements_mac.txt
```

### 2. Запуск блокнота `wikidata_metrics.ipynb`

```bash
jupyter notebook notebooks/metrics/wikidata_metrics.ipynb
```

Блокнот автоматически определит оптимальное устройство:
- **MPS** (Apple Silicon GPU) — если доступен
- **CPU** — fallback

## 📝 Изменения для Mac

### Созданные файлы:
- `deployment/requirements_mac.txt` — зависимости без NVIDIA пакетов (200 вместо 213)
- `src/utils/device_utils.py` — утилита автоопределения устройства

### Обновленные файлы:
- `src/kg_model/embeddings_model.py` — поддержка MPS
- `src/kg_model/nodestree_model/NodesTreeModel.py` — поддержка MPS
- `notebooks/metrics/wikidata_metrics.ipynb` — автоопределение устройства

## ✅ Всё готово для GitHub

Все необходимые файлы добавлены в Git и готовы к коммиту:
```bash
git commit -m "Add Mac support: requirements_mac.txt, device auto-detection (MPS/CPU)"
git push
```

## 📚 Документация

Полная документация: `mac_installation_guide.md` в артефактах
