import re
from dataclasses import dataclass, field
from typing import Tuple, Union, List, Dict

from .config import ENEXTR_MAIN_LOG_PATH, EntitiesExtractorConfig
from ......utils import ReturnInfo, Logger
from ......utils.errors import ReturnStatus
from ......utils.data_structs import create_id


class EntitiesExtractor:
    """Simple regex-based entity extractor (legacy LLM extractor removed; real extraction is in ExtractionStage)."""

    def __init__(self, config: EntitiesExtractorConfig = EntitiesExtractorConfig(),
                 cache_kvdriver_config=None, cache_llm_inference: bool = True):
        self.config = config
        self.log = self.config.log
        self.verbose = self.config.verbose

    def perform(self, query: str) -> Tuple[Dict[str, Union[List[str], Union[str, None]]], ReturnInfo]:
        self.log("START ENTITIES EXTRACTION (regex fallback)...", verbose=self.config.verbose)
        info = ReturnInfo()
        self.log(f"QUERY: {query}", verbose=self.config.verbose)

        # Simple heuristic: capitalised words as entities
        entities = list(set(re.findall(r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*', query)))
        extraction_result = {"entities": entities, "time": None}

        if len(entities) < 1:
            info.status = ReturnStatus.empty_answer

        self.log(f"RESULT: {extraction_result}", verbose=self.verbose)
        return extraction_result, info
