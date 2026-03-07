from dataclasses import dataclass, field
from typing import Tuple, Union, List

from .config import AAGG_MAIN_LOG_PATH
from ..query_preprocessing.utils import QueryPreprocessingInfo
from ....utils import ReturnInfo, Logger
from ....agents import AgentDriver, AgentDriverConfig
from ....utils.data_structs import create_id


@dataclass
class AnswersAggregatorConfig:
    lang: str = 'auto'
    adriver_config: AgentDriverConfig = field(default_factory=lambda: AgentDriverConfig())

    log: Logger = field(default_factory=lambda: Logger(AAGG_MAIN_LOG_PATH))
    verbose: bool = False

    def to_str(self):
        return f"{self.lang}|{self.adriver_config.to_str()}"


class AnswersAggregator:
    def __init__(self, config: AnswersAggregatorConfig = AnswersAggregatorConfig(),
                 cache_kvdriver_config=None, cache_llm_inference: bool = True) -> None:
        self.config = config
        self.log = self.config.log
        self.verbose = self.config.verbose

    def get_cache_key(self, query_info: QueryPreprocessingInfo, sub_answers: List[str]) -> List[object]:
        str_sub_answers = "|".join(sub_answers)
        return [query_info.to_str(), str_sub_answers, self.config.to_str()]

    def perform(self, query_info: QueryPreprocessingInfo, sub_answers: List[str]) -> Tuple[str, ReturnInfo]:
        self.log("START ANSWERS AGGREGATION...", verbose=self.config.verbose)
        self.log(f"BASE_QUESTION ID: {create_id(query_info.base_query)}", verbose=self.config.verbose)
        final_answer, info = None, ReturnInfo()

        if len(sub_answers) < 1:
            raise ValueError
        elif len(sub_answers) == 1:
            final_answer = sub_answers[0]
        else:
            # Naive aggregation: join sub-answers
            final_answer = " | ".join(sub_answers)

        self.log(f"STATUS: {info.status}", verbose=self.verbose)
        return final_answer, info
