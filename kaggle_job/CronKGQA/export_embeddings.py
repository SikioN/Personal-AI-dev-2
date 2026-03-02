
import torch
import os
import json

# --- Конфигурация ---
# Пути к файлам проекта
MODEL_PATH = 'models/tcomplex_17dec.ckpt'
ENT_ID_PATH = 'wikidata_big/kg/tkbc_processed_data/wikidata_big/ent_id'
ENT_TEXT_PATH = 'wikidata_big/kg/wd_id2entity_text.txt'
OUTPUT_FILE = 'entity_embeddings.tsv'

# Ключ для тензора эмбеддингов в state_dict модели.
# TComplEx использует комплексные числа (реальная и мнимая часть). Мы будем использовать реальную часть.
EMBEDDING_KEY = 'emb_E_real.weight'

# --- Основной скрипт ---

def export_embeddings():
    """
    Извлекает эмбеддинги сущностей из чекпоинта модели и сохраняет их в TSV файл вместе с метаданными.
    """
    if not os.path.exists(MODEL_PATH):
        print(f"Ошибка: Файл модели не найден по пути: {MODEL_PATH}")
        return

    print(f"Загрузка модели из {MODEL_PATH}...")
    # Загружаем чекпоинт на CPU для универсальности
    try:
        checkpoint = torch.load(MODEL_PATH, map_location=torch.device('cpu'))
    except Exception as e:
        print(f"Ошибка при загрузке файла модели: {e}")
        print("Убедитесь, что у вас установлен PyTorch (`pip install torch`).")
        return

    # Эмбеддинги обычно находятся в 'state_dict'
    if 'state_dict' not in checkpoint:
        print("Ошибка: Ключ 'state_dict' не найден в чекпоинте. Невозможно извлечь эмбеддинги.")
        return
        
    state_dict = checkpoint['state_dict']
    
    if EMBEDDING_KEY not in state_dict:
        print(f"Ошибка: Ключ эмбеддингов '{EMBEDDING_KEY}' не найден в state_dict модели.")
        print(f"Доступные ключи: {list(state_dict.keys())}")
        return
        
    # Получаем эмбеддинги как NumPy массив
    embeddings = state_dict[EMBEDDING_KEY].cpu().numpy()
    num_embeddings = embeddings.shape[0]
    print(f"Найдено {num_embeddings} эмбеддингов.")

    print("Загрузка сопоставлений для сущностей...")
    # Карта: индекс (0, 1, 2...) -> ID из Wikidata (Q123, Q456...)
    index_to_id = {}
    with open(ENT_ID_PATH, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 2:
                index_to_id[int(parts[1])] = parts[0]

    # Карта: ID из Wikidata (Q123) -> человекочитаемый текст ("John Doe")
    id_to_text = {}
    with open(ENT_TEXT_PATH, 'r') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) == 2:
                id_to_text[parts[0]] = parts[1]
    
    print(f"Запись эмбеддингов в файл {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        # Записываем заголовок
        f.write("index\twikidata_id\ttext\tembedding_vector\n")
        
        # Записываем каждый эмбеддинг с его метаданными
        for i in range(num_embeddings):
            wikidata_id = index_to_id.get(i, "UNKNOWN_ID")
            text = id_to_text.get(wikidata_id, "UNKNOWN_TEXT")
            # Преобразуем вектор в строку JSON
            vector_str = json.dumps(embeddings[i].tolist())
            
            f.write(f"{i}\t{wikidata_id}\t{text}\t{vector_str}\n")
            
    print(f"\nГотово! Эмбеддинги успешно экспортированы в {OUTPUT_FILE}")
    print("Каждая строка в файле содержит: индекс, ID из Wikidata, название сущности и вектор в формате JSON.")

if __name__ == '__main__':
    export_embeddings()
