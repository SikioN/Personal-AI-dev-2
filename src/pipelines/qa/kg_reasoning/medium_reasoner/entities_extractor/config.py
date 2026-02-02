from .agent_tasks.entities_extractor import AgentEntitiesExtrTaskConfigSelector
from dataclasses import dataclass, field
from ......agents import AgentDriverConfig
from ......utils import Logger, AgentTaskSolverConfig

ENEXTR_MAIN_LOG_PATH = "log/qa/kg_reasoner/medium/entities_extractor/main"
DEFAULT_ENT_EXTR_TASK_CONFIG = AgentEntitiesExtrTaskConfigSelector.select(base_config_version='v1')

@dataclass
class EntitiesExtractorConfig:
    lang: str = 'auto'
    adriver_config: AgentDriverConfig = field(default_factory=lambda: AgentDriverConfig())
    entities_extraction_agent_task_config: AgentTaskSolverConfig = field(default_factory=lambda: DEFAULT_ENT_EXTR_TASK_CONFIG)

    cache_table_name: str = "medreasn_entextr_main_stage_cache"
    log: Logger = field(default_factory=lambda: Logger(ENEXTR_MAIN_LOG_PATH))
    verbose: bool = False

    def to_str(self):
        return f"{self.lang}|{self.adriver_config.to_str()}|{self.entities_extraction_agent_task_config.version}"