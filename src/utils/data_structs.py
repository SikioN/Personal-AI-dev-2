from dataclasses import dataclass, field
from typing import List, Union, Tuple, Dict
from enum import Enum
import hashlib

from src.db_drivers.vector_driver import VectorDBInstance

class NodeType(Enum):
    """Доступные типы вершин."""
    #: Вершина хранит атомарную сущность.
    object = "object"
    #: Вершина хранит тезисную информацию.
    hyper = "hyper"
    #: Вершина хранит эпизодическую информацию.
    episodic = "episodic"
    #: Вершина хранит временную информацию.
    time = "time"

NODES_TYPES_MAP = {
    'object': NodeType.object,
    'hyper': NodeType.hyper,
    'episodic': NodeType.episodic,
    'time': NodeType.time,
}

class RelationType(Enum):
    """Доступные типы связей/триплетов."""
    #: Связывает только вершины с типом 'object'.
    simple = "simple"
    #: Связывает пары вершин ('object','hyper').
    hyper = "hyper"
    #: Связывает пары вершин ('object', 'episodic') и ('object', 'hyper').
    episodic = "episodic"
    #: Связывает пары вершин ('episodic', 'time') и ('hyper', 'time').
    time = "time"

RELATIONS_TYPES_MAP = {
    'simple': RelationType.simple,
    'hyper': RelationType.hyper,
    'episodic': RelationType.episodic,
    'time': RelationType.time,
}

@dataclass
class Node:
    """Структура данных вершины."""
    #: Главная смысловая информация.
    name: str
    #: Тип вершины.
    type: NodeType
    #: Дополнительные свойства вершины.
    prop: dict = field(default_factory=lambda: dict())
    #: Строковое представление вершины.
    stringified: str = None
    #: Идентификатор вершины, полученный на основе её строкового представления.
    id: str = None

@dataclass
class Relation:
    "Струкура данных связи."
    #: Главная смысловая информация.
    name: str
    # Тип связи.
    type: RelationType
    #: Дополнительные свойства связи.
    prop: dict = field(default_factory=lambda: dict())
    #: Идентификатор связи, полученный на основе строкового представления триплета, в котором она (связь) находится.
    #: Данное значение отличается от значения в поле id объекта класса Triplet.
    id: str = None

@dataclass
class Quadruplet:
    """Структура данных квадруплета (S, R, O, T)."""
    # Subject-часть квадруплета.
    start_node: Node
    # Отношение сущностей в квадруплете. Отношение идёт от subject к object.
    relation: Relation
    # Object-часть квадруплета.
    end_node: Node
    #: Временная/Time-часть квадруплета.
    time: Node
    #: Строковое представление квадруплета.
    stringified: str = None
    #: Идентификатор квадруплета, полученный на основе идентификаторов его частей.
    id: str = None

class BaseCreator:
    @staticmethod
    def add_str_props(obj: Union[Relation, Node], obj_str: str) -> str:
        """Метод предназначен для добавления свойств, хранящихся в Relation/Node-структуре, к их базовым строковым представлениям.

        :param obj: Структура объекта, строковое представление которого обогащается его свойствами.
        :type obj: Union[Relation, Node]
        :param obj_str: Текущее строковое представление объекта.
        :type obj_str: str
        :return: Обогащённое строковое представление объекта.
        :rtype: str
        """
        str_prop = '; '.join([f"{k}: {v}" for k, v in obj.prop.items() if k not in ['name', 'type', 'raw_time', 'time', 'str_id', 't_id', 'time_node_id']])
        if str_prop:
            obj_str += f" ({str_prop})"
        return obj_str

