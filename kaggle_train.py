import argparse
import torch
from torch import optim
import os
import numpy as np
import pickle
import time
import psutil
from collections import defaultdict

# Add tkbc to path if needed (Assuming we are in CronKGQA folder on Kaggle)
import sys
if 'tkbc' not in sys.path:
    sys.path.append('tkbc')

from tkbc.datasets import TemporalDataset
from tkbc.optimizers import TKBCOptimizer
from tkbc.models import TComplEx
from tkbc.regularizers import N3, Lambda3

def main():
    parser = argparse.ArgumentParser(description="Kaggle TComplEx retraining")
    parser.add_argument("--dataset", type=str, default="wikidata_extended", help="Dataset name")
    parser.add_argument("--model", type=str, default="TComplEx", help="Model name")
    parser.add_argument("--max_epochs", type=int, default=100, help="Number of training epochs")
    parser.add_argument("--valid_freq", type=int, default=10, help="Validation frequency")
    parser.add_argument("--rank", type=int, default=200, help="Model rank")
    parser.add_argument("--batch_size", type=int, default=1000, help="Batch size")
    parser.add_argument("--learning_rate", type=float, default=0.05, help="Learning rate")
    parser.add_argument("--emb_reg", type=float, default=0.005, help="Embedding regularizer weight")
    parser.add_argument("--time_reg", type=float, default=0.005, help="Time regularizer weight")
    parser.add_argument("--no_time_emb", action='store_true', help="Disable time embeddings")
    parser.add_argument("--save_dir", type=str, default="/kaggle/working/models", help="Save directory")
    args = parser.parse_args()

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Training {args.model} on {args.dataset} using {device}...")
    
    start_time = time.time()

    # Monkeypatch TemporalDataset to read from the current working directory
    # instead of tkbc's __file__ location from pip install.
    original_init = TemporalDataset.__init__
    
    def custom_init(self, name: str):
        # Instead of __file__, use our current working directory where data/ is created
        project_root = os.getcwd()
        DATA_PATH = os.path.join(project_root, f'data/{name}/kg/tkbc_processed_data/')
        self.root = os.path.join(DATA_PATH, name)
        
        self.data = {}
        import pickle
        import torch
        for f in ['train', 'test', 'valid']:
            in_file = open(os.path.join(self.root, f + '.pickle'), 'rb')
            self.data[f] = pickle.load(in_file)

        maxis = np.max(self.data['train'], axis=0)
        self.n_entities = int(max(maxis[0], maxis[2]) + 1)
        self.n_predicates = int(maxis[1] + 1)
        self.n_predicates *= 2

        if maxis.shape[0] > 4:
            self.n_timestamps = max(int(maxis[3] + 1), int(maxis[4] + 1))
        else:
            self.n_timestamps = int(maxis[3] + 1)
            
        try:
            inp_f = open(os.path.join(self.root, 'ts_diffs.pickle'), 'rb')
            self.time_diffs = torch.from_numpy(pickle.load(inp_f)).cuda().float()
            inp_f.close()
        except OSError:
            print("Assume all timestamps are regularly spaced")
            self.time_diffs = None

        try:
            e = open(os.path.join(self.root, 'event_list_all.pickle'), 'rb')
            self.events = pickle.load(e)
            e.close()

            f = open(os.path.join(self.root, 'ts_id'), 'rb')
            dictionary = pickle.load(f)
            f.close()
            self.timestamps = sorted(dictionary.keys())
            self.n_timestamps = len(self.timestamps)
            print('Changed number of timestamps (from default script)')
            print('Number of entity, rel, time')
            print(self.n_entities, self.n_predicates, self.n_timestamps)
        except OSError:
            print("Not using time intervals and events eval")
            self.events = None

        if self.events is None:
            inp_f = open(os.path.join(self.root, 'to_skip.pickle'), 'rb')
            self.to_skip = pickle.load(inp_f)
            inp_f.close()
            
    # Apply monkeypatch
    TemporalDataset.__init__ = custom_init

    dataset = TemporalDataset(args.dataset)
    sizes = dataset.get_shape()
    train_split_len = len(dataset.get_train())
    print(f"Sizes (entities, predicates, entities, timestamps): {sizes}")
    print(f"Total quadruplets in train split: {train_split_len}")

    model = TComplEx(sizes, args.rank, no_time_emb=args.no_time_emb)
    model = model.to(device)

    # Initializing Report Content
    gpu_info = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "None CPU"
    ram_info = f"{psutil.virtual_memory().total / (1024**3):.2f} GB"
    report = [
        "========================================",
        "TComplEx Retraining Report (Kaggle)",
        "========================================",
        f"Dataset: {args.dataset}",
        f"Model: {args.model}",
        f"Max Epochs: {args.max_epochs}",
        f"Learning Rate: {args.learning_rate}",
        f"Batch Size: {args.batch_size}",
        "----------------------------------------",
        f"System RAM: {ram_info}",
        f"GPU Device: {gpu_info}",
        "----------------------------------------",
        f"Dictionary Sizes: {sizes}",
        f"Total Train Quadruplets: {train_split_len}",
        "----------------------------------------",
    ]

    opt = optim.Adagrad(model.parameters(), lr=args.learning_rate)
    emb_reg = N3(args.emb_reg)
    time_reg = Lambda3(args.time_reg)

    print("Starting training loop...")
    loss_history = []
    
    for epoch in range(args.max_epochs):
        epoch_start = time.time()
        examples = torch.from_numpy(dataset.get_train().astype('int64'))
        model.train()
        
        optimizer = TKBCOptimizer(
            model, emb_reg, time_reg, opt,
            batch_size=args.batch_size
        )
        
        # Capture the final loss of the epoch by parsing tqdm output conceptually
        # We will track loss by monkeypatching the progress bar temporarily or just calculating it manually.
        # But for simplicity, we just rely on running the epoch.
        optimizer.epoch(examples)
        
        epoch_time = time.time() - epoch_start
        if (epoch + 1) % args.valid_freq == 0:
            print(f"Epoch {epoch+1}/{args.max_epochs} | Time: {epoch_time:.2f}s")
            # We don't have direct access to loss from the TKBCOptimizer without rewriting it, 
            # but we know it prints it. We will append a generic marker to the report.
            loss_history.append(f"Epoch {epoch+1}: Completed in {epoch_time:.2f}s")
            
    total_time = time.time() - start_time
    total_time_mins = total_time / 60
    print(f"Training finished. Total time took {total_time_mins:.2f} minutes.")

    # SAVE MODEL
    os.makedirs(args.save_dir, exist_ok=True)
    save_path = os.path.join(args.save_dir, 'tcomplex_extended.ckpt')
    torch.save(model.state_dict(), save_path)
    print(f"KGE Model saved to {save_path}")

    # SAVE REPORT
    report.append("--- Training Progress ---")
    report.extend(loss_history)
    report.append(f"Total Runtime: {total_time_mins:.2f} minutes")
    report_file = os.path.join(args.save_dir, 'training_report.txt')
    with open(report_file, 'w') as f:
        f.write("\n".join(report))
    print(f"Execution report saved to {report_file}")

if __name__ == "__main__":
    main()
