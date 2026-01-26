from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from tqdm import tqdm

from .kg_model import KnowledgeGraphModel, KnowledgeGraphModelConfig
from .pipelines.qa import QAPipeline, QAPipelineConfig
from .pipelines.memorize import MemPipeline, MemPipelineConfig
from .utils import Logger, ReturnInfo, Triplet
from .utils.data_structs import create_id
from .db_drivers.kv_driver import KeyValueDriverConfig

RKG_LOG_PATH = "log/main"

@dataclass
class PersonalAIConfig:
    """Конфигурация персонального ассистента.

    :param kg_model_config: Конфигурация памяти ассистента. Значение по умолчанию KnowledgeGraphModelConfig().
    :type kg_model_config: KnowledgeGraphModelConfig, optional
    :param qa_pipeline_config: Конфигурация конвейера, который выполняет обработку входящих user-вопросов и генерацию ответов. Значение по умолчанию QAPipelineConfig().
    :type qa_pipeline_config: QAPipelineConfig, optional
    :param mem_pipeline_config: Конфигурация конвейера, который выполняет изменение/обновление знаний в памяти ассистента. Значение по умолчанию MemPipelineConfig().
    :type mem_pipeline_config: MemPipelineConfig, optional
    :param log: Отладочный класс для журналирования/мониторинга поведения инициализируемой компоненты. Значение по умолчанию Logger(RKG_LOG_PATH).
    :type log: Logger
    :param verbose: Если True, то информация о поведении класса будет сохраняться в stdout и файл-журналирования (log), иначе только в файл. Значение по умолчанию False.
    :type verbose: bool
    """
    kg_model_config: KnowledgeGraphModelConfig = field(default_factory=lambda: KnowledgeGraphModelConfig())
    qa_pipeline_config: QAPipelineConfig = field(default_factory=lambda: QAPipelineConfig())
    mem_pipeline_config: MemPipelineConfig = field(default_factory=lambda: MemPipelineConfig())
    log: Logger = field(default_factory=lambda: Logger(RKG_LOG_PATH))
    verbose: bool = False

class PersonalAI:
    """Верхнеуровневый класс персонального ассистента.

    :param config: Конфигурация персонального ассистента.
    :type config: PersonalAIConfig
    """
    def __init__(self, config: PersonalAIConfig, cache_kvdriver_config: KeyValueDriverConfig = None):
        self.config = config
        self.log = self.config.log

        self.kg_model = KnowledgeGraphModel(
            config=self.config.kg_model_config, cache_kvdriver_config=cache_kvdriver_config)
        self.qa_pipeline = QAPipeline(kg_model=self.kg_model, config=config.qa_pipeline_config)
        self.mem_pipeline = MemPipeline(kg_model=self.kg_model, config=config.mem_pipeline_config)

    def answer_question(self, question: str) -> Tuple[str, ReturnInfo]:
        """Метод предназначен для контекстуального поиска и извлечения релевантной информации
        из памяти (графа знаний) ассистента для генерации ответа на user-вопрос.

        :param question: User-вопрос на естественном языке.
        :type question: str
        :return: Кортеж из двух объектов: (1) сгенерированный ответ; (2) статус завершения операции с пояснительной информацией.
        :rtype: Tuple[str, ReturnInfo]
        """
        self.log("START ANSWER GENERATION...", verbose=self.config.verbose)
        self.log(f"BASE_QUESTION ID: {create_id(question)}", verbose=self.config.verbose)
        self.log(f"BASE_QUESTION: {question}", verbose=self.config.verbose)

        answer, info = self.qa_pipeline.answer(question)
        self.log(f"RESULT:\n* FINAL ANSWER - {answer}", verbose=self.config.verbose)
        return answer, info

    def update_memory(self, text: str, text_properties: Dict) -> Tuple[List[Triplet], ReturnInfo]:
        """Метод предназначен для добавления новой информации в память (граф знаний) и её актуализацию.

        :param text: Слабоструктурированный текст на естественном языке.
        :type text: str
        :param text_properties: Набор свойств данного текста, который необходимо дополнительно сохранить в память ассистента.
        :type text_properties: Dict
        :return: Кортеж из двух объектов: (1) список извлечённой из текста информации (в виде триплетов), который использовался для обновления/актуализации памяти ассистента; (2) статус завершения операции с пояснительной информацией.
        :rtype: Tuple[List[Triplet], ReturnInfo]
        """
        self.log("START MEMORY_UPDATING ...", verbose=self.config.verbose)
        self.log(f"BASE_TEXT ID: {create_id(text)}", verbose=self.config.verbose)
        self.log(f"BASE_TEXT: {text}", verbose=self.config.verbose)

        triplets, info = self.mem_pipeline.remember(text, text_properties)
        self.log(f"RESULT:\n* EXTRACTED_TRIPLETS AMOUNT - {len(triplets)}", verbose=self.config.verbose)

        return triplets, info
