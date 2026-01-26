from dataclasses import dataclass, field
from typing import Tuple, Dict, Union
import json
from copy import deepcopy
import hashlib 

from .logger import Logger
from .language_detector import detect_lang
from .errors import ReturnStatus, STATUS_MESSAGE
from .cache_kv import CacheKV
from ..agents.utils import AbstractAgentConnector
from ..db_drivers.kv_driver import KeyValueDriverConfig

@dataclass
class AgentTaskSuite:
    """Набор гиперпараметров для инференса и разбора ответа LLM-агента в рамках заданной атомарной задачи.

    :param system_prompt: System-промпт с описанием персоны, свойствам которой должен удовлетворять LLM-агент во время инференса.
    :type system_prompt: str
    :param user_prompt: User-промпт для инференса LLM-агента с описанием задачи.
    :type user_prompt: str
    :param assistant_prompt: Assistant-промпт с дополнительной информацией по решаемой задаче для инференса LLM-агента.
    :type assistant_prompt: str
    :param parse_answer_func: Кастомная функция, которая должна выполнять промежуточный разбор ответа LLM-агента, полученного в рамках инференса.
    :type parse_answer_func: object
    """
    system_prompt: str
    user_prompt: str
    assistant_prompt: str
    parse_answer_func: object

@dataclass
class AgentTaskSolverConfig:
    """Конфигурация agent-солвера.

    :param suites: Набор гиперпараметров для инференса и разбора ответа LLM-агента в рамках заданной атомарной задачи.
    :type suites: Dict[str, AgentTaskSuite]
    :param formate_context_func: Кастомная функция, приводящая входной (в agent-солвер) набор данных в строковый формат (в виде словаря со строковыми значениями), который далее будет добавляться в user-prompt для LLM-агента.
    :type formate_context_func: object
    :param postprocess_answer_func: Кастомная функция, приводящая разобранный ответ от LLM-агента к формату, который требуется для данной атомарной задачи.
    :type postprocess_answer_func: object
    :param log: Отладочный класс для журналирования/мониторинга поведения инициализируемой компоненты. Значение по умолчанию Logger(RKG_LOG_PATH).
    :type log: Logger
    :param verbose: Если True, то информация о поведении класса будет сохраняться в stdout и файл-журналирования (log), иначе только в файл. Значение по умолчанию False.
    :type verbose: bool
    """
    version: str
    suites: Dict[str, AgentTaskSuite]
    formate_context_func: object
    postprocess_answer_func: object

    cache_table_name: str

    log: Logger
    verbose: bool = False

