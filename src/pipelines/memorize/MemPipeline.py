from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from .configs import MEMORIZE_MAIN_LOG_PATH
from .extractor.LLMExtractor import LLMExtractor
from .updator.LLMUpdator import LLMUpdator
from .extractor import LLMExtractorConfig
from .updator import LLMUpdatorConfig
from ...kg_model import KnowledgeGraphModel
from ...utils import Logger, Quadruplet, ReturnStatus, ReturnInfo
from ...utils.data_structs import create_id
from ...utils.errors import STATUS_MESSAGE
from ...db_drivers.kv_driver import KeyValueDriverConfig

@dataclass
class MemPipelineConfig:
    """Конфигурация Memorize-конвейера.

    :param extractor_config: Конфигурация первой стадии Memorize-конвейера: извлечение информации из текстовых данных и приведение их в quadruplet-формат. Значение по умолчанию LLMExtractorConfig().
    :type extractor_config: LLMExtractorConfig
    :param updator_config: Конфигурация второй стадии Memorize-конвейера: актуализация знаний в памяти ассистента. Значение по умолчанию LLMUpdatorConfig().
    :type updator_config: LLMUpdatorConfig
    :param log: Отладочный класс для журналирования/мониторинга поведения инициализируемой комопненты. Значение по умолчанию Logger(MEM_LOG_PATH).
    :type log: Logger
    :param verbose: Если True, то информация о поведении класса будет сохраняться в stdout и файл-журналирования (log), иначе только в файл. Значение по умолчанию False.
    :type verbose: bool
    """
    extractor_config: LLMExtractorConfig = field(default_factory=lambda: LLMExtractorConfig())
    updator_config: LLMUpdatorConfig = field(default_factory=lambda: LLMUpdatorConfig())

    log: Logger = field(default_factory=lambda: Logger(MEMORIZE_MAIN_LOG_PATH))
    verbose: bool = False

class MemPipeline:
    """Верхнеуровневый класс Memorize-конвейера, отвечающий за изменение знаний в памяти ассистента.

    :param kg_model: Модель памяти (графа знаний) ассистента.
    :type kg_model: KnowledgeGraphModel
    :param config: Конфигурация Memorize-конвейера. Значение по умолчанию MemPipelineConfig().
    :type config: MemPipelineConfig
    """

    def __init__(self, kg_model: KnowledgeGraphModel, config: MemPipelineConfig = MemPipelineConfig(),
                 cache_kvdriver_config: KeyValueDriverConfig = None) -> None:
        self.config = config
        self.log = config.log

        self.extractor = LLMExtractor(config.extractor_config, cache_kvdriver_config)
        self.updator = LLMUpdator(kg_model, config.updator_config, cache_kvdriver_config)

    def remember(self, text: str, time: str = "No time", properties: Dict = dict()) -> Tuple[List[Quadruplet], ReturnInfo]:
        """Метод предназначен для извлечения информации (в виде квадруплетов) из слабоструктурированного текста и обновление/актуализацию знаний в памяти (графе знаний) ассистента.

        :param text: Слабоструктурированный текст на естественном языке.
        :type text: str
        :param delete_obsolete_info: Если True, то перед добавлением заданной информации будет удалена устаревшая информация из памяти (графа знаний) ассистента, инчае False. Значение по умолчанию False.
        :type delete_obsolete_info: bool, optional
        :param time: Время, с которым ассоциированы события текста
        :type time: str, optional
        :param properties: Набор свойств, который должен быть сохранён в памяти вмести с извлечённой из текста информацией, Значение по умолчанию dict().
        :type properties: Dict, optional
        :return: Кортеж из двух объектов: (1) список с извлечённой из текста информации (в виде квадруплетов), который использовался для обновления/актуализации памяти ассистента; (2) статус завершения операции с пояснительной информацией.
        :rtype: Tuple[List[Quadruplet], ReturnInfo]
        """

        self.log("START KNOWLEDGE REMEMBERING...", verbose=self.config.verbose)
        self.log(f"BASE_TEXT ID: {create_id(text)}", verbose=self.config.verbose)

        self.log("STAGE#1 - 'Извлечение информации (в структурированном формате) из текста'", verbose=self.config.verbose)
        new_quadruplets, info = self.extractor.extract_knowledge(text, time, properties)

        self.log(f"RESULT: {len(new_quadruplets)}", verbose=self.config.verbose)
        for quadruplet in new_quadruplets:
            self.log(f"* {quadruplet}", verbose=self.config.verbose)

        if info.status == ReturnStatus.success:
            self.log("STAGE#2 - 'Обновление информации в памяти (графе знаний) асситента'", verbose=self.config.verbose)
            self.log(f"QUADRUPLETS_ID: {create_id(f'{new_quadruplets}')}", verbose=self.config.verbose)
            info = self.updator.update_knowledge(new_quadruplets)

        self.log(f"STATUS: {STATUS_MESSAGE[info.status]}", verbose=self.config.verbose)

        return new_quadruplets, info
