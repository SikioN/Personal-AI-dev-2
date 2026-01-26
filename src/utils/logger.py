import os
import sys
import json
import logging
import torch
import datetime

LOGGER = logging.getLogger(__name__)

def init_logger(args, stdout_only=False):
    if torch.distributed.is_initialized():
        torch.distributed.barrier()
    stdout_handler = logging.StreamHandler(sys.stdout)
    handlers = [stdout_handler]
    if not stdout_only:
        file_handler = logging.FileHandler(filename=os.path.join(args.output_dir, "run.log"))
        handlers.append(file_handler)
    logging.basicConfig(
        datefmt="%m/%d/%Y %H:%M:%S",
        level=logging.INFO,
        format="[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s",
        handlers=handlers,
    )
    return LOGGER

class Logger:
    def __init__(self, path):
        self.path = path
        os.makedirs(path, exist_ok=True)

    def __call__(self, text, filename = "log.txt", verbose = True, debug=True):
        if debug:
            text = str(text)
            if verbose:
                print(text)
            with open(self.path + "/" + filename, "a") as file:
                file.write(f"[{str(datetime.datetime.now())}] {text}\n")

    def to_json(self, obj, filename = "history.json"):
        try:
            with open(self.path + "/" + filename, "w") as file:
                json.dump(obj, file)
        except:
            raise "Object isn't json serializible"
