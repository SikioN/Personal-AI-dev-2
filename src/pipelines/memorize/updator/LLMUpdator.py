from .configs import MEM_UPDATOR_MAIN_LOG_PATH, DEFAULT_REPLACE_THESIS_TASK_CONFIG, DEFAULT_REPLACE_SIMPLE_TASK_CONFIG, LLMUpdatorConfig
from ....utils import Logger, Triplet, AgentTaskSolverConfig, AgentTaskSolver
from ....utils.data_structs import RelationType, NodeType, create_id
from ....utils.errors import ReturnInfo, ReturnStatus, STATUS_MESSAGE
from ....agents import AgentDriver, AgentDriverConfig
from ....kg_model import KnowledgeGraphModel
from ....db_drivers.kv_driver import KeyValueDriverConfig

from dataclasses import dataclass, field
from typing import List
from tqdm import tqdm

class LLMUpdator:
    """Верхнеуровневый класс первой стадии Memorize-конвейера для актуализации знаний в памяти ассистента.

    :param kg_model: Модель памяти (графа знаний) ассистента.
    :type kg_model: KnowledgeGraphModel
    :param config: Конфигурация Updator-стадии. Значение по умолчанию LLMUpdatorConfig().
    :type config: LLMUpdatorConfig
    """

    def __init__(self, kg_model: KnowledgeGraphModel, config: LLMUpdatorConfig = LLMUpdatorConfig(),
                 cache_kvdriver_config: KeyValueDriverConfig = None) -> None:
        self.config = config
        self.kg_model = kg_model
        self.log = config.log

        self.agent = AgentDriver.connect(config.adriver_config)
        self.replace_simple_solver = AgentTaskSolver(
            self.agent, self.config.replace_simple_task_config, cache_kvdriver_config)
        self.replace_hyper_solver = AgentTaskSolver(
            self.agent, self.config.replace_thesis_task_config, cache_kvdriver_config)

    def find_simple_obsolete_triplet_ids(self, base_triplet: Triplet) -> List[str]:
        """Метод предназначен для поиска устаревших simple-триплетов в графе знаний по сравнению с указанным (base_triplet) simple-триплетом.

        :param base_triplet: Simple-триплет, на основании которого нужно искать устаревшие simple-триплеты в графе знаний.
        :type base_triplet: Triplet
        :return: Идентификаторы устаревших simple-триплетов.
        :rtype: List[str]
        """
        obsolete_triplet_ids = list()

        # Формируем уникальный список триплетов, которые инциденты вершинам
        # из текущего триплета (если такие вершины присутствуют в графе знаний)
        incident_triplets = dict()
        for base_node in [base_triplet.start_node, base_triplet.end_node]:

            # сопоставляем ноду из триплета нодам в графе знаний по полю name
            matched_nodes = self.kg_model.graph_struct.db_conn.read_by_name(
                name=base_node.name,  object_type=NodeType.object, object='node')

            for m_node in matched_nodes:
                neighbour_node_ids = self.kg_model.graph_struct.db_conn.get_adjecent_nids(m_node.id, [NodeType.object])
                for neighbour_id in neighbour_node_ids:
                    shared_triplets = self.kg_model.graph_struct.db_conn.get_triplets(m_node.id, neighbour_id)
                    incident_triplets.update({item.id: item for item in shared_triplets})

        incident_triplets = list(incident_triplets.values())

        # Выполняем поиск устаревших триплетов
        tmp_obsolete_triplet_ids, status = self.replace_simple_solver.solve(
            lang=self.config.lang, base_triplet=base_triplet, incident_triplets=incident_triplets)

        if status == ReturnStatus.success:
            obsolete_triplet_ids += tmp_obsolete_triplet_ids

        return list(set(obsolete_triplet_ids))

    def find_hyper_obsolete_triplet_ids(self, base_triplet: Triplet) -> List[str]:
        """Метод предназначен для поиска устаревших hyper-триплетов в графе знаний по сравнению с указанным (base_triplet) hyper-триплетом.

        :param base_triplet: Hyper-триплет, на основании которого нужно искать устаревшие hyper-триплеты в графе знаний.
        :type base_triplet: Triplet
        :return: Идентификаторы устаревших hyper-триплетов.
        :rtype: List[str]
        """
        obsolete_triplet_ids = list()

        # Формируем уникальный список триплетов, которые инциденты вершинам
        # из текущего триплета (если такие вершины присутствуют в графе знаний)
        incident_triplets = dict()

        # сопоставляем ноду из триплета нодам в графе знаний по полю name
        matched_nodes = self.kg_model.graph_struct.db_conn.read_by_name(
            name=base_triplet.start_node.name,  object_type=NodeType.object, object='node')

        for m_node in matched_nodes:
            neighbour_node_ids = self.kg_model.graph_struct.db_conn.get_adjecent_nids(m_node.id, [NodeType.hyper])

            for neighbour_id in neighbour_node_ids:
                shared_triplets = self.kg_model.graph_struct.db_conn.get_triplets(m_node.id, neighbour_id)

                incident_triplets.update({item.id: item for item in shared_triplets})

        incident_triplets = list(incident_triplets.values())

        # Выполняем поиск устаревших триплетов
        tmp_obsolete_triplet_ids, status = self.replace_hyper_solver.solve(
            lang=self.config.lang, base_triplet=base_triplet, incident_triplets=incident_triplets)

        if status == ReturnStatus.success:
            obsolete_triplet_ids += tmp_obsolete_triplet_ids

        return list(set(obsolete_triplet_ids))

    def find_episodic_o_obsolete_triplet_ids(self, base_triplet: Triplet) -> List[str]:
        """Метод предназначен для поиска устаревших episodic-триплетов (с object-вершиной) в графе знаний по сравнению с указанным (base_triplet) episodic-триплетом.

        :param base_triplet: Episodic-триплет (с object-вершиной), на основании которого нужно искать устаревшие episodic-триплеты в графе знаний.
        :type base_triplet: Triplet
        :return: Идентификаторы устаревших episodic-триплетов.
        :rtype: List[str]
        """
        obsolete_triplet_ids = list()

        # Сопоставляем object-сущность из триплета вершинам в графе знаний
        matched_object_nodes = self.kg_model.graph_struct.db_conn.read_by_name(
                name=base_triplet.start_node.name,  object_type=NodeType.object, object='node')

        if len(matched_object_nodes) == 0:
            return obsolete_triplet_ids

        for m_object_n in matched_object_nodes:
            # Для object-вершины ищем смежные episodic-вершины
            object_adj_episodic_ids = self.kg_model.graph_struct.db_conn.get_adjecent_nids(m_object_n.id, [NodeType.episodic])

            if len(object_adj_episodic_ids) < 1:
                continue

            # Для object-вершины ищем смежные hyper-вершины
            object_adj_hyper_ids = set(self.kg_model.graph_struct.db_conn.get_adjecent_nids(m_object_n.id, [NodeType.hyper]))

            for episodic_id in object_adj_episodic_ids:
                # Для episodic-вершины, смежной с текущей object-вершиной, ищем смежные hyper-вершины
                episodic_adj_hyper_ids = self.kg_model.graph_struct.db_conn.get_adjecent_nids(episodic_id, [NodeType.hyper])

                shared_hyper_ids = object_adj_hyper_ids.intersection(set(episodic_adj_hyper_ids))
                if len(shared_hyper_ids) < 1:
                    # Если у данных object-вершины и episodic-вершины нет общей hyper-вершины, значит данный episodic-триплет устрел
                    # и его нужно добавить в список на удаление
                    episodic_triplet = self.kg_model.graph_struct.db_conn.get_triplets(m_object_n.id, episodic_id)
                    assert len(episodic_triplet) == 1

                    obsolete_triplet_ids.append(episodic_triplet[0].id)

        return list(set(obsolete_triplet_ids))

    def find_episodic_h_obsolete_triplet_ids(self, base_triplet: Triplet) -> List[str]:
        """Метод предназначен для поиска устаревших episodic-триплетов (c hyper-вершиной) в графе знаний по сравнению с указанным (base_triplet) episodic-триплетом.

        :param base_triplet: Episodic-триплет (с hyper-вершиной), на основании которого нужно искать устаревшие episodic-триплеты в графе знаний.
        :type base_triplet: Triplet
        :return: Идентификаторы устаревших episodic-триплетов.
        :rtype: List[str]
        """
        obsolete_triplet_ids = list()

        # Сопоставляем hyper-сущность из триплета вершинам в графе знаний
        matched_hyper_nodes = self.kg_model.graph_struct.db_conn.read_by_name(
                name=base_triplet.start_node.name,  object_type=NodeType.hyper, object='node')

        if len(matched_hyper_nodes) == 0:
            return obsolete_triplet_ids

        for m_hyper_n in matched_hyper_nodes:

            # Проверям: с каким количеством object-вершин смежна данная hyper-вершина
            hyper_adj_object_ids = self.kg_model.graph_struct.db_conn.get_adjecent_nids(m_hyper_n.id, [NodeType.object])
            if len(hyper_adj_object_ids) < 1:
                # Если у hyper-вершины нет смежных object-вершин, то связи со всеми episodic-вершинами являются устаревшими
                hyper_adj_episodic_ids = self.kg_model.graph_struct.db_conn.get_adjecent_nids(m_hyper_n.id, [NodeType.episodic])
                for episodic_id in hyper_adj_episodic_ids:
                    episodic_triplets = self.kg_model.graph_struct.db_conn.get_triplets(m_hyper_n.id, episodic_id)
                    assert len(episodic_triplets) == 1
                    obsolete_triplet_ids.append(episodic_triplets[0].id)

        return list(set(obsolete_triplet_ids))

    def update_knowledge(self, new_triplets: List[Triplet], status_bar: bool = False) -> ReturnInfo:
        """Метод предназначен для изменения (удаления устаревшей / добавление новой информации) памяти (графа знаний) ассистента.

        :param new_triplets: Список триплетов с информацией для добавления в память (граф знаний) ассистента.
        :type new_triplets: List[Triplet]
        :return: Статус завершения операции с пояснительной информацией.
        :rtype: ReturnInfo
        """
        info = ReturnInfo()

        self.log("START KNOWLEDGE UPDATING...", verbose=self.config.verbose)
        self.log(f"TRIPLETS_ID: {create_id(f'{new_triplets}')}", verbose=self.config.verbose)

        if self.config.delete_obsolete_info:
            obsolete_triplets_counter = 0

            self.log(f"START SEARCH OF OBSOLETE TRIPLETS IN MEMORY...", verbose=self.config.verbose)
            # Note: обрабатываем каждый триплет по отдельности, так как в пуле триплетов могут быть такие,
            # которые заменяют одни и те же устаревшие триплеты. Соответсвенно, мы должны итеративно обновлять память и сохранить
            # только последнюю актуальную информацию.
            process = tqdm(new_triplets) if status_bar else new_triplets
            for triplet in process:
                self.log(f"BASE_TRIPLET ID: {triplet.id}", verbose=self.config.verbose)
                self.log(f"BASE_TRIPLET: {triplet}", verbose=self.config.verbose)

                if triplet.relation.type == RelationType.simple:
                    obsolete_t_ids = self.find_simple_obsolete_triplet_ids(triplet)
                elif triplet.relation.type == RelationType.hyper:
                    obsolete_t_ids = self.find_hyper_obsolete_triplet_ids(triplet)
                elif (triplet.relation.type == RelationType.episodic) and (triplet.start_node.type == NodeType.object):
                    obsolete_t_ids = self.find_episodic_o_obsolete_triplet_ids(triplet)
                elif (triplet.relation.type == RelationType.episodic) and (triplet.start_node.type == NodeType.hyper):
                    obsolete_t_ids = self.find_episodic_h_obsolete_triplet_ids(triplet)
                else:
                    raise ValueError

                self.log("RESULT:", verbose=self.config.verbose)
                self.log(f"* OBSOLETE TRIPELTS AMOUNT - {len(obsolete_t_ids)}", verbose=self.config.verbose)
                self.log(f"* OBSOLETE TRIPLET IDS - {obsolete_t_ids}", verbose=self.config.verbose)
                obsolete_triplets_counter += len(obsolete_t_ids)

                self.log(f"DELETING OBSOLETE TRIPLETS FROM MEMORY...", verbose=self.config.verbose)
                obsolete_triplets = self.kg_model.graph_struct.db_conn.read(obsolete_t_ids)

                self.log(f"TRIPLETS TO DELETE: {len(obsolete_triplets)}", verbose=self.config.verbose)
                for obs_t in obsolete_triplets:
                    self.log(f"* [{obs_t.id}] {obs_t}", verbose=self.config.verbose)

                remove_info = self.kg_model.remove_knowledge(obsolete_triplets)
                self.log(f"REMOVE INFO: {remove_info}", verbose=self.config.verbose)

                self.log(f"ADDING NEW TRIPLET TO MEMORY...", verbose=self.config.verbose)

                add_info = self.kg_model.add_knowledge([triplet])
                self.log(f"ADD INFO: {add_info}", verbose=self.config.verbose)

            self.log(f"FINAL RESULT:", verbose=self.config.verbose)
            self.log(f"- SUM AMOUNT OF OBSOLETE TRIPELTS: {obsolete_triplets_counter}", verbose=self.config.verbose)

        else:
            self.log(f"ADDING TRIPLETS TO MEMORY...", verbose=self.config.verbose)

            add_info = self.kg_model.add_knowledge(new_triplets, status_bar=status_bar)
            self.log(f"ADD INFO: {add_info}", verbose=self.config.verbose)

        self.log(f"FINAL STATUS: {STATUS_MESSAGE[info.status]}", verbose=self.config.verbose)

        return info
