from abc import  abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Tuple, Union

from ..utils import AbstractDatabaseConnection, BaseDatabaseConfig

@dataclass
class VectorDBConnectionConfig(BaseDatabaseConfig):
    conn: Dict = field(default_factory=lambda: dict())

@dataclass
class VectorDBInstance:
    id: str = None
    document: str = None
    embedding: List[float] = None
    metadata: Dict = field(default_factory=lambda: dict())

    def dict(self):
        return {k: v for k, v in asdict(self).items()}

class AbstractVectorDatabaseConnection(AbstractDatabaseConnection):
    @abstractmethod
    def retrieve(self, query_instances: List[VectorDBInstance], n_results: int = 50, subset_ids: Union[None, List[str]] = None,
                 includes: List[str] = ['embeddings', 'documents', 'metadatas']) -> List[List[Tuple[float, VectorDBInstance]]]:
        # извлечение N ближайших сущностей к данной по заданной метрике
        pass

    @abstractmethod
    def upsert(self, items: List[VectorDBInstance]) -> None:
        pass
