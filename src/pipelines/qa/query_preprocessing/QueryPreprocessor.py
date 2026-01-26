from dataclasses import dataclass, field
from typing import Tuple, Union, List
from copy import deepcopy

from .utils import QueryPreprocessingInfo
from .config import QP_MAIN_LOG_PATH
from .decomposition import QueryDecomposer, QueryDecomposerConfig
from ....utils import ReturnInfo, Logger, ReturnStatus
from ....utils.data_structs import create_id
from ....db_drivers.kv_driver import KeyValueDriverConfig
from ....utils.cache_kv import CacheKV, CacheUtils

@dataclass
class QueryPreprocessorConfig:
    """_summary_

    :param denoising_config: ...
    :type denoising_config: Union[object, None], optional
    :param enhancing_config: ...
    :type enhancing_config: Union[object, None], optional
    :param decomposition_config: ...
    :type decomposition_config: Union[object, None], optional

    :param cache_table_name: ...
    :type cache_table_name: str, optional
    :param log: Отладочный класс для журналирования/мониторинга поведения инициализируемой компоненты. Значение по умолчанию Logger(LOG_PATH).
    :type log: Logger
    :param verbose: Если True, то информация о поведении класса будет сохраняться в stdout и файл-журналирования (log), иначе только в файл. Значение по умолчанию False.
    :type verbose: bool
    """
    denoising_config: Union[object, None] = None # TODO
    enhancing_config: Union[object, None] = None # TODO
    decomposition_config: Union[QueryDecomposerConfig, None] = field(default_factory=lambda: QueryDecomposerConfig())

    cache_table_name = "query_preprocessing_main_stage_cache"
    log: Logger = field(default_factory=lambda: Logger(QP_MAIN_LOG_PATH))
    verbose: bool = False

    def to_str(self):
        str_denois_config = self.denoising_config if self.denoising_config is not None else 'None'
        str_enh_config = self.enhancing_config if self.enhancing_config is not None else 'None'
        return f"{str_denois_config}|{str_enh_config}|{self.decomposition_config.to_str()}"

class QueryPreprocessor(CacheUtils):
    def __init__(self, config: QueryPreprocessorConfig = QueryPreprocessorConfig(),
                 cache_kvdriver_config: KeyValueDriverConfig = None) -> None:
        """_summary_

        :param config: _description_, defaults to QueryPreprocessorConfig()
        :type config: QueryPreprocessorConfig, optional
        :param cache_kvdriver_config: _description_, defaults to None
        :type cache_kvdriver_config: KeyValueDriverConfig, optional
        """
        self.config = config

        #self.denoiser = QueryDenoiser(self.config.denoising_config, cache_kvdriver_config) if self.config.denoising_config is not None else None
        #self.enhancer = QueryEnhancer(self.config.enhancing_config, cache_kvdriver_config) if self.config.enhancing_config is not None else None
        self.decomposer = QueryDecomposer(self.config.decomposition_config, cache_kvdriver_config) if self.config.decomposition_config is not None else None

        if cache_kvdriver_config is not None and self.config.cache_table_name is not None:
            cache_config = deepcopy(cache_kvdriver_config)
            cache_config.db_config.db_info['table'] = self.config.cache_table_name
            self.cachekv = CacheKV(cache_config)
        else:
            self.cachekv = None

        self.log = self.config.log
        self.verbose = self.config.verbose

    def clear_kv_caches(self) -> None:
        """_summary_
        """
        self.cachekv.kv_conn.clear()
        #self.denoiser.cachekv.kv_conn.clear()
        #self.enhancer.cachekv.kv_conn.clear()
        self.decomposer.cachekv.kv_conn.clear()

    def get_cache_key(self, query: str) -> List[str]:
        """_summary_

        :param query: _description_
        :type query: str
        :return: _description_
        :rtype: List[str]
        """
        return [query, self.config.to_str()]

    @CacheUtils.cache_method_output
    def perform(self, query: str) -> Tuple[QueryPreprocessingInfo, ReturnInfo]:
        """_summary_

        :param query: _description_
        :type query: str
        :return: _description_
        :rtype: Tuple[QueryPreprocessingInfo, ReturnInfo]
        """
        self.log("START QUERY PREPROCESSING...", verbose=self.config.verbose)
        self.log(f"BASE_QUESTION ID: {create_id(query)}", verbose=self.config.verbose)
        self.log(f"BASE_QUESTION: {query}", verbose=self.config.verbose)
        q_info = QueryPreprocessingInfo(base_query=query)
        info = ReturnInfo()

        #if self.denoiser is not None:
        #    self.log("Удаление шума из запроса...", verbose=self.verbose)
        #    q_info.denoised_query, info = self.denoiser.perform(q_info)
        #    self.log(f"RESULT: {q_info.denoised_query}", verbose=self.verbose)

        #if info.status == ReturnStatus.success and self.enhancer is not None:
        #    self.log("Корректировка формата запроса...", verbose=self.verbose)
        #    q_info.enchanced_query, info = self.enhancer.perform(q_info)
        #    self.log(f"RESULT: {q_info.enchanced_query}", verbose=self.verbose)

        if info.status == ReturnStatus.success and self.decomposer is not None:
            self.log("Разбиение запроса на независимые части...", verbose=self.verbose)
            q_info.decomposed_query, info = self.decomposer.perform(q_info)
            self.log(f"RESULT: {q_info.decomposed_query}", verbose=self.verbose)

        self.log(f"STATUS: {info.status}", verbose=self.verbose)

        return q_info, info
