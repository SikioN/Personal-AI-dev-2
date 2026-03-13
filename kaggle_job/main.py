import os
import subprocess
import shutil

def run_cmd(cmd):
    print(f"Running: {cmd}")
    subprocess.run(cmd, shell=True, check=True)

def find_dir_with_file(start_path, target_file):
    """Recursively search for a directory containing a specific file."""
    for root, dirs, files in os.walk(start_path):
        if target_file in files:
            return root
    return None

def main():
    print("Starting TComplEx Kaggle Job (v6)...")
    
    # Kaggle starts in /kaggle/working/
    base_dir = os.getcwd()
    print("Base Dir:", base_dir)
    
    # Клонируем в папку repo
    if os.path.exists("repo"):
        shutil.rmtree("repo")
    
    run_cmd("git clone -b feature/qa_experiments_update https://github.com/SikioN/Personal-AI-dev-2.git repo")
    
    # Находим CronKGQA динамически
    cronkgqa_dir = find_dir_with_file(os.path.join(base_dir, "repo"), "setup_tkbc.py")
    
    if not cronkgqa_dir:
        raise FileNotFoundError("Could not find setup_tkbc.py inside the cloned repo!")
        
    print(f"Found CronKGQA at: {cronkgqa_dir}")
    os.chdir(cronkgqa_dir)

    # Установка tkbc
    print("Installing tkbc...")
    run_cmd("pip install -r requirements_tkbc.txt")
    run_cmd("python setup_tkbc.py install")
    
    # Возвращаемся в корень склонированного репозитория (там где kaggle_train.py)
    repo_root = find_dir_with_file(os.path.join(base_dir, "repo"), "kaggle_train.py")
    if not repo_root:
        raise FileNotFoundError("Could not find kaggle_train.py inside the cloned repo!")
    
    os.chdir(repo_root)
    print(f"Changed Dir back to repo root: {os.getcwd()}")

    # Слияние оригинального датасета с out.json
    print("Merging out.json into dataset...")
    
    # by looking for 'ent_id' instead of 'train.pickle' because Kaggle dataset has multiple train.pickle files 
    # (one for QA questions, one for KGE graph). Only the KGE graph folder has 'ent_id'.
    dataset_base = find_dir_with_file("/kaggle/input", "ent_id")
    if not dataset_base:
        raise FileNotFoundError("Could not find ent_id inside /kaggle/input. Did you attach the dataset?")
    
    print(f"Found original dataset at: {dataset_base}")
    # dataset_base points to something like /kaggle/input/wikidata-big-sber/wikidata_big/kg/tkbc_processed_data/wikidata_big/
    
    run_cmd(f"python scripts/merge_out_json.py "
            f"--json_file out.json "
            f"--baseline_dir {dataset_base}/ "
            f"--out_dir data/wikidata_extended/kg/tkbc_processed_data/wikidata_extended/")
    
    # Запуск 100 эпох TComplEx
    print("Running TComplEx training...")
    run_cmd("python kaggle_train.py --dataset wikidata_extended --model TComplEx --max_epochs 100 --save_dir /kaggle/working/models")

    print("Kaggle Training Process Finished!")

if __name__ == "__main__":
    main()