class RelationCreator(BaseCreator):
    @staticmethod
    def create(r_type: Union[str, RelationType], name: str = None,  prop: Dict = None) -> Relation:
        """Метод предназначен для создания структуры данных связи с указанным содержанием.

        :param r_type: Тип создаваемой связи в строковой- или Enum-структуре данных.
        :type r_type: Union[str, RelationType]
        :param name: Главная смысловая информация, которая будет добавлена в связь. Значение по умолчанию None.
        :type name: str, optional
        :param prop: Дополнительные свойства создаваемой связи. Значение по умолчанию None.
        :type prop: Dict, optional
        :return: Созданная структура данных связи.
        :rtype: Relation
        """
        if type(r_type) is not RelationType:
            formated_r_type = RELATIONS_TYPES_MAP.get(r_type, None)
            if formated_r_type is None:
                raise ValueError
            else:
                r_type = formated_r_type

        if r_type is not RelationType.simple:
            name = r_type.value
        elif name is None:
            raise ValueError

        prop = dict() if prop is None else prop

        rel = Relation(name=name, type=r_type, prop=prop)
        return rel

class NodeCreator(BaseCreator):
    @staticmethod
    def create(n_type: Union[str, NodeType], name: str, prop: Dict = None, add_stringified_node: bool = True) -> Node:
        """Метод предназначен для создания структуры данных вершины с указанным содержанием.

        :param n_type: Тип создаваемой вершины в строковой- или Enum-структуре данных.
        :type n_type: Union[str, NodeType]
        :param name: Главная смысловая информация, которая будет добавлена в вершину.
        :type name: str
        :param prop: Дополнительные свойства создаваемой вершины. Значение по умолчанию None.
        :type prop: Dict, optional
        :param add_stringified_node: Если True, то в структуру данных вершины будет сохранено её строковое представление, иначе соответствующее поле будет хранить None. Значение по умолчанию True.
        :type add_stringified_node: bool, optional
        :return: Созданная структура данных вершины.
        :rtype: Node
        """
        if type(n_type) is not NodeType:
            formated_n_type = NODES_TYPES_MAP.get(n_type, None)
            if formated_n_type is None:
                raise ValueError
            else:
                n_type = formated_n_type

        prop = dict() if prop is None else prop

        node = Node(name=name, type=n_type, prop=prop)
        _, str_node = NodeCreator.stringify(node)
        node.id = create_id(str_node)
        if add_stringified_node:
            node.stringified = str_node
        return node

    @staticmethod
    def stringify(node: Node) -> Tuple[str,str]:
        """Метод предназначен для приведения структуры данных вершины в её строковое представление.

        :param triplet: Структура данных вершины.
        :type triplet: Node
        :return: Кортеж, состоящий из двух объектов: (1) идентификатор вершины; (2) строковое представление вершины.
        :rtype: Typle[str,str]
        """
        str_node = ""
        if "time" in node.prop.keys():
            str_node += node.prop["time"] + ": "
        str_node += NodeCreator.add_str_props(node, str(node.name))
        return node.id, str_node

def create_id_for_node_pair(node1_id: str, node2_id: str) -> str:
    """Метод предназначен для условной генерации идентификатора к паре вершин. Вершины представлены в виде их собственных идентификаторов.
    При указании такой же пары вершин, но в другом порядке, полученный идентификатор не изменится: инвариант относительно перестановок.

    :param node1_id: Идентификатор первой вершины.
    :type node1_id: str
    :param node2_id: Идентификатор второй вершины.
    :type node2_id: str
    :return: Идентификатор пары вершин.
    :rtype: str
    """
    start_id, end_id = (node1_id, node2_id) if node1_id > node2_id else (node2_id, node1_id)
    return hashlib.md5((start_id+end_id).encode()).hexdigest()

def create_id(seed: str) -> str:
    return hashlib.md5(seed.encode()).hexdigest()

