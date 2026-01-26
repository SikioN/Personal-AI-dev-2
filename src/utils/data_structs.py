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
class Triplet:
    """Структура данных триплета."""
    # Subject-часть триплета.
    start_node: Node
    # Отношение сущностей в триплете. Отношение идёт от subject к object.
    relation: Relation
    # Object-часть триплета.
    # Object-часть триплета.
    end_node: Node
    #: Временная/Time-часть триплета.
    time: Node = None
    #: Строковое представление триплета.
    stringified: str = None
    #: Идентификатор триплета, полученный на основе идентификаторов его частей.
    #: Данное значение отличается от значения в поле id объекта класса Relation.
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
        str_prop = '; '.join([f"{k}: {v}" for k, v in obj.prop.items() if k not in ['name', 'type', 'raw_time', 'time', 'str_id', 't_id']])
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

class TripletCreator(BaseCreator):
    @staticmethod
    def create(start_node: Node, relation: Relation, end_node: Node, time: Node = None,
            add_stringified_triplet: bool = True, t_id: str = None) -> Triplet:
        """Метод предназначен для создания структуры данных триплета с указанным содержанием.
        Триплет является ориентированным: у связи между вершинами (парой subject/object) есть направление.

        :param start_node: Структура данных стартовой (subject) вершины триплета.
        :type start_node: Node
        :param relation: Структура данных связи триплета.
        :type relation: Relation
        :param end_node: Структура данных конечной (object) вершины триплета.
        :type end_node: Node
        :param time: Структура данных времени (time) вершины триплета. Значение по умолчанию None.
        :type time: Node, optional
        :param add_stringified_triplet: Если True, то в структуру данных триплета будет сохранено его строковое представление, иначе соответствующее поле будет хранить None. Значение по умолчанию True.
        :type add_stringified_triplet: bool, optional
        :param t_id: Идентификатор, который будет назначен триплету вручную. Если идентификатор не указан (None), то он будет назначен триплету автоматически. Значение по умолчанию None.
        :type t_id: str, optional
        :return: Созданная структура данных триплета.
        :rtype: Triplet
        """

        triplet = Triplet(start_node, relation, end_node, time=time)
        _, str_triplet = TripletCreator.stringify(triplet)
        if add_stringified_triplet:
            triplet.stringified = str_triplet

        triplet.relation.id = create_id(str_triplet)

        if t_id is None:
            time_id = triplet.time.id if triplet.time is not None else ""
            triplet.id = create_id(''.join(
                [triplet.start_node.id,triplet.relation.id,triplet.end_node.id, time_id]))
        else:
            triplet.id = t_id

        return triplet

    @staticmethod
    def stringify(triplet: Triplet) -> Tuple[str,str]:
        """Метод предназначен для приведения Triplet-структуры данных в её строковое представление. Строковое представление зависит от типа триплета (Triplet.relation.type):
        (1) simple - используется информация из обеих вершин и связи; (2) hyper/episodic - используется информация только из конечной (object) вершины.

        :param triplet: Структура данных триплета.
        :type triplet: Triplet
        :raises KeyError: В триплете у связи указан тип, который не поддерживается.
        :return: Кортеж из двух объектов: (1) идентификатор связи между данной парой вершин из триплета; (2) строковое представление триплета.
        :rtype: Tuple[str,str]
        """
        rel_type = triplet.relation.type
        if (rel_type == RelationType.episodic) or (rel_type == RelationType.hyper) or (rel_type == RelationType.time):
            str_triplet = ""
            if "time" in triplet.end_node.prop.keys():
                str_triplet += triplet.end_node.prop["time"] + ": "
            str_triplet += TripletCreator.add_str_props(triplet.end_node, str(triplet.end_node.name))

        elif rel_type == RelationType.simple:
            str_triplet = ""
            # Если есть явная вершина времени, добавляем её в начало
            if triplet.time is not None:
                str_triplet += f"{triplet.time.name}: "
            # Иначе проверяем старый способ через свойства (для обратной совместимости)
            elif "time" in triplet.relation.prop.keys():
                str_triplet += triplet.relation.prop["time"] + ": "

            str_triplet += " ".join([
                TripletCreator.add_str_props(triplet.start_node, str(triplet.start_node.name)),
                TripletCreator.add_str_props(triplet.relation, str(triplet.relation.name)),
                TripletCreator.add_str_props(triplet.end_node, str(triplet.end_node.name))])


        else:
            raise KeyError

        return triplet.relation.id, str_triplet

    @staticmethod
    def from_json(json_triplet: Dict) -> Triplet:
        """Метод предназначен для перевода триплета из json-формата (полуструктурированного) в dataclass-формат (структурированный) хранения.
        Триплет является направленным: связь идёт от субъекта к объекту.

        Триплет в json-формате должен содержать следующие ключи: "subject", "relation" и "object". По каждому из данных ключей должен храниться словарь
        со следующими ключами: "name", "type" и "prop". По ключу "name" должна храниться строка текста на естественном языке, представляющая основную
        смысловую информацию данной части триплета. По ключу "prop" в виде словаря могут храниться дополнительные свойства данной части триплета.
        Если у компоненты триплета нет свойств, то соответствующее поле "prop" можно не указывать/заполнять. По ключу "type" могут храниться только следующие значения:
        * в случае "subject"/"object"-компонент это "object", "hyper" и "episodic";
        * в случае "relation"-компоненты это "simple", "hyper" и "episodic".

        В случае если по ключу "type" у "relation"-компоненты триплета указывается значение "hyper" или "episodic", то значение по соответствующему ключу "name"
        можно не указывать: указанное вручную значение в поле "name" использоваться не будет.

        Примеры валидных json-триплетов:
        1. {'subject': {'name': 'qwe', 'type': 'object', 'prop': {'k1': 'v1'}},
        'relation': {'name': 'rty', 'type': 'simple'}, 'object': {'name': 'uio', 'type': 'object'}};
        2. {'subject': {'name': 'asd', 'type': 'object', 'prop': {'k2': 'v2'}},
        'relation': {'type': 'hyper', 'prop': {'k3': 'v3'}}, 'object': {'name': 'fgh', 'type': 'hyper'}};
        3. {'subject': {'name': 'jkl', 'type': 'hyper', 'prop': {'k4': 'v4'}},
        'relation': {'type': 'episodic', 'prop': {'k5': 'v5'}}, 'object': {'name': 'zxc', 'type': 'episodic', 'prop': {'k5': 'v5'}}}.

        :param json_triplet: Триплет в json-формате.
        :type json_triplet: Dict
        :return: Триплет в dataclass-формате.
        :rtype: Triplet
        """

        subject = NodeCreator.create(
            name=json_triplet['subject']['name'],
            n_type=json_triplet['subject']['type'],
            prop=json_triplet['subject'].get('prop', None))
        relation = RelationCreator.create(
            name=json_triplet['relation'].get('name', None),
            r_type=json_triplet['relation']['type'],
            prop=json_triplet['relation'].get('prop', None))
        object = NodeCreator.create(
            name=json_triplet['object']['name'],
            n_type=json_triplet['object']['type'],
            prop=json_triplet['object'].get('prop', None))

        converted_triplet = TripletCreator.create(start_node=subject, relation=relation, end_node=object)
        return converted_triplet

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
