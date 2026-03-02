import torch
from typing import Tuple, Dict

class TKBCModel(torch.nn.Module):
    def get_rhs(self, chunk_begin: int, chunk_size: int):
        raise NotImplementedError

    def get_queries(self, queries: torch.Tensor):
        raise NotImplementedError

    def score(self, x: torch.Tensor):
        raise NotImplementedError

    def forward(self, x: torch.Tensor):
        raise NotImplementedError

    @staticmethod
    def get_params(arg_dict: Dict):
        raise NotImplementedError
