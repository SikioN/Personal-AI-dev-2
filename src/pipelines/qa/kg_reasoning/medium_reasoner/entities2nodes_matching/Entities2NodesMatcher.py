from dataclasses import dataclass, field
from typing import Tuple, Union, List, Dict

from .config import E2NMATCHER_MAIN_LOG_PATH
from ......kg_model import KnowledgeGraphModel
from ......utils import ReturnInfo, Logger
from ......utils.errors import ReturnStatus
from ......utils.data_structs import create_id, NodeType
from ......db_drivers.vector_driver import VectorDBInstance


@dataclass
class Entities2NodesMatcherConfig:
    use_tree: bool = False
    distance_threshold: float = 0.4
    max_n: int = 3
    fetch_k: int = 50

    log: Logger = field(default_factory=lambda: Logger(E2NMATCHER_MAIN_LOG_PATH))
    verbose: bool = False

    def to_str(self):
        return f"{self.use_tree}|{self.distance_threshold}|{self.max_n}|{self.fetch_k}"


class Entities2NodesMatcher:
    def __init__(self, kg_model: KnowledgeGraphModel,
                 config: Entities2NodesMatcherConfig = Entities2NodesMatcherConfig(),
                 cache_kvdriver_config=None):
        self.config = config
        self.kg_model = kg_model
        self.log = self.config.log
        self.verbose = self.config.verbose

    def match_entitie2knowledge(self, entitie: str, use_tree: bool = False,
                                distance_threshold: float = 0.4,
                                max_n: int = 3, fetch_k: int = 50) -> List[VectorDBInstance]:
        if use_tree:
            matched_objects = self.kg_model.nodestree_struct.match_entitie2objects(
                entitie, distance_threshold=distance_threshold, fetch_k=fetch_k, max_n=max_n)
        else:
            entitie_embedding = self.kg_model.embeddings_struct.embedder.encode_queries([entitie])[0]
            entitie_vinstance = VectorDBInstance(embedding=entitie_embedding)

            raw_scored_nodes = self.kg_model.embeddings_struct.vectordbs['nodes'].retrieve(
                query_instances=[entitie_vinstance], n_results=fetch_k, includes=['documents'])[0]
            filtered_nodes = list(filter(lambda pair: pair[0] <= distance_threshold, raw_scored_nodes))

            object_nodes = list(filter(
                lambda pair: self.kg_model.graph_struct.db_conn.get_node_type(pair[1].id) == NodeType.object,
                filtered_nodes))
            matched_objects = list(map(
                lambda pair: pair[1],
                sorted(object_nodes, key=lambda p: p[0], reverse=False)))[:max_n]

        return matched_objects

    def perform(self, entities: List[str]) -> Tuple[Dict[str, List[VectorDBInstance]], ReturnInfo]:
        self.log("START ENTITIES2NODES MATCHING...", verbose=self.config.verbose)
        info = ReturnInfo()
        self.log(f"ENTITIES: {entities}", verbose=self.config.verbose)
        if len(entities) < 1:
            raise ValueError

        matched_kg_objects = dict()
        for i, entitie in enumerate(entities):
            self.log(f"Entity #{i}: {entitie}", verbose=self.verbose)
            matched_kg_objects[entitie] = self.match_entitie2knowledge(
                entitie, use_tree=self.config.use_tree,
                distance_threshold=self.config.distance_threshold,
                max_n=self.config.max_n, fetch_k=self.config.fetch_k)
            str_matched = ', '.join(list(map(lambda obj: obj.document, matched_kg_objects[entitie])))
            self.log(f"RESULT: {str_matched}", verbose=self.verbose)

        m_objects_amount = sum(len(v) for v in matched_kg_objects.values())
        if m_objects_amount < 1:
            info.status = ReturnStatus.empty_answer
        self.log(f"STATUS: {info.status}", verbose=self.verbose)

        return matched_kg_objects, info
