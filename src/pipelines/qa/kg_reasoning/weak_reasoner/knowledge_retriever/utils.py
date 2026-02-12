from typing import List, Dict
from abc import ABC, abstractmethod
from dataclasses import dataclass

from ......utils.data_structs import QueryInfo, Quadruplet
from .errors import NOT_VALID_ID_ERROR_MSG, NO_START_NODE_IN_PARENT_ERROR_MSG, EMPTY_PARENT_ERROR_MSG

def get_nodes_path(parent: Dict[str, str], end_node_id: str) -> List[str]:
    """Метод предназначен для получения пути обхода графа, заканчивая заданной конечной end_node_id вершиной.
    Путь должен быть ацикличным: есть стартовая вершин, у которой нет родителя.
    
    :param parent: Словарь с идентификаторами родительских вершин. Ключи - идентикиаторы вершин, которые были посещены; значения - идентификаторы вершины (родитель), из которой был выполнен переход в данную (ключ) вершину.
    :type parent: Dict[str, str]
    :param end_node_id: Идентификатор последней посещённой вершины.
    :type end_node_id: str
    :return: Последовательность посещённых вершин: от конечной до стартовой (в обратном порядке).
    :rtype: List[str]
    """
    if type(end_node_id) is not str:
        raise ValueError(NOT_VALID_ID_ERROR_MSG)
    if None not in parent.values():
        raise ValueError(NO_START_NODE_IN_PARENT_ERROR_MSG)
    if len(parent) == 0:
        raise ValueError(EMPTY_PARENT_ERROR_MSG)

    path, end_flag, cur_n = [end_node_id], False, end_node_id
    while not end_flag:
        next_n = parent[cur_n]
        if next_n is None:
            end_flag = True
        else:
            path.append(next_n)
            cur_n = next_n
    return path

class AbstractQuadrupletsFilter(ABC):
    """Интерфейс алгоритмов фильтрации/ранжирования квадруплетов."""
    @abstractmethod
    def apply_filter(self, query_info: QueryInfo, quadruplets: List[Quadruplet]) -> List[Quadruplet]:
        """Метод предназначен для применения операциии ранжирования/фильтрации к набору квадруплетов на основе меры их релевантности к user-вопросу.

        :param query_info: Структура данных с user-вопросом.
        :type query_info: QueryInfo
        :param quadruplets: Набор квадруплетов для ранжирования/отбора.
        :type quadruplets: List[Quadruplet]
        :return: Набор квадруплетов, релевантных данному user-вопросу.
        :rtype: List[Quadruplet]
        """
        pass

class AbstractQuadrupletsRetriever(ABC):
    """Интерфейс алгоритмов извлечения квадруплетов из графа знаний."""
    @abstractmethod
    def get_relevant_quadruplets(self, query_info: QueryInfo) -> List[Quadruplet]:
        """Метод предназначен для извлечения квадруплетов из графа знаний на основе информации из user-вопроса. Возвращаемый список квадруплетов не содержит дубликатов (по строковому представлению).

        :param query_info: Структура данных с информацией о user-вопросе.
        :type query_info: QueryInfo
        :return: Набор квадруплетов, извлечённый из графа знаний.
        :rtype: List[Quadruplet]
        """
        pass

@dataclass
class BaseGraphSearchConfig:
    """Базовая конфигурация алгоритмов по извлечению квадруплетов из графа знаний."""
    pass

@dataclass
class BaseQuadrupletsFilterConfig:
    """Базовая конфигурация алгоритмов по ранжированию/фильтрации квадруплетов."""
    pass
