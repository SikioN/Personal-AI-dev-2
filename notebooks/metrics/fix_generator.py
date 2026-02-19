"""
Script to fix generate_qa_dataset.ipynb Cypher query and Logger issue
"""
import json
import os

def fix_logger():
    logger_path = '/Users/nmuravya/Desktop/KG_sber/Personal-AI-dev 2/src/utils/logger.py'
    with open(logger_path, 'r') as f:
        lines = f.readlines()
    
    new_lines = []
    for line in lines:
        if 'os.makedirs(path, exist_ok=True)' in line:
            new_lines.append('        # Fix: If path is a file, create its directory. If directory, create it.\n')
            new_lines.append('        dir_path = os.path.dirname(path) if "." in os.path.basename(path) else path\n')
            new_lines.append('        if dir_path:\n')
            new_lines.append('            os.makedirs(dir_path, exist_ok=True)\n')
        else:
            new_lines.append(line)
            
    with open(logger_path, 'w') as f:
        f.writelines(new_lines)
    print(f"✓ Fixed Logger in {logger_path}")

def fix_notebook():
    nb_path = '/Users/nmuravya/Desktop/KG_sber/Personal-AI-dev 2/notebooks/metrics/generate_qa_dataset.ipynb'
    with open(nb_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)
    
    for cell in nb['cells']:
        if cell.get('id') == 'extract-quadruplets':
            cell['source'] = [
                "def extract_quadruplets_from_neo4j(driver, limit: int = 2000) -> List[Dict]:\n",
                "    \"\"\"\n",
                "    Извлекает квадруплеты из Neo4j.\n",
                "    \"\"\"\n",
                "    # Query matching the actual schema: (s:object)-[r]->(o:object) with optional time node\n",
                "    query = f\"\"\"\n",
                "    MATCH (s:object)-[r]->(o:object)\n",
                "    OPTIONAL MATCH (t:time) WHERE t.str_id = r.time_node_id OR t.str_id = replace(r.time_node_id, '\"', '')\n",
                "    RETURN \n",
                "        s.name as subject,\n",
                "        s.str_id as subject_id,\n",
                "        r.name as relation,\n",
                "        o.name as object,\n",
                "        o.str_id as object_id,\n",
                "        t.name as time_start,\n",
                "        t.str_id as time_id\n",
                "    LIMIT {limit}\n",
                "    \"\"\"\n",
                "    \n",
                "    print(f\"Выполнение запроса к Neo4j (limit={limit})...\")\n",
                "    try:\n",
                "        raw_result = driver.execute_query(query)\n",
                "        \n",
                "        if not raw_result:\n",
                "            print(\"⚠️ Запрос вернул 0 результатов. Проверка наличия любых отношений...\")\n",
                "            fallback_query = \"MATCH ()-[r]->() RETURN count(r) as cnt\"\n",
                "            cnt_res = driver.execute_query(fallback_query)\n",
                "            print(f\"Всего отношений в базе: {cnt_res[0]['cnt'] if cnt_res else 0}\")\n",
                "            \n",
                "            print(\"Проверка меток отношений...\")\n",
                "            labels_query = \"MATCH ()-[r]->() RETURN DISTINCT type(r) LIMIT 5\"\n",
                "            labels_res = driver.execute_query(labels_query)\n",
                "            print(f\"Типы отношений: {[r['type(r)'] for r in labels_res]}\")\n",
                "        \n",
                "        quadruplets = []\n",
                "        for record in raw_result:\n",
                "            time_val = record.get('time_start')\n",
                "            # If time is missing or 'Always', we might skip it for temporal questions but keep for Simple Entity\n",
                "            quad = {\n",
                "                'subject': record.get('subject', 'Unknown'),\n",
                "                'subject_id': record.get('subject_id', ''),\n",
                "                'relation': record.get('relation', 'related_to'),\n",
                "                'object': record.get('object', 'Unknown'),\n",
                "                'object_id': record.get('object_id', ''),\n",
                "                'time_start': time_val if time_val not in [None, 'Always', 'Unknown'] else None,\n",
                "                'time_end': None # End time not explicitly stored in this schema\n",
                "            }\n",
                "            quadruplets.append(quad)\n",
                "        \n",
                "        return quadruplets\n",
                "    \n",
                "    except Exception as e:\n",
                "        print(f'Ошибка при извлечении данных: {e}')\n",
                "        return []\n",
                "\n",
                "# Извлечение данных\n",
                "all_quadruplets = extract_quadruplets_from_neo4j(graph_driver, limit=5000)\n",
                "print(f'\\n✓ Извлечено {len(all_quadruplets)} квадруплетов')\n",
                "\n",
                "# Статистика по наличию времени\n",
                "with_time = [q for q in all_quadruplets if q['time_start']]\n",
                "print(f'✓ Из них с временной меткой: {len(with_time)}')\n",
                "\n",
                "if all_quadruplets:\n",
                "    print('\\nПримеры извлеченных данных:')\n",
                "    for i, quad in enumerate(all_quadruplets[:5], 1):\n",
                "        time_str = quad['time_start'] if quad['time_start'] else 'No Time'\n",
                "        print(f\"{i}. {quad['subject']} --[{quad['relation']}]--> {quad['object']} ({time_str})\")\n"
            ]
    
    with open(nb_path, 'w', encoding='utf-8') as f:
        json.dump(nb, f, ensure_ascii=False, indent=4)
    print(f"✓ Fixed Notebook in {nb_path}")

if __name__ == '__main__':
    fix_logger()
    fix_notebook()
