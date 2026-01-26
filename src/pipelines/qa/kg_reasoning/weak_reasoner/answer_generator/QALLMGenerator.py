from typing import List, Tuple, Union
from dataclasses import dataclass, field
from copy import deepcopy
import hashlib

from .configs import DEFAULT_AG_TASK_CONFIG, AG_MAIN_LOG_PATH

from ......utils.data_structs import Triplet, RelationType, create_id, TripletCreator
from ......utils.errors import STATUS_MESSAGE
from ......agents import AgentDriver, AgentDriverConfig
from ......utils import Logger, ReturnInfo, ReturnStatus, AgentTaskSolverConfig, AgentTaskSolver
from ......utils.cache_kv import CacheKV, CacheUtils
from ......db_drivers.kv_driver import KeyValueDriverConfig


@dataclass
class QALLMGeneratorConfig:
    """Конфигурация "Question Answering"-стадии QA-конвейера.

    :param lang: Язык, который будет использоваться в подаваемом на вход тексте. На основании выбранного языка будут использоваться соответствующие промпты для инференса LLM-агента. Если 'auto', то язык определяется автоматически. Значение по умолчанию 'auto'.
    :type lang: str
    :param adriver_config: Конфигурация LLM-агента, который будет использоваться в рамках данной стадии. Значение по умолчанию AgentDriverConfig().
    :type adriver_config: AgentDriverConfig
    :param ag_task_config: Конфигурация атомарной задачи для LLM-агента по условной генерации ответа на вопрос. Значение по умолчанию DEFAULT_AG_TASK_CONFIG.
    :type ag_tasK_config: AgentTaskSolverConfig
    :param relation_type: Типы триплетов, которые могут присутствовать в контексте для генерации ответа на user-вопрос. Значение по умолчанию [RelationType.simple, RelationType.hyper, RelationType.episodic].
    :type relation_type: List[RelationType]
    :param log: Отладочный класс для журналирования/мониторинга поведения инициализируемой компоненты. Значение по умолчанию Logger(QA_LOG_PATH).
    :type log: Logger
    :param verbose: Если True, то информация о поведении класса будет сохраняться в stdout и файл-журналирования (log), иначе только в файл. Значение по умолчанию False.
    :type verbose: bool
    """
    lang: str = "auto"
    adriver_config: AgentDriverConfig = field(default_factory=lambda: AgentDriverConfig())
    ag_task_config: AgentTaskSolverConfig = field(default_factory=lambda: DEFAULT_AG_TASK_CONFIG)

    relation_type: List[RelationType] = field(default_factory=lambda: [RelationType.simple, RelationType.hyper, RelationType.episodic])
    cache_table_name: Union[str, None] = 'qa_agenerator_stage_cache'

    log: Logger = field(default_factory=lambda: Logger(AG_MAIN_LOG_PATH))
    verbose: bool = False

    def to_str(self):
        str_relations = ";".join(list(map(lambda v: v.value, self.relation_type)))
        return f"{self.lang}|{self.adriver_config.to_str()}|{self.ag_task_config.version}|{str_relations}"

class QALLMGenerator(CacheUtils):
    """Верхнеуровневый класс четвёртой стадии QA-конвейера для генерации ответа на user-вопрос,
    обусловленного извлечённой информацией из памяти (графа знаний) ассистента.

    :param config: Конфигурация "Answer-generation"-стадии. Значение по умолчанию QALLMGeneratorConfig().
    :type config: QALLMGeneratorConfig
    """
    def __init__(self, config: QALLMGeneratorConfig = QALLMGeneratorConfig(),
                 cache_kvdriver_config: KeyValueDriverConfig = None, cache_llm_inference: bool = True) -> None:
        self.config = config
        self.log = self.config.log
        self.verbose = self.config.verbose

        if cache_kvdriver_config is not None and self.config.cache_table_name is not None:
            cache_config = deepcopy(cache_kvdriver_config)
            cache_config.db_config.db_info['table'] = self.config.cache_table_name
            self.cachekv = CacheKV(cache_config)
        else:
            self.cachekv = None

        self.agent = AgentDriver.connect(config.adriver_config)

        ag_task_cache_config = None
        if cache_llm_inference:
            ag_task_cache_config = deepcopy(cache_kvdriver_config)

        self.answer_generator_solver = AgentTaskSolver(
            self.agent, self.config.ag_task_config, ag_task_cache_config)

    def get_cache_key(self, query: str, context_triplets: List[Triplet]) -> List[object]:
        str_triplets = hashlib.sha1("\n".join(sorted([TripletCreator.stringify(triplet)[1] for triplet in context_triplets])).encode()).hexdigest()
        return [self.config.to_str(), query, str_triplets]

    @CacheUtils.cache_method_output
    def generate(self, query: str, context_triplets: List[Triplet]) -> Tuple[str, ReturnInfo]:
        """Метод предназначен для условной генерации ответа на вопрос.

        :param query: Вопрос на естественном языке.
        :type query: str
        :param context: Ненумерованный список дополнительной информации на естественном языке для генерации ответа.
        :type context: str
        :return: Кортеж из двух объектов: (1) сгенерированный ответ на вопрос; (2) статус выполнения операции с пояснительной информацией.
        :rtype: Tuple[str, ReturnInfo]
        """

        info = ReturnInfo()
        self.log("START ANSWER GENERATION ...", verbose=self.config.verbose)
        self.log(f"BASE_QUESTION ID: {create_id(query)}", verbose=self.config.verbose)
        self.log(f"BASE_QUESTION: {query}", verbose=self.config.verbose)
        self.log(f"CONTEXT_TRIPLETS:",verbose=self.config.verbose)
        for triplet in context_triplets:
            self.log(f"*[{triplet.id}] {triplet}", verbose=self.config.verbose)

        self.log("Выполнение условной генерации ответа на вопрос с помощью LLM-агента...", verbose=self.config.verbose)
        answer, status = self.answer_generator_solver.solve(lang=self.config.lang, query=query, triplets=context_triplets)

        if status != ReturnStatus.success:
            info.occurred_warning.append(status)

        if answer is None or len(answer) == 0:
            info.status = ReturnStatus.empty_answer
            info.message = STATUS_MESSAGE[info.status]

        self.log(f"RESULT:\n* GENERATED ANSWER - {answer}", verbose=self.config.verbose)
        self.log(f"STATUS: {info.status}", verbose=self.config.verbose)

        return answer, info
