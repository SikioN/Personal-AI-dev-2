from dataclasses import dataclass, field
from ......utils import Logger, ReturnInfo

ENEXTR_MAIN_LOG_PATH = "log/qa/kg_reasoner/medium/entities_extractor/main"


@dataclass
class EntitiesExtractorConfig:
    lang: str = 'auto'
    log: Logger = field(default_factory=lambda: Logger(ENEXTR_MAIN_LOG_PATH))
    verbose: bool = False

    def to_str(self):
        return f"{self.lang}"
