from typing import List, Dict, Set, Union
from dataclasses import dataclass, field

from .graph_model import GraphModelConfig, GraphModel
from .embeddings_model import EmbeddingsModelConfig, EmbeddingsModel
from ..db_drivers.kv_driver import KeyValueDriverConfig
from .nodestree_model import NodesTreeModelConfig, NodesTreeModel
from ..utils import Triplet, Logger
from ..utils.data_structs import Node

KG_MAIN_LOG_PATH = 'log/kg_model/main'

@dataclass
class KnowledgeGraphModelConfig:
    """Конфигурация памяти (граф знаний) ассистента.

    :param graph_config: Конфигурация структуры данных, которая отвечает за хранение знаний ассистента в формате графа. Значение по умолчанию GraphModelConfig().
    :type graph_struct: GraphModel, optional
    :param embeddings_config:  Конфигурация структуры данных, которая отвечает за представление/хранение знаний ассистента в векторном формате. Значение по умолчанию EmbeddingsModelConfig().
    :type embeddings_config: EmbeddingsModel, optional
    :param nodestree_config: Конфигурация структуры данных, которая отвечает за представление/хранение знаний ассистента в формате дерева. Значение по умолчанию None.
    :type nodestree_config: Union[NodesTreeModelConfig,None]
    :param log: Отладочный класс для журналирования/мониторинга поведения инициализируемой компоненты. Значение по умолчанию Logger(EMBEDDINGS_MODEL_LOG_PATH).
    :type log: Logger
    :param verbose: Если True, то информация о поведении класса будет сохраняться в stdout и файл-журналирования (log), иначе только в файл. Значение по умолчанию False.
    :type verbose: bool
    """
    graph_config: GraphModelConfig = field(default_factory=lambda: GraphModelConfig())
    embeddings_config: EmbeddingsModelConfig = field(default_factory=lambda: EmbeddingsModelConfig())
    nodestree_config: Union[NodesTreeModelConfig,None] = None

    log: Logger = field(default_factory=lambda: Logger(KG_MAIN_LOG_PATH))
    verbose: bool = False

class KnowledgeGraphModel:
    """Модель памяти (граф знаний) ассистента.

    :param config: Конфигурация памяти (граф знаний) ассистента. Значение по умолчанию KnowledgeGraphModelConfig().
    :type config: KnowledgeGraphModelConfig, optional
    :param cache_kvdriver_config: Конфигурация структуры данных для кеширования промежутчных результатов в рамках компонент данного класса. Значение по умолчению None.
    :type cache_kvdriver_config: Union[KeyValueDriverConfig, None], optional
    """

    def __init__(self, config: KnowledgeGraphModelConfig = KnowledgeGraphModelConfig(),
                 cache_kvdriver_config: Union[KeyValueDriverConfig, None] = None) -> None:
        self.config = config
        self.graph_struct = GraphModel(self.config.graph_config)
        self.embeddings_struct =  EmbeddingsModel(self.config.embeddings_config)
        if self.config.nodestree_config is not None:
            self.nodestree_struct = NodesTreeModel(self.config.nodestree_config, cache_kvdriver_config)
        else:
            self.nodestree_struct = None

        self.log = self.config.log
        self.verbose = self.config.verbose

    def check_consistency(self) -> None:
        gdb_count = self.graph_struct.db_conn.count_items()
        self.log(f"GRAPH DB STATUS: {gdb_count}", verbose=self.verbose)
        vdb_nodes_count = self.embeddings_struct.vectordbs['nodes'].count_items()
        vdb_triplets_count = self.embeddings_struct.vectordbs['triplets'].count_items()
        self.log(f"VECTOR DB STATUS: {vdb_nodes_count} - nodes; {vdb_triplets_count} - triplets", verbose=self.verbose)

        assert gdb_count['nodes'] == vdb_nodes_count
        assert gdb_count['triplets'] >= vdb_triplets_count
        #assert vdb_nodes_count > vdb_triplets_count

        if self.nodestree_struct is not None:
            self.nodestree_struct.check_consistency()

    def add_knowledge(self, triplets: List[Triplet], check_consistency: bool = True, status_bar: bool = False) -> Dict[str, Dict[str,Set[str]]]:
        """Метод предназначен для добавления информации в память ассистента в виде списка триплетов.

        :param triplets: Список триплетов с информацией для добавления в память ассистента.
        :type triplets: List[Triplet]
        :param check_consistency: Если True, то после выполнения данной операции будет проверена консистентность памяти ассистента, иначе False. Значение по умолчанию True.
        :type check_consistency: bool, optional
        :param status_bar: Если True, то во время исполнения операции в stdout будет выводиться статус её исполнения, иначе False. Значение по умолчанию True.
        :type status_bar: bool, optional
        :return: Словарь с информацией о триплетах, которые были добавлены в память ассистента.
        :rtype: Dict[str, Dict[str,Set[str]]]
        """
        graph_create_info = self.graph_struct.create_triplets(triplets, status_bar=status_bar)
        embd_create_info = self.embeddings_struct.create_triplets(triplets, status_bar=status_bar)

        if self.nodestree_struct is not None:
            tree_expand_info = self.nodestree_struct.expand_tree(triplets, status_bar=status_bar)
        else:
            tree_expand_info = None

        if check_consistency:
            self.check_consistency()

        return {'graph_info': graph_create_info, 'embeddings_info': embd_create_info, 'tree_info': tree_expand_info}

    def remove_knowledge(self, triplets: List[Triplet], check_consistency: bool = True) -> Dict[str, Dict[int,Dict[str,bool]]]:
        """Метод предназначен для удаления информации из памяти ассистента.
        Удаление производится по идентификаторам триплетов, в которых данная информация находилась
        при её добавлении в память с помощью соответствующего add_knowledge-метода.

        :param triplets: Набор триплетов, по которым нужно удалить соответствующую информацию из памяти ассистента.
        :type triplets: List[Triplet]
        :param check_consistency: Если True, то после выполнения данной операции будет проверена консистентность памяти ассистента, иначе False. Значение по умолчанию True.
        :type check_consistency: bool, optional
        :return: Словарь с информацией о триплетах, которые были удалены (значение True, иначе False) из памяти ассистента.
        :rtype: Dict[str, Dict[int,Dict[str,bool]]]
        """
        graph_delete_info, embds_delete_info = self.graph_struct.delete_triplets(triplets)
        self.embeddings_struct.delete_triplets(triplets, delete_info=embds_delete_info)

        if self.nodestree_struct is not None:
            tree_reduce_info = self.nodestree_struct.reduce_tree(triplets, delete_info=graph_delete_info)
        else:
            tree_reduce_info = None

        if check_consistency:
            self.check_consistency()

        return {'graph_info': graph_delete_info, 'embeddings_info': embds_delete_info, 'tree_info': tree_reduce_info}

    def count_items(self) -> Dict[str, Dict[str, int]]:
        return {
            'graph_info': self.graph_struct.count_items(),
            'embeddings_info': self.embeddings_struct.count_items(),
            'nodestree_info': self.nodestree_struct.count_items() if self.config.nodestree_config is not None else None
        }

    def clear(self) -> None:
        """Метод предназначен для полного удаления содержимого памяти ассистента.
        """
        self.embeddings_struct.clear()
        self.graph_struct.clear()
        if self.config.nodestree_config is not None:
            self.nodestree_struct.clear()
