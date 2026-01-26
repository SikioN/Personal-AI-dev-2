from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple
import math
from tqdm import tqdm

from ..db_drivers.graph_driver import GraphDriver, GraphDriverConfig, DEFAULT_NEO4J_CONFIG
from ..utils.data_structs import Triplet
from ..utils import Logger

GRAPH_DB_DEFAULT_DRIVER_CONFIG = GraphDriverConfig(db_vendor='neo4j', db_config=DEFAULT_NEO4J_CONFIG)
GRAPH_MODEL_LOG_PATH = 'log/kg_model/graph'

@dataclass
class GraphModelConfig:
    """Конфигурация графовой структуры данных.

    :param driver_config: Конфигурация графовой БД.
    :type driver_config: GraphDriverConfig
    :param log: Отладочный класс для журналирования/мониторинга поведения инициализируемой компоненты. Значение по умолчанию Logger(GRAPH_MODEL_LOG_PATH).
    :type log: Logger
    :param verbose: Если, True, то информация о поведении класса будет сохраняться в stdout и файл-журналирования (log), иначе только в файл. Значение по умолчанию False.
    :type verbose: bool
    """
    driver_config: GraphDriverConfig = field(default_factory=lambda: GRAPH_DB_DEFAULT_DRIVER_CONFIG)
    log: Logger = field(default_factory=lambda: Logger(GRAPH_MODEL_LOG_PATH))
    verbose: bool = False

