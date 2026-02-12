import torch
import torch.nn as nn
import numpy as np
from typing import List, Dict, Optional, Tuple, Union
from dataclasses import dataclass, field
from src.utils.data_structs import Node, Relation, Quadruplet
from src.utils import Logger
import os

from src.utils.device_utils import get_device

@dataclass
class TComplexConfig:
    """Конфигурация модели TComplEx."""
    num_entities: int = 0
    num_relations: int = 0
    num_timestamps: int = 0
    embedding_dim: int = 100
    reg_weight: float = 0.01
    learning_rate: float = 0.001
    device: str = field(default_factory=get_device)
    log_path: str = 'log/kg_model/temporal'
    model_path: str = 'models/tcomplex.pt'

class TComplexModel(nn.Module):
    """
    Реализация модели TComplEx (Temporal Complex Embeddings) для темпоральных графов знаний.
    Модель разлагает квадруплеты (s, r, o, t) в комплексном пространстве.
    """
    def __init__(self, config: TComplexConfig):
        super(TComplexModel, self).__init__()
        self.config = config
        self.log = Logger(config.log_path)
        self.device = torch.device(config.device)

        self.emb_dim = config.embedding_dim
        
        # Комплексные эмбеддинги представлены как две части (Re, Im)
        self.ent_re = nn.Embedding(config.num_entities, self.emb_dim)
        self.ent_im = nn.Embedding(config.num_entities, self.emb_dim)
        
        self.rel_re = nn.Embedding(config.num_relations, self.emb_dim)
        self.rel_im = nn.Embedding(config.num_relations, self.emb_dim)
        
        self.time_re = nn.Embedding(config.num_timestamps, self.emb_dim)
        self.time_im = nn.Embedding(config.num_timestamps, self.emb_dim)

        self._init_weights()
        self.to(self.device)

    def _init_weights(self):
        """Инициализация весов нормальным распределением."""
        for emb in [self.ent_re, self.ent_im, self.rel_re, self.rel_im, self.time_re, self.time_im]:
            nn.init.normal_(emb.weight, std=0.1)

    def forward(self, s_idx, r_idx, o_idx, t_idx):
        """
        Вычисление скора факта (s, r, o, t).
        Score formula in TComplEx:
        Re < w_s, w_r * w_t, complex_conj(w_o) >
        """
        s_re, s_im = self.ent_re(s_idx), self.ent_im(s_idx)
        r_re, r_im = self.rel_re(r_idx), self.rel_im(r_idx)
        o_re, o_im = self.ent_re(o_idx), self.ent_im(o_idx)
        t_re, t_im = self.time_re(t_idx), self.time_im(t_idx)

        # (w_r * w_t)
        # (r_re + i*r_im) * (t_re + i*t_im) = (r_re*t_re - r_im*t_im) + i*(r_re*t_im + r_im*t_re)
        rt_re = r_re * t_re - r_im * t_im
        rt_im = r_re * t_im + r_im * t_re

        # Re < w_s, (w_r * w_t), conjugate(w_o) >
        # This boils down to:
        # sum( s_re * rt_re * o_re + s_re * rt_im * o_im + s_im * rt_re * o_im - s_im * rt_im * o_re )
        score = torch.sum(s_re * rt_re * o_re + s_re * rt_im * o_im + s_im * rt_re * o_im - s_im * rt_im * o_re, dim=-1)
        return score

    def predict_object(self, s_idx, r_idx, t_idx) -> torch.Tensor:
        """Предсказание объекта для (s, r, ?, t)."""
        with torch.no_grad():
            s_re, s_im = self.ent_re(s_idx), self.ent_im(s_idx)
            r_re, r_im = self.rel_re(r_idx), self.rel_im(r_idx)
            t_re, t_im = self.time_re(t_idx), self.time_im(t_idx)

            rt_re = r_re * t_re - r_im * t_im
            rt_im = r_re * t_im + r_im * t_re

            # Чтобы получить скоры для всех объектов, используем матричное умножение
            # Query vector q = (s_re * rt_re - s_im * rt_im) + i*(s_re * rt_im + s_im * rt_re)
            q_re = s_re * rt_re - s_im * rt_im
            q_im = s_re * rt_im + s_im * rt_re

            # scores = Re(q * conjugate(W_entities))
            # scores = q_re * ent_re^T + q_im * ent_im^T
            scores = torch.matmul(q_re, self.ent_re.weight.t()) + torch.matmul(q_im, self.ent_im.weight.t())
            return scores

    def save_model(self, path: Optional[str] = None):
        save_path = path or self.config.model_path
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        torch.save({
            'state_dict': self.state_dict(),
            'config': self.config
        }, save_path)
        self.log(f"Model saved to {save_path}")

    @classmethod
    def load_model(cls, path: str, device: str = 'cpu'):
        checkpoint = torch.load(path, map_location=device)
        config = checkpoint['config']
        config.device = device
        model = cls(config)
        model.load_state_dict(checkpoint['state_dict'])
        return model

class TemporalReasoner:
    """Обертка над TComplEx моделью для интеграции в Personal-AI."""
    def __init__(self, model: TComplexModel, entity_to_idx: Dict[str, int], rel_to_idx: Dict[str, int], time_to_idx: Dict[str, int]):
        self.model = model
        self.entity_to_idx = entity_to_idx
        self.rel_to_idx = rel_to_idx
        self.time_to_idx = time_to_idx

    def score_fact(self, quadruplet: Quadruplet) -> float:
        """Оценка достоверности квадруплета во времени."""
        s = self.entity_to_idx.get(quadruplet.start_node.id)
        r = self.rel_to_idx.get(quadruplet.relation.id)
        o = self.entity_to_idx.get(quadruplet.end_node.id)
        t = self.time_to_idx.get(quadruplet.time.id) if quadruplet.time else None

        if None in [s, r, o, t]:
            return 0.0
        
        s_t = torch.tensor([s], device=self.model.device)
        r_t = torch.tensor([r], device=self.model.device)
        o_t = torch.tensor([o], device=self.model.device)
        t_t = torch.tensor([t], device=self.model.device)
        
        with torch.no_grad():
            score = self.model(s_t, r_t, o_t, t_t)
        return score.item()
