from typing import Dict, List, Union
from dataclasses import dataclass
from abc import abstractmethod

from ...utils import ReturnInfo
from ...utils.data_structs import Quadruplet, NodeType, RelationType, Node
from ..utils import AbstractDatabaseConnection, BaseDatabaseConfig

@dataclass
class GraphDBConnectionConfig(BaseDatabaseConfig):
    host: str = None
    port: str = None

class AbstractGraphDatabaseConnection(AbstractDatabaseConnection):

    @abstractmethod
    def create(self, quadruplets: List[Quadruplet], creation_info: Dict = dict()) -> ReturnInfo:
        pass

    @abstractmethod
    def get_adjecent_nids(self, base_node_id: str, accepted_n_types: List[NodeType] = [NodeType.object, NodeType.hyper, NodeType.episodic]) -> List[str]:
        pass

    @abstractmethod
    def get_nodes_shared_ids(self, node1_id: str, node2_id: str, id_type: str = 'both') -> List[Dict[str,str]]:
        pass

    @abstractmethod
    def get_quadruplets_by_name(self, subj_name: str, obj_name: str, obj_type) -> List[Quadruplet]:
        pass

    @abstractmethod
    def get_quadruplets(self, node1_id: str, node2_id: str) -> List[Quadruplet]:
        pass

    @abstractmethod
    def read_by_name(self, name: str, object_type: Union[RelationType,NodeType],
                     object: str = 'quadruplet') -> List[Union[Quadruplet, Node]]:
        pass

    @abstractmethod
    def get_node_type(self, id: str) -> NodeType:
        pass

    @abstractmethod
    def count_items(self, id: str = None, id_type: str = None) -> Union[Dict[str,int],int]:
        pass

    @abstractmethod
    def item_exist(self, id: str, id_type: str='quadruplet') -> bool:
        pass