class GraphModel:
    """Структура данных, предназначенная для хранения информации в формате графа.

    :param config: Конфигурация графовой структуры. Значение по умолчанию GraphModelConfig().
    :type config: GraphModelConfig
    """
    def __init__(self, config: GraphModelConfig = GraphModelConfig()) -> None:
        self.config = config
        self.log = config.log
        self.db_conn = GraphDriver.connect(self.config.driver_config)

    def create_triplets(self, triplets: List[Triplet], batch_size: int = 64, status_bar: bool = True) -> Dict[str, Set[str]]:
        """Метод предназначен для сохранения информации, представленной в виде списка триплетов, в графовую структуру.

        :param triplets: Набора триплетов для добавления в графовую структуру.
        :type triplets: List[Triplet]
        :param batch_size: Количество триплетов, которое будет сохраняться за одну create-операцию. Значение по умолчанию 64.
        :type batch_size: int, optional
        :param status_bar: Если True, то во время исполнения операции в stdout будет выводиться статус её исполнения, иначе False. Значение по умолчанию True.
        :type status_bar: bool, optional
        :return: Словарь с информацией о триплетах, которые были добавлены в графовую структуру.
        :rtype: Dict[str, Set[str]]
        """
        self.log("Adding triplets to graph-model...", verbose=self.config.verbose)
        unique_triplet_ids, unique_node_ids = set(), set()
        existed_triplet_ids, existed_node_ids = set(), set()
        created_triplet_ids, created_node_ids = set(), set()

        batches = math.ceil(len(triplets) / batch_size)
        process = tqdm(range(batches)) if status_bar else range(batches)
        for batch_idx in process:
            # if n1 rel n2
            # else empty
                # n1 _ _
                # _ _ n2
                # n1 _ n2
                # _ _ _

            creation_info = dict()
            triplets_to_create = list()
            info_counter = -1
            for triplet_idx in range(batch_idx*batch_size, (batch_idx+1)*batch_size, 1):
                if triplet_idx >= len(triplets):
                    break

                cur_triplet = triplets[triplet_idx]
                if cur_triplet.id in unique_triplet_ids:
                    continue
                else:
                    unique_triplet_ids.add(cur_triplet.id)

                if self.db_conn.item_exist(cur_triplet.id, id_type='triplet'):
                    existed_triplet_ids.add(cur_triplet.id)
                    continue
                else:
                    triplets_to_create.append(cur_triplet)
                    info_counter += 1
                    creation_info[info_counter] = {'s_node': False, 'e_node': False}
                    created_triplet_ids.add(cur_triplet.id)

                s_node_id = cur_triplet.start_node.id
                if (s_node_id not in unique_node_ids):
                    unique_node_ids.add(s_node_id)
                    if not self.db_conn.item_exist(s_node_id, id_type='node'):
                        creation_info[info_counter]['s_node'] = True
                        created_node_ids.add(s_node_id)
                    else:
                        existed_node_ids.add(s_node_id)

                e_node_id = cur_triplet.end_node.id
                if (e_node_id not in unique_node_ids):
                    unique_node_ids.add(e_node_id)
                    if not self.db_conn.item_exist(e_node_id, id_type='node'):
                        creation_info[info_counter]['e_node'] = True
                        created_node_ids.add(e_node_id)
                    else:
                        existed_node_ids.add(e_node_id)

            self.db_conn.create(triplets_to_create, creation_info)

        self.log(f"all/unique/existed triplets - {len(triplets)}/{len(unique_triplet_ids)}/{len(existed_triplet_ids)}", verbose=self.config.verbose)
        self.log(f"all/unique/existed nodes - {len(triplets)*2}/{len(unique_node_ids)}/{len(existed_node_ids)}", verbose=self.config.verbose)
        self.log("Triplets added successfully!", verbose=self.config.verbose)

        return {'triplets': created_triplet_ids, 'nodes': created_node_ids}

    def delete_triplets(self, triplets: List[Triplet], status_bar: bool = False) -> Tuple[Dict[int,Dict[str,bool]], Dict[int,Dict[str,bool]]]:
        """Метод предназначен для удаления информации, представленной в виде списка триплетов, из графовой структуры.

        :param triplets: Набор триплетов на удаления из графовой структуры.
        :type triplets: List[Triplet]
        :param status_bar: Если True, то во время исполнения операции в stdout будет выводиться статус её исполнения, иначе False. Значение по умолчанию True.
        :type status_bar: bool, optional
        :return: Информация для векторной структуры данных, чтобы удалить устаревшие вершины/триплеты и сохранить консистентность памяти ассистента.
        :rtype: List[Dict[str,bool]]
        """

        vdb_delete_info, gdb_delete_info = dict(), dict()
        process = tqdm(enumerate(triplets)) if status_bar else enumerate(triplets)
        for i, triplet in process:
            vector_delete_info = {'s_node': False, 'triplet': False, 'e_node': False}
            graph_delete_info = {'s_node': False, 'e_node': False}

            # Если в триплете у стартовой вершины только одно инцидентное ребро,
            # то готовим его к удалению из графовой и векторной структур данных
            s_node_neighbours = self.db_conn.get_adjecent_nids(triplet.start_node.id)
            if len(s_node_neighbours) == 1 and s_node_neighbours[0] == triplet.end_node.id:
                graph_delete_info['s_node'] = True
                vector_delete_info['s_node'] = True

            # Если в триплете у конечной вершины только одно инцидентное ребро,
            # то готовим его к удалению из графовой и векторной структур данных
            e_node_neighbours = self.db_conn.get_adjecent_nids(triplet.end_node.id)
            if len(e_node_neighbours) == 1 and e_node_neighbours[0] == triplet.start_node.id:
                graph_delete_info['e_node'] = True
                vector_delete_info['e_node'] = True

            # Если в графовой структуре данных содержиться только один триплет с таким-же строковым представлением (как у текущего triplet),
            # то готовим его к удалению как из графовой, так и из векторной структур данных. Если триплетов с таким же
            # строковым представлением несколько (>=2), то готовим его к удалению только из графовой структуры.
            same_str_id_count = self.db_conn.count_items(id=triplet.relation.id, id_type='relation')
            if same_str_id_count == 1:
                vector_delete_info['triplet'] = True

            vdb_delete_info[i] = vector_delete_info
            gdb_delete_info[i] = graph_delete_info

            self.db_conn.delete([triplet.id], {0: gdb_delete_info[i]})

        return gdb_delete_info, vdb_delete_info

    def count_items(self) -> Dict[str, int]:
        return self.db_conn.count_items()

    def clear(self) -> None:
        """Метод предназначен для удаления содержимого графовой структуры данных."""
        self.db_conn.clear()
