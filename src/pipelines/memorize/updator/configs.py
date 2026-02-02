from .agent_tasks.replace_simple_triplets import AgentReplSimpleTripletTaskConfigSelector
from .agent_tasks.replace_thesis_triplets import AgentReplThesisTripletTaskConfigSelector

from dataclasses import dataclass, field
from ....agents import AgentDriverConfig
from ....utils import Logger, AgentTaskSolverConfig

MEM_UPDATOR_MAIN_LOG_PATH = "log/memorize/updator/main"
DEFAULT_REPLACE_SIMPLE_TASK_CONFIG =  AgentReplSimpleTripletTaskConfigSelector.select(base_config_version='v1')
DEFAULT_REPLACE_THESIS_TASK_CONFIG =  AgentReplThesisTripletTaskConfigSelector.select(base_config_version='v1')

@dataclass
class LLMUpdatorConfig:
    """Конфигурация Updator-стадии Memorize-конвейера.

    :param lang: Язык, который будет использоваться в подаваемом на вход тексте. На основании выбранного языка будут использоваться соответствующие промпты для инференса LLM-агента. Если указано значение 'auto', то язык определяется автоматически. Значение по умолчанию 'auto'.
    :type lang: str
    :param adriver_config: Конфигурация LLM-агента, который будет использоваться в рамках данной стадии.
    :type adriver_config: AgentDriverConfig
    :param replace_simple_task_config: Конфигурация атомарной задачи для LLM-агента по поиску устаревших триплетов типа "simple". Значение по умолчанию DEFAULT_REPLACE_SIMPLE_TASK_CONFIG.
    :type replace_simple_task_config: AgentTaskSolverConfig
    :param replace_thesis_task_config: Конфигурация атомарной задачи для LLM-агента по поиску устаревших триплетов типа "hyper". Значение по умолчанию DEFAULT_REPLACE_THESIS_TASK_CONFIG.
    :type replace_thesis_task_config: AgentTaskSolverConfig
    :param delete_obsolete_info: Если True, то перед добавлением заданной информации будет удалена устаревшие знания из памяти (графа знаний) ассистента, иначе False. Значение по умолчанию False.
    :type delete_obsolete_info: bool, optional
    :param log: Отладочный класс для журналирования/мониторинга поведения инициализируемой компоненты. Значение по умолчанию Logger(MEM_UPDATE_LOG).
    :type log: Logger
    :param verbose: Если True, то информация о поведении класса будет сохраняться в stdout и файл-журналирования (log), иначе только в файл. Значение по умолчанию False.
    :type verbose: bool
    """
    lang: str = "auto"
    adriver_config: AgentDriverConfig = field(default_factory=lambda: AgentDriverConfig())
    replace_simple_task_config: AgentTaskSolverConfig = field(default_factory=lambda: DEFAULT_REPLACE_SIMPLE_TASK_CONFIG)
    replace_thesis_task_config: AgentTaskSolverConfig = field(default_factory=lambda: DEFAULT_REPLACE_THESIS_TASK_CONFIG)
    delete_obsolete_info: bool = False

    log: Logger = field(default_factory=lambda: Logger(MEM_UPDATOR_MAIN_LOG_PATH))
    verbose: bool = False
