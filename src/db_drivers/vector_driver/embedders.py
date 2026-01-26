from dataclasses import dataclass, field
from sentence_transformers import SentenceTransformer
from typing import Dict, List

@dataclass
class EmbedderModelConfig:
    model_name_or_path: str = '../models/intfloat/multilingual-e5-small'
    prompts: Dict = field(default_factory=lambda: {"query": "query: ", "passage": "passage: "})
    device: str = 'cuda'
    normalize_embeddings: bool = True

class EmbedderModel:

    def __init__(self, config: EmbedderModelConfig = None) -> None:
        self.config = EmbedderModelConfig() if config is None else config
        self.model = SentenceTransformer(
            config.model_name_or_path, device=config.device,
            prompts=config.prompts
        )

    def encode(self, queries: List[str], **kwargs) -> List[List[float]]:
        output = self.model.encode(
            queries, normalize_embeddings=self.config.normalize_embeddings, **kwargs)
        return [list(obj.astype(float)) for obj in output]

    def encode_queries(self, queries: List[str], **kwargs) -> List[List[float]]:
        output = self.model.encode(queries, prompt_name='query',
                                 normalize_embeddings=self.config.normalize_embeddings, **kwargs)
        return [list(obj.astype(float)) for obj in output]

    def encode_passages(self, passages: List[str], **kwargs) -> List[List[float]]:
        output = self.model.encode(passages, prompt_name='passage',
                                 normalize_embeddings=self.config.normalize_embeddings,
                                 **kwargs)
        return [list(obj.astype(float)) for obj in output]
