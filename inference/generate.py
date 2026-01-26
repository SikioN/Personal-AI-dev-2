import sys 
sys.path.insert(0, '/app')

from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Dict
import json
from torch.utils.data import Dataset
from tqdm import tqdm
import gc
import torch

from src.agent_model import AgentModel

class ReaderInputDataset(Dataset):
    def __init__(self,user_prompts, system_prompt: str, template_pipe_func):
        self.user_prompts = user_prompts
        self.sys_prompt = system_prompt
        self.teplate = template_pipe_func
    
    def __len__(self):
        return len(self.user_prompts)

    def __getitem__(self, i):
        messages = [
            {"role": "system", "content": self.sys_prompt},
            {"role": "user","content": self.user_prompts[i]}
            ]
        return self.teplate(
            messages, tokenize=False, add_generation_prompt=True)

agent = AgentModel()

PROMPTS_FILE = 'user_prompts.json'
PARAMS_FILE = 'hyperp.json'
SAVE_FILE = 'generated_output.json'

with open(PROMPTS_FILE, 'r', encoding='utf-8') as fd:
    inputs = json.loads(fd.read())

with open(PARAMS_FILE, 'r', encoding='utf-8') as fd:
    params = json.loads(fd.read())

def post_proc(running_pipe):
    for out in running_pipe:
        proc_out = [item['generated_text'].strip() for item in out]
        yield proc_out

dataset = ReaderInputDataset(inputs, params["system_prompt"], 
                             agent.pipeline.tokenizer.apply_chat_template)

generated_out = []
terminators = [
    agent.pipeline.tokenizer.eos_token_id,
    agent.pipeline.tokenizer.convert_tokens_to_ids("<|eot_id|>")
]
pipe = post_proc(agent.pipeline(
            dataset, return_full_text=False, batch_size=1,
            eos_token_id=terminators,
            pad_token_id=agent.pipeline.tokenizer.eos_token_id, 
            **params['gen_strat']))
display_iter = 1
for i, out in tqdm(enumerate(pipe)):
    
    generated_out.append(out)

    if i % display_iter == 0:
        print(f"{out}")

with open(SAVE_FILE, 'w', encoding='utf-8') as fd:
    fd.write(json.dumps(generated_out, ensure_ascii=False, indent=1))