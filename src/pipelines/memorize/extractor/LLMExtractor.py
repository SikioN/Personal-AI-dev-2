from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from copy import deepcopy

from ....utils import Logger, ReturnStatus, ReturnInfo, AgentTaskSolver, AgentTaskSolverConfig
from ....utils.errors import STATUS_MESSAGE
from ....utils.data_structs import QuadrupletCreator, NodeCreator, Node, Relation, RelationType, NodeType, Quadruplet, create_id
from ....agents import AgentDriver, AgentDriverConfig
from ....db_drivers.kv_driver import KeyValueDriverConfig

from .configs import DEFAULT_THESISES_EXTR_TASK_CONFIG, DEFAULT_TRIPLETS_EXTR_TASK_CONFIG, MEM_EXTRACTOR_MAIN_LOG_PATH

@dataclass
class LLMExtractorConfig:
    """Конфигурация Extractor-стадии Memorize-конвейера.

    :param lang: Язык, который будет использоваться в подаваемом на вход тексте. На основании выбранного языка будут использоваться соответствующие промпты для инференса LLM-агента. Если 'auto', то язык определяется автоматически. Значение по умолчанию 'auto'.
    :type lang: str
    :param adriver_config: Конфигурация LLM-агента, который будет использоваться в рамках данной стадии. Значение по умолчанию AgentDriverConfig().
    :type adriver_config: AgentDriverConfig
    :param triplets_extraction_task_config: Конфигурация атомарной задачи для LLM-агента по извлечению квадруплетов с информацией типа 'simple' из слабоструктурированных текстов на естественном языке. Значение по умолчанию DEFAULT_EXTRACT_TRIPLETS_TASK_CONFIG.
    :type triplets_extraction_task_config: AgentTaskSolverConfig
    :param thesises_extraction_task_config: Конфигурация атомарной задачи для LLM-агента по извлечению квадруплетов с информацией типа 'hyper' из слабоструктурированных текстов на естественном языке. Значение по умолчанию DEFAULT_EXTRACT_THESISES_TASK_CONFIG.
    :type thesises_extraction_task_config: AgentTaskSolverConfig
    :param need_simple: Если True, то из входного текста на первой стадии Mem-конвейера будет выполнено извлечение квадруплетов с типом связи 'simple', иначе False. Значение по умолчанию True.
    :type need_simple: bool, optional
    :param need_thesises: Если True, то из входного текста на первой стадии Mem-конвейера будет выполнено извлечение квадруплетов с типом связи 'hyper', иначе False. Значение по умолчанию True.
    :type need_thesises: bool, optional
    :param need_episodic: Если True, то из входного текста на первой стадии Mem-конвейера будет выполнено извлечение квадруплетов с типом связи 'episodic', иначе False. Значение по умолчанию True.
    :type need_episodic: bool, optional
    :param log: Отладочный класс для журналирования/мониторинга поведения инициализируемой компоненты. Значение по умолчанию Logger(QA_LOG_PATH).
    :type log: Logger
    :param verbose: Если True, то информация о поведении класса будет сохраняться в stdout и файл-журналирования (log), иначе только в файл. Значение по умолчанию False.
    :type verbose: bool
    """
    lang: str = "auto"
    adriver_config: AgentDriverConfig = field(default_factory=lambda: AgentDriverConfig())
    triplets_extraction_task_config: AgentTaskSolverConfig = field(default_factory=lambda: DEFAULT_TRIPLETS_EXTR_TASK_CONFIG)
    thesises_extraction_task_config: AgentTaskSolverConfig = field(default_factory=lambda: DEFAULT_THESISES_EXTR_TASK_CONFIG)
    need_simple: bool = True
    need_thesises: bool = True
    need_episodic: bool = True
    log: Logger = field(default_factory=lambda: Logger(MEM_EXTRACTOR_MAIN_LOG_PATH))
    verbose: bool = False

