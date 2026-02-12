from .configs import MEM_UPDATOR_MAIN_LOG_PATH, DEFAULT_REPLACE_THESIS_TASK_CONFIG, DEFAULT_REPLACE_SIMPLE_TASK_CONFIG, LLMUpdatorConfig
from ....utils import Logger, Quadruplet, AgentTaskSolverConfig, AgentTaskSolver
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

    def find_simple_obsolete_quadruplet_ids(self, base_quadruplet: Quadruplet) -> List[str]:
        """Метод предназначен для поиска устаревших simple-quadruplets в графе знаний по сравнению с указанным (base_quadruplet) simple-quadruplet.

        :param base_quadruplet: Simple-квадруплет, на основании которого нужно искать устаревшие simple-квадруплеты в графе знаний.
        :type base_quadruplet: Quadruplet
        :return: Идентификаторы устаревших simple-квадруплетов.
        :rtype: List[str]
        """
        obsolete_quadruplet_ids = list()

        # Формируем уникальный список квадруплетов, которые инциденты вершинам
        # из текущего квадруплета (если такие вершины присутствуют в графе знаний)
        incident_quadruplets = dict()
        for base_node in [base_quadruplet.start_node, base_quadruplet.end_node]:

            # сопоставляем ноду из квадруплета нодам в графе знаний по полю name
            matched_nodes = self.kg_model.graph_struct.db_conn.read_by_name(
                name=base_node.name,  object_type=NodeType.object, object='node')

            for m_node in matched_nodes:
                neighbour_node_ids = self.kg_model.graph_struct.db_conn.get_adjecent_nids(m_node.id, [NodeType.object])
                for neighbour_id in neighbour_node_ids:
                    shared_quadruplets = self.kg_model.graph_struct.db_conn.get_quadruplets(m_node.id, neighbour_id)
                    incident_quadruplets.update({item.id: item for item in shared_quadruplets})

        incident_quadruplets = list(incident_quadruplets.values())

        # Выполняем поиск устаревших квадруплетов
        tmp_obsolete_quadruplet_ids, status = self.replace_simple_solver.solve(
            lang=self.config.lang, base_quadruplet=base_quadruplet, incident_quadruplets=incident_quadruplets)

        if status == ReturnStatus.success:
            obsolete_quadruplet_ids += tmp_obsolete_quadruplet_ids

        return list(set(obsolete_quadruplet_ids))

    def find_hyper_obsolete_quadruplet_ids(self, base_quadruplet: Quadruplet) -> List[str]:
        """Метод предназначен для поиска устаревших hyper-quadruplets в графе знаний по сравнению с указанным (base_quadruplet) hyper-quadruplet.

        :param base_quadruplet: Hyper-квадруплет, на основании которого нужно искать устаревшие hyper-квадруплеты в графе знаний.
        :type base_quadruplet: Quadruplet
        :return: Идентификаторы устаревших hyper-квадруплетов.
        :rtype: List[str]
        """
        obsolete_quadruplet_ids = list()

        # Формируем уникальный список квадруплетов, которые инциденты вершинам
        # из текущего квадруплета (если такие вершины присутствуют в графе знаний)
        incident_quadruplets = dict()

        # сопоставляем ноду из квадруплета нодам в графе знаний по полю name
        matched_nodes = self.kg_model.graph_struct.db_conn.read_by_name(
            name=base_quadruplet.start_node.name,  object_type=NodeType.object, object='node')

        for m_node in matched_nodes:
            neighbour_node_ids = self.kg_model.graph_struct.db_conn.get_adjecent_nids(m_node.id, [NodeType.hyper])

            for neighbour_id in neighbour_node_ids:
                shared_quadruplets = self.kg_model.graph_struct.db_conn.get_quadruplets(m_node.id, neighbour_id)

                incident_quadruplets.update({item.id: item for item in shared_quadruplets})

        incident_quadruplets = list(incident_quadruplets.values())

        # Выполняем поиск устаревших квадруплетов
        tmp_obsolete_quadruplet_ids, status = self.replace_hyper_solver.solve(
            lang=self.config.lang, base_quadruplet=base_quadruplet, incident_quadruplets=incident_quadruplets)

        if status == ReturnStatus.success:
            obsolete_quadruplet_ids += tmp_obsolete_quadruplet_ids

        return list(set(obsolete_quadruplet_ids))

    def find_episodic_o_obsolete_quadruplet_ids(self, base_quadruplet: Quadruplet) -> List[str]:
        """Метод предназначен для поиска устаревших episodic-quadruplets (с object-вершиной) в графе знаний по сравнению с указанным (base_quadruplet) episodic-quadruplet.

        :param base_quadruplet: Episodic-квадруплет (с object-вершиной), на основании которого нужно искать устаревшие episodic-квадруплеты в графе знаний.
        :type base_quadruplet: Quadruplet
        :return: Идентификаторы устаревших episodic-квадруплетов.
        :rtype: List[str]
        """
        obsolete_quadruplet_ids = list()

        # Сопоставляем object-сущность из квадруплета вершинам в графе знаний
        matched_object_nodes = self.kg_model.graph_struct.db_conn.read_by_name(
                name=base_quadruplet.start_node.name,  object_type=NodeType.object, object='node')

        if len(matched_object_nodes) == 0:
            return obsolete_quadruplet_ids

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
                    # Если у данных object-вершины и episodic-вершины нет общей hyper-вершины, значит данный episodic-квадруплет устрел
                    # и его нужно добавить в список на удаление
                    episodic_quadruplet = self.kg_model.graph_struct.db_conn.get_quadruplets(m_object_n.id, episodic_id)
                    assert len(episodic_quadruplet) == 1

                    obsolete_quadruplet_ids.append(episodic_quadruplet[0].id)

        return list(set(obsolete_quadruplet_ids))

    def find_episodic_h_obsolete_quadruplet_ids(self, base_quadruplet: Quadruplet) -> List[str]:
        """Метод предназначен для поиска устаревших episodic-quadruplets (c hyper-вершиной) в графе знаний по сравнению с указанным (base_quadruplet) episodic-quadruplet.

        :param base_quadruplet: Episodic-квадруплет (с hyper-вершиной), на основании которого нужно искать устаревшие episodic-квадруплеты в графе знаний.
        :type base_quadruplet: Quadruplet
        :return: Идентификаторы устаревших episodic-квадруплетов.
        :rtype: List[str]
        """
        obsolete_quadruplet_ids = list()

        # Сопоставляем hyper-сущность из квадруплета вершинам в графе знаний
        matched_hyper_nodes = self.kg_model.graph_struct.db_conn.read_by_name(
                name=base_quadruplet.start_node.name,  object_type=NodeType.hyper, object='node')

        if len(matched_hyper_nodes) == 0:
            return obsolete_quadruplet_ids

        for m_hyper_n in matched_hyper_nodes:

            # Проверям: с каким количеством object-вершин смежна данная hyper-вершина
            hyper_adj_object_ids = self.kg_model.graph_struct.db_conn.get_adjecent_nids(m_hyper_n.id, [NodeType.object])
            if len(hyper_adj_object_ids) < 1:
                # Если у hyper-вершины нет смежных object-вершин, то связи со всеми episodic-вершинами являются устаревшими
                hyper_adj_episodic_ids = self.kg_model.graph_struct.db_conn.get_adjecent_nids(m_hyper_n.id, [NodeType.episodic])
                for episodic_id in hyper_adj_episodic_ids:
                    episodic_quadruplets = self.kg_model.graph_struct.db_conn.get_quadruplets(m_hyper_n.id, episodic_id)
                    assert len(episodic_quadruplets) == 1
                    obsolete_quadruplet_ids.append(episodic_quadruplets[0].id)

        return list(set(obsolete_quadruplet_ids))

    def update_knowledge(self, new_quadruplets: List[Quadruplet], status_bar: bool = False) -> ReturnInfo:
        """Метод предназначен для изменения (удаления устаревшей / добавление новой информации) памяти (графа знаний) ассистента.

        :param new_quadruplets: Список квадруплетов с информацией для добавления в память (граф знаний) ассистента.
        :type new_quadruplets: List[Quadruplet]
        :return: Статус завершения операции с пояснительной информацией.
        :rtype: ReturnInfo
        """
        info = ReturnInfo()

        self.log("START KNOWLEDGE UPDATING...", verbose=self.config.verbose)
        self.log(f"QUADRUPLETS_ID: {create_id(f'{new_quadruplets}')}", verbose=self.config.verbose)

        if self.config.delete_obsolete_info:
            obsolete_quadruplets_counter = 0

            self.log(f"START SEARCH OF OBSOLETE QUADRUPLETS IN MEMORY...", verbose=self.config.verbose)
            # Note: обрабатываем каждый квадруплет по отдельности, так как в пуле могут быть такие,
            # которые заменяют одни и те же устаревшие квадруплеты.
            process = tqdm(new_quadruplets) if status_bar else new_quadruplets
            for quadruplet in process:
                self.log(f"BASE_QUADRUPLET ID: {quadruplet.id}", verbose=self.config.verbose)
                self.log(f"BASE_QUADRUPLET: {quadruplet}", verbose=self.config.verbose)

                if quadruplet.relation.type == RelationType.simple:
                    obsolete_q_ids = self.find_simple_obsolete_quadruplet_ids(quadruplet)
                elif quadruplet.relation.type == RelationType.hyper:
                    obsolete_q_ids = self.find_hyper_obsolete_quadruplet_ids(quadruplet)
                elif (quadruplet.relation.type == RelationType.episodic) and (quadruplet.start_node.type == NodeType.object):
                    obsolete_q_ids = self.find_episodic_o_obsolete_quadruplet_ids(quadruplet)
                elif (quadruplet.relation.type == RelationType.episodic) and (quadruplet.start_node.type == NodeType.hyper):
                    obsolete_q_ids = self.find_episodic_h_obsolete_quadruplet_ids(quadruplet)
                else:
                    raise ValueError

                self.log("RESULT:", verbose=self.config.verbose)
                self.log(f"* OBSOLETE QUADRUPLETS AMOUNT - {len(obsolete_q_ids)}", verbose=self.config.verbose)
                self.log(f"* OBSOLETE QUADRUPLETS IDS - {obsolete_q_ids}", verbose=self.config.verbose)
                obsolete_quadruplets_counter += len(obsolete_q_ids)

                self.log(f"DELETING OBSOLETE QUADRUPLETS FROM MEMORY...", verbose=self.config.verbose)
                obsolete_quadruplets = self.kg_model.graph_struct.db_conn.read(obsolete_q_ids)

                self.log(f"QUADRUPLETS TO DELETE: {len(obsolete_quadruplets)}", verbose=self.config.verbose)
                for obs_q in obsolete_quadruplets:
                    self.log(f"* [{obs_q.id}] {obs_q}", verbose=self.config.verbose)

                remove_info = self.kg_model.remove_knowledge(obsolete_quadruplets)
                self.log(f"REMOVE INFO: {remove_info}", verbose=self.config.verbose)

                self.log(f"ADDING NEW QUADRUPLET TO MEMORY...", verbose=self.config.verbose)

                add_info = self.kg_model.add_knowledge([quadruplet])
                self.log(f"ADD INFO: {add_info}", verbose=self.config.verbose)

            self.log(f"FINAL RESULT:", verbose=self.config.verbose)
            self.log(f"- SUM AMOUNT OF OBSOLETE QUADRUPLETS: {obsolete_quadruplets_counter}", verbose=self.config.verbose)

        else:
            self.log(f"ADDING QUADRUPLETS TO MEMORY...", verbose=self.config.verbose)

            add_info = self.kg_model.add_knowledge(new_quadruplets, status_bar=status_bar)
            self.log(f"ADD INFO: {add_info}", verbose=self.config.verbose)

        self.log(f"FINAL STATUS: {STATUS_MESSAGE[info.status]}", verbose=self.config.verbose)

        return info
