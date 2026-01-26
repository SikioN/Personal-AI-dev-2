from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

MODEL_NAME = 'Undi95/Meta-Llama-3-8B-Instruct-hf'
SAVE_PATH = '../models/Undi95/Meta-Llama-3-8B-Instruct-hf'

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME, torch_dtype=torch.bfloat16).to('cuda')

tokenizer.save_pretrained(SAVE_PATH)
model.save_pretrained(SAVE_PATH)
