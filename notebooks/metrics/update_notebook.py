"""
Script to add dataset loader functionality to qa_metrics_evaluation.ipynb
"""
import json

def update_metrics_notebook():
    nb_path = '/Users/nmuravya/Desktop/KG_sber/Personal-AI-dev 2/notebooks/metrics/qa_metrics_evaluation.ipynb'
    
    with open(nb_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)
    
    # Find the section2-header cell (index 3 in the cells array based on the file)
    # We'll insert a new cell after it
    
    new_loader_cell = {
        "cell_type": "code",
        "execution_count": None,
        "id": "load-dataset",
        "metadata": {},
        "outputs": [],
        "source": [
            "import json\n",
            "\n",
            "# Настройка: установите True для использования сгенерированного датасета\n",
            "USE_GENERATED_DATASET = True\n",
            "\n",
            "if USE_GENERATED_DATASET:\n",
            "    dataset_path = '../../data/qa_test_dataset_1000.json'\n",
            "    try:\n",
            "        with open(dataset_path, 'r', encoding='utf-8') as f:\n",
            "            test_questions = json.load(f)\n",
            "        print(f'✓ Загружен сгенерированный датасет: {len(test_questions)} вопросов')\n",
            "        print(f'  Файл: {dataset_path}')\n",
            "    except FileNotFoundError:\n",
            "        print(f'⚠️ Файл {dataset_path} не найден.')\n",
            "        print('  Запустите generate_qa_dataset.ipynb для генерации датасета.')\n",
            "        print('  Переключаюсь на базовый набор из 7 примеров...')\n",
            "        USE_GENERATED_DATASET = False\n",
            "\n",
            "if not USE_GENERATED_DATASET:\n",
            "    print('Используется базовый набор из 7 примеров')\n",
            "    test_questions = None  # Будет заполнено в следующей ячейке"
        ]
    }
    
    # Update section 2 header to mention both options
    for idx, cell in enumerate(nb['cells']):
        if cell.get('id') == 'section2-header':
            cell['source'] = [
                "## 2. Тестовый датасет вопросов\n",
                "\n",
                "Загружаем датасет вопросов. Можно использовать:\n",
                "1. Сгенерированный датасет из ~1000 вопросов (`data/qa_test_dataset_1000.json`)\n",
                "2. Базовый набор из 7 примеров (по умолчанию)"
            ]
            # Insert new loader cell after this one
            nb['cells'].insert(idx + 1, new_loader_cell)
            break
    
    # Update the test-dataset cell to check if test_questions is None
    for cell in nb['cells']:
        if cell.get('id') == 'test-dataset':
            # Prepend conditional check
            cell['source'][0] = "# Базовый датасет (используется только если не загружен сгенерированный)\nif test_questions is None:\n    test_questions = [\n"
            # Update the last lines to close the if statement
            for i in range(len(cell['source']) - 1, 0, -1):
                if ']' in cell['source'][i] and 'test_questions' not in cell['source'][i]:
                    cell['source'][i] = cell['source'][i].replace(']', '    ]')
                    break
            break
    
    # Save updated notebook
    with open(nb_path, 'w', encoding='utf-8') as f:
        json.dump(nb, f, ensure_ascii=False, indent=4)
    
    print(f'✓ Notebook updated: {nb_path}')

if __name__ == '__main__':
    update_metrics_notebook()
