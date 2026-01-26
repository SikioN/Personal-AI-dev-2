from typing import Dict, List
from dataclasses import dataclass
from abc import abstractmethod
from enum import Enum

from ..utils import AbstractDatabaseConnection, BaseDatabaseConfig

class TreeNodeType(Enum):
    """_summary_
    """
    #
    leaf = "leaf"
    #
    root = "root"
    #
    summarized = "summarized"

TREENODES_TYPES_MAP = {
    'leaf': TreeNodeType.leaf,
    'root': TreeNodeType.root,
    'summarized': TreeNodeType.summarized
}


class TreeIdType(Enum):
    """_summary_
    """
    #
    external = "external_id"
    #
    str = "str_id"

@dataclass
class TreeNode:
    """_summary_
    """
    #
    id: str
    #
    text: str
    #
    type: TreeNodeType
    #
    props: Dict[str, object]

@dataclass
class TreeDBConnectionConfig(BaseDatabaseConfig):
    host: str = None
    port: str = None

class AbstractTreeDatabaseConnection(AbstractDatabaseConnection):

    root_node_id: str = "ROOT_NODE_ID"

    @abstractmethod
    def open_connection(self) -> None:
        """_summary_
        """
        pass

    @abstractmethod
    def is_open(self) -> bool:
        """_summary_

        :return: _description_
        :rtype: bool
        """
        pass

    @abstractmethod
    def close_connection(self) -> None:
        """_summary_
        """
        pass

    @abstractmethod
    def check_consistency(self) -> None:
        """_summary_
        """
        pass

    @abstractmethod
    def create(self, parent_id: str, new_node: TreeNode) -> None:
        """_summary_

        :param parent_id: _description_
        :type parent_id: str
        :param new_node: _description_
        :type new_node: TreeNode
        """
        pass

    @abstractmethod
    def read(self, ids: List[str], ids_type: TreeIdType = TreeIdType.external) -> List[TreeNode]:
        """_summary_

        :param ids: _description_
        :type ids: List[str]
        :param ids_type: _description_, defaults to TreeIdType.external
        :type ids_type: TreeIdType, optional
        :return: _description_
        :rtype: List[TreeNode]
        """
        pass

    @abstractmethod
    def update(self, items: List[TreeNode]) -> None:
        """_summary_

        :param items: _description_
        :type items: List[TreeNode]
        """
        pass

    @abstractmethod
    def delete(self, ids: List[str], ids_type: TreeIdType = TreeIdType.external) -> None:
        """_summary_

        :param ids: _description_
        :type ids: List[str]
        :param ids_type: _description_, defaults to TreeIdType.external
        :type ids_type: TreeIdType, optional
        """
        pass

    @abstractmethod
    def get_leaf_descendants(self, id: str, id_type: str=TreeIdType.external) -> List[TreeNode]:
        """_summary_

        :param id: _description_
        :type id: str
        :param id_type: _description_, defaults to TreeIdType.external
        :type id_type: str, optional
        :return: _description_
        :rtype: List[TreeNode]
        """
        pass

    @abstractmethod
    def item_exist(self, id: str, id_type: str = TreeIdType.external) -> bool:
        """_summary_

        :param id: _description_
        :type id: str
        :param id_type: _description_, defaults to TreeIdType.external
        :type id_type: str, optional
        :return: _description_
        :rtype: bool
        """
        pass

    @abstractmethod
    def count_items(self) -> Dict[str, int]:
        """_summary_

        :return: _description_
        :rtype: Dict[str, int]
        """
        pass

    @abstractmethod
    def get_child_nodes(self, parent_id: str) -> List[TreeNode]:
        """_summary_

        :param parent_id: _description_
        :type parent_id: str
        :return: _description_
        :rtype: List[TreeNode]
        """
        pass

    @abstractmethod
    def get_tree_maxdepth(self) -> int:
        """_summary_

        :return: _description_
        :rtype: int
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """_summary_
        """
        pass