class LLMExtractor:
    """Верхнеуровневый класс первой стадии Memorize-конвейера для извлечения информации (и её приведения в quadruplet-формат) из слабоструктурированных данных.

    :param config: Конфигурация Exctrator-стадии. Значение по умолчанию LLMExtractorConfig().
    :type config: LLMExtractorConfig
    """
    def __init__(self, config: LLMExtractorConfig = LLMExtractorConfig(),
                 cache_kvdriver_config: KeyValueDriverConfig = None) -> None:
        self.config = config
        self.log = config.log

        self.agent = AgentDriver.connect(config.adriver_config)
        self.triplets_extraction_solver = AgentTaskSolver(
            self.agent, self.config.triplets_extraction_task_config, cache_kvdriver_config)
        self.thesises_extraction_solver = AgentTaskSolver(
            self.agent, self.config.thesises_extraction_task_config, cache_kvdriver_config)

    def extract_knowledge(self, text: str, time: str = "No time", properties: Dict = {}) -> Tuple[List[Quadruplet], ReturnInfo]:
        """Метод предназначен для извлечения информации (в виде квадруплетов) из слабоструктурированного текста
        на естественном языке.

        :param text: Слабоструктурированный текст.
        :type text: str
        :param properties: Набор свойств, который должен быть сохранён в памяти вмести с извлечённой из текста информацией, Значение по умолчанию dict().
        :type properties: Dict, optional
        :param time: Время, с которым ассоциированы события текста
        :type time: str, optional
        :return: Кортеж из двух объектов: (1) список извлечённой из текста информации (в виде квадруплетов); (2) статус завершения операции с пояснительной информацией.
        :rtype: Tuple[List[Quadruplet], ReturnInfo]
        """
        assert self.config.need_simple or self.config.need_thesises
        props = deepcopy(properties)
        assert 'time' not in props.keys()
        new_quadruplets, info = [], ReturnInfo()

        if time != "No time":
            props["time"] = time

        self.log("START KNOWLEDGE EXTRACTION...", verbose=self.config.verbose)
        self.log(f"BASE_TEXT ID: {create_id(text)}", verbose=self.config.verbose)

        if self.config.need_simple:
            self.log("START SIMPLE-QUADRUPLETS EXTRACTION...", verbose=self.config.verbose)
            # Solvers will use parsers that check rel_prop/node_prop for 'time'
            tmp_quadruplets, status = self.triplets_extraction_solver.solve(
                lang=self.config.lang, text=text, rel_prop=props)
            self.log(f"STATUS: {STATUS_MESSAGE[status]}", verbose=self.config.verbose)

            if status != ReturnStatus.success:
                self.log(f"RESULT: None", verbose=self.config.verbose)
                info.occurred_warning.append(status)
            else:
                self.log(f"RESULT: {len(tmp_quadruplets)}", verbose=self.config.verbose)
                for quadruplet in tmp_quadruplets:
                    self.log(f"* {quadruplet}", verbose=self.config.verbose)
                new_quadruplets += tmp_quadruplets

        if self.config.need_thesises:
            self.log("START HYPER-QUADRUPLETS EXTRACTION...", verbose=self.config.verbose)
            tmp_quadruplets, status = self.thesises_extraction_solver.solve(
                lang=self.config.lang, text=text, node_prop=props)
            self.log(f"STATUS: {STATUS_MESSAGE[status]}", verbose=self.config.verbose)

            if status != ReturnStatus.success:
                self.log(f"RESULT: None", verbose=self.config.verbose)
                info.occurred_warning.append(status)
            else:
                self.log(f"RESULT: {len(tmp_quadruplets)}", verbose=self.config.verbose)
                for quadruplet in tmp_quadruplets:
                    self.log(f"* {quadruplet}", verbose=self.config.verbose)
                new_quadruplets += tmp_quadruplets

        if self.config.need_episodic:
            self.log("START EPISODIC-QUADRUPLETS BUILDING...", verbose=self.config.verbose)
            tmp_quadruplets = self.get_episodic_relationships(
                text, self.get_entities_from_quadruplets(new_quadruplets), time=time, node_prop=props)

            self.log(f"RESULT: {len(tmp_quadruplets)}", verbose=self.config.verbose)
            for quadruplet in tmp_quadruplets:
                self.log(f"* {quadruplet}", verbose=self.config.verbose)
            # status for episodic building is implicit success if entities exist or empty
            
            new_quadruplets += tmp_quadruplets

        # NOTE: get_time_triplets removed, time is intrinsic to Quadruplets now.

        if len(new_quadruplets) == 0:
            info.status = ReturnStatus.zero_triplets # Keep status name or rename? Keeping for compatibility with ReturnStatus enum
            info.message = STATUS_MESSAGE[info.status]

        self.log(f"FINAL STATUS: {STATUS_MESSAGE[info.status]}", verbose=self.config.verbose)

        return new_quadruplets, info

    def get_entities_from_quadruplets(self, quadruplets: List[Quadruplet]) -> List[Node]:
        entities = {}
        for quadruplet in quadruplets:
            entities[quadruplet.start_node.stringified] = quadruplet.start_node
            entities[quadruplet.end_node.stringified] = quadruplet.end_node
        return list(entities.values())

    def get_episodic_relationships(self, text: str, entities: List[Node], time: str = "No time", node_prop: Dict = {}, rel_prop: Dict = {}) -> List[Quadruplet]:
        episodic_node = NodeCreator.create(name=text, n_type=NodeType.episodic, prop={**node_prop})
        episodic_rel = Relation(name=RelationType.episodic.value, type=RelationType.episodic, prop={**rel_prop})
        
        if time == "No time":
            time_node = None
        else:
            time_node = NodeCreator.create(NodeType.time, time, add_stringified_node=True)

        episodic_quadruplets = [QuadrupletCreator.create(entity, episodic_rel, episodic_node, time=time_node) for entity in entities]
        return episodic_quadruplets