class QuadrupletCreator(BaseCreator):
    @staticmethod
    def create(start_node: Node, relation: Relation, end_node: Node, time: Node = None,
            add_stringified_quadruplet: bool = True, t_id: str = None) -> Quadruplet:
        """Метод предназначен для создания структуры данных квадруплета (S, R, O, T)."""

        if time is None:
            # Default to "Always" if not provided
            time = NodeCreator.create(NodeType.time, "Always", add_stringified_node=True)

        quadruplet = Quadruplet(start_node, relation, end_node, time=time)
        _, str_quadruplet = QuadrupletCreator.stringify(quadruplet)
        if add_stringified_quadruplet:
            quadruplet.stringified = str_quadruplet

        quadruplet.relation.id = create_id(str_quadruplet)

        if t_id is None:
            # ID depends on S, R, O, T
            quadruplet.id = create_id(''.join(
                [quadruplet.start_node.id, quadruplet.relation.id, quadruplet.end_node.id, quadruplet.time.id]))
        else:
            quadruplet.id = t_id

        return quadruplet

    @staticmethod
    def stringify(quadruplet: Quadruplet) -> Tuple[str,str]:
        """Метод предназначен для приведения структуры данных в строковое представление."""
        rel_type = quadruplet.relation.type
        str_quadruplet = ""

        # Добавляем временной маркер в самое начало, если он не "Always"
        if quadruplet.time is not None and quadruplet.time.name != "Always":
             str_quadruplet += f"{quadruplet.time.name}: "

        if (rel_type == RelationType.episodic) or (rel_type == RelationType.hyper) or (rel_type == RelationType.time):
            str_quadruplet += QuadrupletCreator.add_str_props(quadruplet.end_node, str(quadruplet.end_node.name))

        elif rel_type == RelationType.simple:
            parts = [
                QuadrupletCreator.add_str_props(quadruplet.start_node, str(quadruplet.start_node.name)),
                QuadrupletCreator.add_str_props(quadruplet.relation, str(quadruplet.relation.name)),
                QuadrupletCreator.add_str_props(quadruplet.end_node, str(quadruplet.end_node.name))
            ]
            str_quadruplet += " ".join(parts)

        else:
            raise KeyError

        return quadruplet.relation.id, str_quadruplet

    @staticmethod
    def from_json(json_quadruplet: Dict) -> Quadruplet:
        """Метод предназначен для перевода квадруплета из json-формата."""

        subject = NodeCreator.create(
            name=json_quadruplet['subject']['name'],
            n_type=json_quadruplet['subject']['type'],
            prop=json_quadruplet['subject'].get('prop', None))
        relation = RelationCreator.create(
            name=json_quadruplet['relation'].get('name', None),
            r_type=json_quadruplet['relation']['type'],
            prop=json_quadruplet['relation'].get('prop', None))
        object = NodeCreator.create(
            name=json_quadruplet['object']['name'],
            n_type=json_quadruplet['object']['type'],
            prop=json_quadruplet['object'].get('prop', None))
        
        # Parse time if available
        time_data = json_quadruplet.get('time', {})
        time_name = time_data.get('name', 'Always')
        time = NodeCreator.create(NodeType.time, time_name, prop=time_data.get('prop', None), add_stringified_node=True)

        return QuadrupletCreator.create(start_node=subject, relation=relation, end_node=object, time=time)

#from ..embedding_functions import VectorDBInstance

@dataclass
class QueryInfo:
    """Класс предназначен для хранения промежуточных результатов по user-вопросу,
    полученных в рамках его обработки QA-конвейером.

    :param query: Исходный user-вопрос.
    :type query: str
    :param entities: Набор сущностей, который был извлечён из user-вопроса. Значение по умолчанию None.
    :type entities: List[str]
    :param linked_nodes: Набор объектов (вершин) из памяти (графа знаний) ассистента, который был сопоставлен сущностям из user-вопроса. Значение по умолчанию None.
    :type linked_nodes: List[object]
    :param linked_nodes_by_entities: Значение по умолчанию None.
    :type  linked_nodes_by_entities: List[object]
    """
    query: str
    entities: List[str] = None
    linked_nodes: List[VectorDBInstance] = None
    linked_nodes_by_entities: List[VectorDBInstance] = None

    def to_str(self):
        str_entities = ';'.join(sorted(self.entities)) if self.entities is not None else "None"
        str_lnodes = ';'.join(sorted(list(map(lambda item: item.document, self.linked_nodes)))) if self.linked_nodes is not None else "None"
        str_lnodes_by_entities = ';'.join(sorted(list(map(lambda item: ';;'.join(item), self.linked_nodes_by_entities)))) if self.linked_nodes_by_entities is not None else "None"
        return f"{str_entities}|{str_lnodes}|{str_lnodes_by_entities}"
