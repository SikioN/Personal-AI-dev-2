from dataclasses import dataclass, field
from sentence_transformers import SentenceTransformer
from typing import Dict, List

from src.utils.device_utils import get_device

@dataclass
class EmbedderModelConfig:
    model_name_or_path: str = 'intfloat/multilingual-e5-small'
    prompts: Dict = field(default_factory=lambda: {"query": "query: ", "document": "passage: "})
    device: str = field(default_factory=get_device)
    normalize_embeddings: bool = True

class EmbedderModel:

    def __init__(self, config: EmbedderModelConfig = None) -> None:
        self.config = EmbedderModelConfig() if config is None else config
        # Don't pass prompts= to SentenceTransformer — older versions don't support it
        self.model = SentenceTransformer(
            config.model_name_or_path, device=config.device
        )
        self._query_prefix = config.prompts.get("query", "query: ")
        self._doc_prefix = config.prompts.get("document", "passage: ")

    def encode(self, queries: List[str], **kwargs) -> List[List[float]]:
        output = self.model.encode(
            queries, normalize_embeddings=self.config.normalize_embeddings, **kwargs)
        return [list(obj.astype(float)) for obj in output]

    def encode_queries(self, queries: List[str], **kwargs) -> List[List[float]]:
        # Prepend E5 query prefix manually (compatible with all sentence-transformers versions)
        prefixed = [self._query_prefix + q for q in queries]
        output = self.model.encode(
            prefixed, normalize_embeddings=self.config.normalize_embeddings, **kwargs)
        return [list(obj.astype(float)) for obj in output]

    def encode_passages(self, passages: List[str], **kwargs) -> List[List[float]]:
        # Prepend E5 passage prefix manually
        prefixed = [self._doc_prefix + p for p in passages]
        output = self.model.encode(
            prefixed, normalize_embeddings=self.config.normalize_embeddings, **kwargs)
        return [list(obj.astype(float)) for obj in output]
