import sys
import json
from pathlib import Path
import pandas as pd
import csv

def generate_data_files(entity_id):
    kg_dir = Path('./wikidata_big/kg')
    print(f"Загрузка справочников для '{entity_id}'...")
    try:
        entity_map = pd.read_csv(kg_dir / 'wd_id2entity_text.txt', sep='\t', header=None, names=['id', 'text'], engine='python', quoting=csv.QUOTE_NONE).set_index('id')['text'].to_dict()
        relation_map = pd.read_csv(kg_dir / 'wd_id2relation_text.txt', sep='\t', header=None, names=['id', 'text'], engine='python', quoting=csv.QUOTE_NONE).set_index('id')['text'].to_dict()
    except Exception as e:
        print(f"Критическая ошибка: Не удалось загрузить файлы карт: {e}")
        return

    print(f"Поиск фактов...")
    related_facts = []
    with open(kg_dir / 'full.txt', 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 3 and entity_id in (parts[0], parts[2]):
                related_facts.append(parts)
    
    if not related_facts:
        print(f"Факты не найдены.")
        with open('nodes.json', 'w', encoding='utf-8') as f: json.dump([], f)
        with open('edges.json', 'w', encoding='utf-8') as f: json.dump([], f)
        return

    print(f"Найдено {len(related_facts)} фактов. Создание nodes.json и edges.json...")
    nodes, edges = [], []
    added_nodes = set()
    for parts in related_facts:
        s, p, o = parts[0], parts[1], parts[2]
        # Аккуратно извлекаем время
        time_str = f"{parts[3]}-{parts[4]}" if len(parts) == 5 else parts[3] if len(parts) == 4 else ""

        if s not in added_nodes:
            is_target = s == entity_id
            nodes.append({'id': s, 'label': entity_map.get(s, s), 'color': '#FF6347' if is_target else '#ADD8E6', 'size': 25 if is_target else 15, 'title': f'ID: {s}'})
            added_nodes.add(s)
        if o not in added_nodes:
            is_target = o == entity_id
            nodes.append({'id': o, 'label': entity_map.get(o, o), 'color': '#FF6347' if is_target else '#ADD8E6', 'size': 25 if is_target else 15, 'title': f'ID: {o}'})
            added_nodes.add(o)
        
        # Добавляем и title для наведения, и отдельное поле time для клика
        edges.append({'from': s, 'to': o, 'label': relation_map.get(p, p), 'time': time_str, 'title': relation_map.get(p, p)})

    with open('nodes.json', 'w', encoding='utf-8') as f: json.dump(nodes, f, ensure_ascii=False)
    with open('edges.json', 'w', encoding='utf-8') as f: json.dump(edges, f, ensure_ascii=False)
    print("Готово!")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python generate_data.py <ENTITY_ID>")
    else:
        generate_data_files(sys.argv[1])