class AgentTaskSolver:
    """Класс-обёртка, предназначенный для решения атомарной задачи на базе инференса LLM-агента.

    :param agent: интерфейс взаимодействия с LLM-агеном.
    :type agent: AbstractAgentConnector
    :param config: Конфигурация решения конкретной атомарной задачи.
    :type config: AgentTaskSolverConfig
    """

    def __init__(self, agent: AbstractAgentConnector, config: AgentTaskSolverConfig,
                 cache_kvdriver_config: KeyValueDriverConfig = None) -> None:
        self.config = config
        self.agent = agent
        self.log = self.config.log
        self.verbose = self.config.verbose

        if cache_kvdriver_config is not None and self.config.cache_table_name is not None:
            cache_config = deepcopy(cache_kvdriver_config)
            cache_config.db_config.db_info['table'] = self.config.cache_table_name
            self.cachekv = CacheKV(cache_config)
        else:
            self.cachekv = None

    def solve(self, lang: str = 'en', **kwargs) -> Tuple[object, ReturnStatus]:
        """Метод предназначен для запуска agent-солвера на заданных входных данных.

        :param lang: Язык промптов, которые будут использоваться на этапе инференса LLM-агента. Значение по умолчанию 'auto'.
        :type lang: str, optional
        :return: Кортеж из двух объектов: (1) результат работы agent-солвера; (2) статус завершения операции с пояснительной информацией.
        :rtype: Tuple[object, ReturnStatus]
        """
        task_result, status = None, ReturnStatus.success
        self.log("="*20, verbose=self.config.verbose)
        self.log("1. Предобработка данных для их дальнейшней вставки в user-prompt...", verbose=self.config.verbose)

        try:
            formated_context = self.config.formate_context_func(**kwargs)
        except Exception as e:
            self.log(str(e), verbose=self.config.verbose)
            status = ReturnStatus.bad_formater
        else:
            self.log(f"Результат:\n{json.dumps(formated_context, indent=1, ensure_ascii=False)}.", verbose=self.config.verbose)
        finally:
            self.log("Статус: " + STATUS_MESSAGE[status], verbose=self.config.verbose)

        # Если удалось без ошибок привести данные в формат контекста
        # для вставки в user-prompt
        if status == ReturnStatus.success:
            self.log("-"*20, verbose=self.config.verbose)
            self.log("2. Детекция используемого языка...", verbose=self.config.verbose)
            flatten_context = ' '.join(list(formated_context.values()))
            detected_lang, status = detect_lang(flatten_context) if lang == 'auto' else (lang, ReturnStatus.success)

            self.log(f"Результат:\n{detected_lang}.", verbose=self.config.verbose)
            self.log("Статус: " + STATUS_MESSAGE[status], verbose=self.config.verbose)

        # Если удалось определить язык (распознанный язык находится в списке доступных)
        if status == ReturnStatus.success:
            self.log("-"*20, verbose=self.config.verbose)
            self.log("3. Добавление информации в user-prompt...", verbose=self.config.verbose)
            try:
                enriched_user_prompt = self.config.suites[detected_lang].user_prompt.format(**formated_context)
            except Exception as e:
                self.log(str(e), verbose=self.config.verbose)
                status = ReturnStatus.bad_user_prompt_maping
            else:
                self.log(f"Результат:\n{enriched_user_prompt}", verbose=self.config.verbose)
            finally:
                self.log("Статус: " + STATUS_MESSAGE[status], verbose=self.config.verbose)

        # Если удалось добавить дополнительную инофрмациб в user-prompt
        if status == ReturnStatus.success:
            self.log("-"*20, verbose=self.config.verbose)
            self.log("4. Генерация ответа с помощью LLM-агента.", verbose=self.config.verbose)

            raw_answer = None
            gen_flag = True
            
            # preparing cache key
            str_genstrat = ";".join(list(map(lambda p: f"{p[0]}={p[1]}", sorted([(k, str(v)) for k, v in self.agent.config.gen_strategy.items()], key=lambda p: p[0]))))
            str_creds = ";".join(list(map(lambda p: f"{p[0]}={p[1]}", sorted([(k, str(v)) for k, v in self.agent.config.credentials.items()], key=lambda p: p[0]))))
            sprompt_hash = hashlib.sha1(self.config.suites[detected_lang].system_prompt.encode()).hexdigest()
            uprompt_hash = hashlib.sha1(enriched_user_prompt.encode()).hexdigest()
            aprompt_hash = hashlib.sha1(self.config.suites[detected_lang].assistant_prompt.encode()).hexdigest()
            cache_key = [sprompt_hash, uprompt_hash, aprompt_hash, str_genstrat, str_creds]

            key_hash = None

            if self.cachekv is not None:
                self.log("Поиск ответа в кеше...", verbose=self.config.verbose)
                cstatus, key_hash, cached_result = self.cachekv.load_value(key=cache_key)
                if cstatus == 0:
                    self.log("Результат по заданной конфигурации гиперпараметров уже был получен.", verbose=self.config.verbose)
                    self.log(f"* CACHE_TABLE_NAME {self.cachekv.kv_conn.config.db_info['table']}", verbose=self.verbose)
                    self.log(f"* CACHE_HASH_KEY: {key_hash}", verbose=self.verbose)
                    formated_log_cachekey = '\n-'.join(cache_key)
                    self.log(f"* HASH_SEEDS:\n-{formated_log_cachekey}", verbose=self.verbose)

                    gen_flag = False
                    raw_answer = cached_result
                else:
                    self.log("Результата по заданной конфигурации гиперпараметров в кеше нет.", verbose=self.config.verbose)
                    self.log(f"* CACHE_TABLE_NAME {self.cachekv.kv_conn.config.db_info['table']}", verbose=self.verbose)
                    self.log(f"* CACHE_HASH_KEY: {key_hash}.", verbose=self.verbose)
                    formated_log_cachekey = '\n-'.join(cache_key)
                    self.log(f"* HASH_SEEDS:\n-{formated_log_cachekey }", verbose=self.verbose)

            if gen_flag:
                self.log("Выполняем инференс llm...", verbose=self.config.verbose)
                
                raw_answer = self.agent.generate(
                    system_prompt=self.config.suites[detected_lang].system_prompt,
                    user_prompt=enriched_user_prompt,
                    assistant_prompt=self.config.suites[detected_lang].assistant_prompt)

                if self.cachekv is not None:
                    self.log("Кешируем полученный результат.", verbose=self.config.verbose)
                    self.cachekv.save_value(value=raw_answer, key_hash=key_hash)

            self.log(f"Результат:\n{raw_answer}", verbose=self.config.verbose)
            self.log("Статус: " + STATUS_MESSAGE[status], verbose=self.config.verbose)

        # Если сгенрированная raw-строка не является пустой
        if status == ReturnStatus.success:
            self.log("-"*20, verbose=self.config.verbose)
            self.log("5. Разбор ответа, сгенерированного LLM-агентом.", verbose=self.config.verbose)

            try:
                formated_answer = self.config.suites[detected_lang].parse_answer_func(raw_answer, **kwargs)
            except (KeyError, ValueError) as e:
                self.log(str(e), verbose=self.config.verbose)
                status = ReturnStatus.bad_parser
            else:
                self.log(f"Результат:\n{formated_answer}", verbose=self.config.verbose)
            finally:
                self.log("Статус: " + STATUS_MESSAGE[status], verbose=self.config.verbose)

        #  Если не было ошибок при разборе raw-строки
        if status == ReturnStatus.success:
            self.log("-"*20, verbose=self.config.verbose)
            self.log("6. Постобработка ответа от LLM-агента.", verbose=self.config.verbose)

            try:
                task_result = self.config.postprocess_answer_func(formated_answer, **kwargs)
            except Exception as e:
                self.log(str(e), verbose=self.config.verbose)
                status = ReturnStatus.bad_postprocessor
            else:
                self.log(f"Результат:\n{task_result}", verbose=self.config.verbose)
            finally:
                self.log("Статус: " + STATUS_MESSAGE[status], verbose=self.config.verbose)

        return task_result, status

@dataclass
class AgentTaskBaseConfig:
    suites: Dict[str, AgentTaskSuite]
    custom_formate: object
