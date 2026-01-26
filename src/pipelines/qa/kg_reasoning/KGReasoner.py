from dataclasses import dataclass, field
from typing import Tuple, Union
from copy import deepcopy

from .weak_reasoner import WeakKGReasonerConfig
from .config import KGR_MAIN_LOG_PATH, AVAILABLE_KG_REASONERS
from .utils import BaseKGReasonerConfig
from ....utils import ReturnInfo, Logger
from ....kg_model import KnowledgeGraphModel
from ....db_drivers.kv_driver import KeyValueDriverConfig

@dataclass
class KnowledgeGraphReasonerConfig:
    reasoner_name: str = 'weak'
    reasoner_hyperparameters: BaseKGReasonerConfig = field(default_factory=lambda: WeakKGReasonerConfig())

    log: Logger = field(default_factory=lambda: Logger(KGR_MAIN_LOG_PATH))
    verbose: bool = False

class KnowledgeGraphReasoner:
    def __init__(self, kg_model: KnowledgeGraphModel,
                 config: KnowledgeGraphReasonerConfig = KnowledgeGraphReasonerConfig(),
                 cache_kvdriver_config: KeyValueDriverConfig = None):
        self.config = config
        self.reasoner = AVAILABLE_KG_REASONERS[self.config.reasoner_name](
            kg_model, self.config.reasoner_hyperparameters, cache_kvdriver_config)

    def perform(self, query: str) -> Tuple[str, ReturnInfo]:
        answer, info = self.reasoner.perform(query)
        return answer, info
