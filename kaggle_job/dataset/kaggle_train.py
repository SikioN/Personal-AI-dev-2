import argparse
import torch
from torch import optim
import os
import numpy as np
import pickle
import time
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

    dataset = TemporalDataset(args.dataset)
    sizes = dataset.get_shape()
    print(f"Sizes (entities, predicates, entities, timestamps): {sizes}")

    model = TComplEx(sizes, args.rank, no_time_emb=args.no_time_emb)
    model = model.to(device)

    opt = optim.Adagrad(model.parameters(), lr=args.learning_rate)
    emb_reg = N3(args.emb_reg)
    time_reg = Lambda3(args.time_reg)

    print("Starting training loop...")
    for epoch in range(args.max_epochs):
        epoch_start = time.time()
        examples = torch.from_numpy(dataset.get_train().astype('int64'))
        model.train()
        
        optimizer = TKBCOptimizer(
            model, emb_reg, time_reg, opt,
            batch_size=args.batch_size
        )
        optimizer.epoch(examples)
        
        epoch_time = time.time() - epoch_start
        if (epoch + 1) % args.valid_freq == 0:
            print(f"Epoch {epoch+1}/{args.max_epochs} | Time: {epoch_time:.2f}s")
            
    total_time = time.time() - start_time
    print(f"Training finished. Total time took {total_time / 60:.2f} minutes.")

    # SAVE
    os.makedirs(args.save_dir, exist_ok=True)
    save_path = os.path.join(args.save_dir, 'tcomplex_extended.ckpt')
    torch.save(model.state_dict(), save_path)
    print(f"KGE Model saved to {save_path}")

if __name__ == "__main__":
    main()
