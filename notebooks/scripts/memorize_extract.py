import sys
import json
from tqdm import tqdm
import joblib
import time
import gc
import argparse

# Define the parser
parser = argparse.ArgumentParser(description='Short sample app')

# Declare an argument (`--algo`), saying that the
# corresponding value should be stored in the `algo`
# field, and using a default value if the argument
# isn't given
parser.add_argument('--batch', action="store", dest='batch', default=-1)

# Now, parse the command line arguments and store the
# values in the `args` variable
args = parser.parse_args()

print("used batch in script: ", args.batch)

# TO CHANGE
BASEDIR = "/home/dzigen/Desktop/PersonalAI/Personal-AI/"
# TO CHNAGE

sys.path.insert(0, BASEDIR)
from src.utils.data_structs import RelationType, NodeType
from src.memorize_pipeline.extractor.LLMExtractor import LLMExtractor
from src.agents.private import GigaChatAgent

DATASET_PATH = '../../data/Augment_DiaASQ.json'
SAVE_EXTRACTED_TRIPLETS_FILE = f"./extract_parts/tmp_extracted_gigachat_triplets_batch{args.batch}.dump"
gc.collect()

import os.path
if os.path.exists(SAVE_EXTRACTED_TRIPLETS_FILE):
    print("File exists")
    raise ValueError

###########

print("loading dataset...")

with open(DATASET_PATH, 'r', encoding='utf-8') as fd:
    data = json.loads(fd.read())

raw_texts = list(map(lambda v: v['text_dialog'], data['data']))
raw_time = list(map(lambda v: v['time'].split(',')[0].strip(), data['data']))
print(len(raw_texts), len(raw_time))

print("initing agent and llm-extractor...")

agent = GigaChatAgent()
extractor = LLMExtractor(agent_conn=agent)

###########

BATCH_SIZE = 40
START_DIALOGUE_IDX = int(args.batch) * BATCH_SIZE
END_DIALOGUE_IDX = (int(args.batch)+1) * BATCH_SIZE
if END_DIALOGUE_IDX > len(raw_texts):
    END_DIALOGUE_IDX = len(raw_texts)
    BATCH_SIZE = END_DIALOGUE_IDX - START_DIALOGUE_IDX

print("start extracting triplets...")
print(START_DIALOGUE_IDX, END_DIALOGUE_IDX, BATCH_SIZE)

extracted_triplets = []
for i in tqdm(range(START_DIALOGUE_IDX, END_DIALOGUE_IDX)):
    out = extractor.extract(raw_texts[i])
    extracted_triplets.append(out)

###########

print("adding time to triplets...")

for group_idx in tqdm(range(BATCH_SIZE)):
    cur_time = raw_time[group_idx]
    for triplet_idx in range(len(extracted_triplets[group_idx])):
        if extracted_triplets[group_idx][triplet_idx].relation.type == RelationType.simple:
            extracted_triplets[group_idx][triplet_idx].relation.prop['time'] = cur_time
        else:
            extracted_triplets[group_idx][triplet_idx].end_node.prop['time'] = cur_time
            if extracted_triplets[group_idx][triplet_idx].start_node.type != NodeType.object:
                extracted_triplets[group_idx][triplet_idx].start_node.prop['time'] = cur_time

print("saving triplets...")

print(sum(list(map(len, extracted_triplets))))
joblib.dump(extracted_triplets, SAVE_EXTRACTED_TRIPLETS_FILE)

print("DONE")
