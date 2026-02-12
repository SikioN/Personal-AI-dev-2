import copy
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple, Union

from .utils import AbstractQuadrupletsRetriever, BaseGraphSearchConfig

from ......kg_model import KnowledgeGraphModel
from ......utils.data_structs import QueryInfo, QuadrupletCreator, create_id, Quadruplet, NodeCreator, RelationCreator, NodeType, RelationType, NODES_TYPES_MAP
from ......utils import Logger
from ......utils.cache_kv import CacheKV
from ......db_drivers.kv_driver import KeyValueDriverConfig

@dataclass
class WaterCirclesSearchConfig(BaseGraphSearchConfig):
    """Configuration for Water Circles retrieval algorithm."""
    strict_filter: bool = True
    hyper_num: int = 15
    episodic_num: int = 15
    chain_quadruplets_num: int = 25 # Renamed from chain_triplets_num
    other_quadruplets_num: int = 6  # Renamed from other_triplets_num
    do_text_pruning: bool = False
    cache_table_name: str = 'qa_watercircles_q_retriever_cache'
    accepted_node_types: List[NodeType] = field(default_factory=lambda:[NodeType.object, NodeType.hyper, NodeType.episodic, NodeType.time])

    def to_str(self):
        str_accepted_nodes = ";".join(sorted(list(map(lambda v: v.value, self.accepted_node_types))))
        str_values = f"{self.hyper_num};{self.episodic_num};{self.chain_quadruplets_num};{self.other_quadruplets_num}"
        return f"{self.strict_filter}|{str_values}|{self.do_text_pruning}|{str_accepted_nodes}"

def process_chain(
        chain: List[List[str]],
        chain_subj_obj: List[Tuple[str]],
        chain_quadruplets: List[List[str]]
    ) -> Tuple[List[Tuple[str]], List[List[str]]]:
    """
    Process chains to extract unique subject-object-relation combinations.
    """
    for quadruplet in chain:
        subj = quadruplet[0]
        subj_no_props = {key: value for key, value in subj.items() if key != "prop"}
        subj_props = subj["prop"]
        subj = list(subj_no_props.items()) + list(subj_props.items())
        subj = [(key, str(value)) for key, value in subj]
        subj = sorted(subj, key=lambda x: str(x[1]))
        
        obj = quadruplet[2]
        obj_no_props = {key: value for key, value in obj.items() if key != "prop"}
        obj_props = obj["prop"]
        obj = list(obj_no_props.items()) + list(obj_props.items())
        obj = [(key, str(value)) for key, value in obj]
        obj = sorted(obj, key=lambda x: x[1])
        
        subj = str(subj)
        obj = str(obj)
        
        rel_props = quadruplet[1]["prop"].items()
        # IMPORTANT: Removing the exclusion of "time" here. In a temporal KG, time distinguishes facts.
        # rel_props = [(key, value) for key, value in rel_props if key not in ["raw_time", "time"]]
        rel_props = sorted(list(rel_props), key=lambda x: x[0])
        rel_props = str(rel_props)
        
        if (subj, obj, rel_props) not in chain_subj_obj and (obj, subj, rel_props) not in chain_subj_obj \
                and quadruplet not in chain_quadruplets:
            chain_quadruplets.append(quadruplet)
            chain_subj_obj.add((subj, obj, rel_props))
    return chain_subj_obj, chain_quadruplets


def process_inters_chains1(inters_chains1: List[List[List[str]]]) -> List[List[str]]:
    chain_quadruplets1 = []
    chain_subj_obj1 = set()
    for chain in inters_chains1:
        chain_subj_obj1, chain_quadruplets1 = process_chain(chain, chain_subj_obj1, chain_quadruplets1)
    return chain_quadruplets1


def process_inters_chains2(inters_chains2: List[List[List[str]]]) -> List[List[str]]:
    chain_quadruplets2 = []
    chain_subj_obj2 = set()
    for chain1, chain2, *_ in inters_chains2:
        chain_subj_obj2, chain_quadruplets2 = process_chain(chain1, chain_subj_obj2, chain_quadruplets2)
        chain_subj_obj2, chain_quadruplets2 = process_chain(chain2, chain_subj_obj2, chain_quadruplets2)
    return chain_quadruplets2


class WaterCirclesQuadrupletsRetriever(AbstractQuadrupletsRetriever):
    """BFS-based retrieval algorithm ('Water Circles') adapted for Quadruplets."""

    def __init__(self,kg_model: KnowledgeGraphModel,
                 log: Logger, search_config: Union[WaterCirclesSearchConfig, Dict] = WaterCirclesSearchConfig(),
                 cache_kvdriver_config: KeyValueDriverConfig = None, verbose: bool = False) -> None:
        self.log = log
        self.verbose = verbose
        self.kg_model = kg_model

        if type(search_config) is dict:
            if 'accepted_node_types' in search_config:
                search_config['accepted_node_types'] = list(map(lambda k: NODES_TYPES_MAP[k], search_config['accepted_node_types']))
            search_config = WaterCirclesSearchConfig(**search_config)
        self.config = search_config

        self.extract_quadruplets_name1_template = \
            'MATCH (a:object)-[r]-(b:object) WHERE a.name="{name1}" RETURN a, r, b'
        self.extract_quadruplets_name2_template = \
            'MATCH (a:object)-[r]-(b:object) WHERE b.name="{name2}" RETURN a, r, b'
        self.extract_quadruplets_rel_prop_template = \
            'MATCH (a:object)-[r]-(b:object) WHERE r.{prop_name}="{prop_value}" RETURN a, r, b'

        if cache_kvdriver_config is not None and self.config.cache_table_name is not None:
            cache_config = deepcopy(cache_kvdriver_config)
            cache_config.db_config.db_info['table'] = self.config.cache_table_name
            self.cachekv = CacheKV(cache_config)
        else:
            self.cachekv = None

    def get_cache_key(self, query_info: QueryInfo, depth: int = 1):
        return [self.config.to_str(), query_info.to_str(), str(depth)]

    def parse_quadruplet_output(
            self,
            direction: str,
            query: List[Union[list, str]],
            another_entities1: List[str],
            another_entities2: Dict[str, List[List[str]]],
            chain: List[List[str]]
        ) -> Tuple[Tuple[List[dict], List[Tuple[str]], List[List[dict]]], List[List[List[str]]], List[List[List[str]]]]:
        
        quadruplets_info = []
        inters_chains1, inters_chains2 = [], []
        try:
            subj_name, obj_name, obj_type = query
            # Updated method call
            res = self.kg_model.graph_struct.db_conn.get_quadruplets_by_name(subj_name, obj_name, obj_type)
            for quadruplet_raw in res:
                # Convert Quadruplet object to dictionary format for processing
                quadruplet = [{"id": quadruplet_raw.start_node.id,
                            "type": quadruplet_raw.start_node.type,
                            "name": quadruplet_raw.start_node.name.replace("_", " "),
                            "prop": quadruplet_raw.start_node.prop},
                           {"id": quadruplet_raw.relation.id,
                            "type": quadruplet_raw.relation.type,
                            "name": quadruplet_raw.relation.name,
                            "prop": quadruplet_raw.relation.prop},
                           {"id": quadruplet_raw.end_node.id,
                            "type": quadruplet_raw.end_node.type,
                            "name": quadruplet_raw.end_node.name.replace("_", " "),
                            "prop": quadruplet_raw.end_node.prop},
                            direction]
                
                # Add Time Node info if available?
                # The 'quadruplet' list structure [subj, rel, obj, dir] assumes 3 main components + meta.
                # Time is likely implicitly in 'rel.prop' (where we store t_id / time_node_id).
                # We can keep this structure as 'process_chain' expects it.

                new_chain = copy.deepcopy(chain)

                def count_persons(new_chain, second_chain):
                    persons  = set()
                    for cur_chain in [new_chain, second_chain]:
                        for tr in cur_chain:
                            for ent in tr:
                                if "person" in ent:
                                    persons.add(ent["person"])
                    return persons

                if quadruplet not in new_chain:
                    subj = quadruplet[0]["name"].replace("_", " ")
                    obj = quadruplet[-2]["name"].replace("_", " ")
                    prop_values = [val.lower() for val in quadruplet[1]["prop"].values() if isinstance(val, str)] # Safety check
                    cnt1 = 0
                    if subj.lower() in another_entities1:
                        cnt1 += 1
                    if obj.lower() in another_entities1:
                        cnt1 += 1
                    if any([prop_value.lower() in another_entities1 for prop_value in prop_values]):
                        cnt1 += 1

                    if cnt1 > 0:
                        new_chain.append(quadruplet)
                        inters_chains1.append([new_chain, cnt1])
                    elif "backw" in direction and subj.lower() in another_entities2:
                        new_chain.append(quadruplet)
                        second_chain = another_entities2[subj.lower()]
                        persons = count_persons(new_chain, second_chain)
                        if not ([ch[-1] for ch in new_chain] == ["forw", "backw"] \
                                and [ch[-1] for ch in second_chain] == ["forw", "backw"]) and len(persons) < 3:
                            inters_chains2.append([new_chain, second_chain, ["backw", subj]])
                    elif "forw" in direction and obj.lower() in another_entities2:
                        new_chain.append(quadruplet)
                        second_chain = another_entities2[obj.lower()]
                        persons = count_persons(new_chain, second_chain)
                        if not ([ch[-1] for ch in new_chain] == ["forw", "backw"] \
                                and [ch[-1] for ch in second_chain] == ["forw", "backw"]) and len(persons) < 3:
                            inters_chains2.append([new_chain, second_chain, ["forw", obj]])
                    elif any([prop_value.lower() in another_entities2 for prop_value in prop_values]):
                        for prop_value in quadruplet[1]["prop"].values():
                            if isinstance(prop_value, str) and prop_value.lower() in another_entities2:
                                new_chain.append(quadruplet)
                                second_chain = another_entities2[prop_value.lower()]
                                persons = count_persons(new_chain, second_chain)
                                if len(persons) < 3:
                                    inters_chains2.append([new_chain, second_chain, ["prop", prop_value]])
                    else:
                        new_chain.append(quadruplet)
                else:
                    new_chain.append(quadruplet)
                new_entities = []
                if "forw" in direction:
                    new_entities.append((quadruplet_raw.end_node.name, "", "node"))
                if "backw" in direction:
                    new_entities.append((quadruplet_raw.start_node.name, "", "node"))
                quadruplets_info.append([quadruplet, new_entities, new_chain])
        except Exception as e:
            print(f"error in query execution: {e}")
        return quadruplets_info, inters_chains1, inters_chains2

    def add_chains(
            self,
            inters_chains1: List[List[List[str]]],
            inters_chains2: List[List[List[str]]],
            cur_inters_chains1: List[List[List[str]]],
            cur_inters_chains2: List[List[List[str]]]
        ) -> Tuple[List[List[List[str]]], List[List[List[str]]]]:
        
        for ch in cur_inters_chains1:
            if ch not in inters_chains1:
                inters_chains1.append(ch)
        for ch in cur_inters_chains2:
            if ch not in inters_chains2:
                inters_chains2.append(ch)
        return inters_chains1, inters_chains2

    def make_quadruplet_key(self, quadruplet: List[Dict[str, str]]) -> Tuple[Tuple[str], Tuple[str]]:
        subj, rel, obj, *_ = quadruplet
        rel_data_items = list(rel["prop"].items())
        rel_data_items = [(key.replace("_", " "), str(value).replace("_", " ")) for key, value in rel_data_items
                          if key not in ["sentiment"]] # Keeping time in key logic if present
        rel_data_items = sorted(rel_data_items, key=lambda x: x[0])
        rel_data_values = [element[1].lower().replace("_", " ") for element in rel_data_items]
        subj_name = [subj["name"].replace("_", " ")]
        obj_name = [obj["name"].replace("_", " ")]
        rel_type = rel["type"].replace("_", " ")
        keys = [subj_name, rel_type, obj_name] + rel_data_values
        keys_rev = [obj_name, rel_type, subj_name] + rel_data_values
        return tuple(keys), tuple(keys_rev)

    def get_relevant_quadruplets(self, query_info: QueryInfo, depth: int = 1) -> List[Quadruplet]:
        self.log("START KNOWLEDGE RETRIEVING ...", verbose=self.verbose)
        self.log("RETRIEVER: WaterCirclesQuadrupletsRetriever", verbose=self.verbose)
        self.log(f"BASE_QUESTION ID: {create_id(query_info.query)}", verbose=self.verbose)
        self.log(f"BASE_QUESTION: {query_info.query}", verbose=self.verbose)
        seed_entities = []
        if hasattr(query_info, "entities_with_types"):
            entities_with_types = query_info.entities_with_types
            entity_types = list(entities_with_types.values())
            same_types = len(entity_types) > 1 and all([entity_type == entity_types[0]
                                                        for entity_type in entity_types])
        else:
            same_types = False

        for nodes_list in query_info.linked_nodes_by_entities:
            seed_entity = []
            for node in nodes_list:
                if isinstance(node, str):
                    seed_entity.append((node, "", "node"))
                else:
                    seed_entity.append((node.document, "", "node"))
            seed_entities.append(seed_entity)

        quadruplets_dict, inters_chains1, inters_chains2 = self.bfs(seed_entities, depth)
        output_texts_hyper, output_texts_episodic = self.extract_thesis(seed_entities, same_types)

        thres = self.config.chain_quadruplets_num
        if len(inters_chains1) == 1:
            thres = self.config.chain_quadruplets_num
        elif len(inters_chains1) == 2:
            thres = int(self.config.chain_quadruplets_num * 0.5)
        elif len(inters_chains1) >= 3:
            thres = int(self.config.chain_quadruplets_num * 0.3)

        chain_quadruplets = []
        for seed_entity in inters_chains1:
            ent_chain_quadruplets = []
            ent_inters_chains1 = inters_chains1[seed_entity]
            ent_inters_chains2 = inters_chains2[seed_entity]
            ent_inters_chains1 = sorted(ent_inters_chains1, key=lambda x: x[1], reverse=True)

            inters_chains1_more = [ch for ch, cnt in ent_inters_chains1 if cnt > 1]
            inters_chains1_less = [ch for ch, cnt in ent_inters_chains1 if cnt == 1]
            chain_quadruplets1_more = process_inters_chains1(inters_chains1_more)
            chain_quadruplets1_less = process_inters_chains1(inters_chains1_less)

            chain_quadruplets2 = process_inters_chains2(ent_inters_chains2)
            prob_tr = False
            if self.config.strict_filter:
                if inters_chains1_more:
                    ent_chain_quadruplets = chain_quadruplets1_more
                    prob_tr = True
                else:
                    ent_chain_quadruplets = chain_quadruplets1_less + chain_quadruplets2
                if not ent_chain_quadruplets:
                    ent_chain_quadruplets = chain_quadruplets1_more + chain_quadruplets1_less + chain_quadruplets2
            else:
                ent_chain_quadruplets = chain_quadruplets1_more + chain_quadruplets1_less + chain_quadruplets2
            chain_quadruplets += ent_chain_quadruplets[:thres]

        def format_quadruplet(quadruplet_data):
            subj, rel, obj, *_ = quadruplet_data
            subj_node = NodeCreator.create(name=subj["name"], n_type=subj["type"], prop=subj["prop"])
            subj_node.id = subj['id']

            obj_node = NodeCreator.create(name=obj["name"], n_type=obj["type"], prop=obj["prop"])
            obj_node.id = obj['id']

            rel_edge = RelationCreator.create(name=rel.get("name", None), r_type=rel["type"], prop=rel["prop"])
            rel_edge.id=rel["id"]

            # Try to recover time info. 
            # In parse_quadruplet_output we put prop dict in rel.
            # Neo4jConnector stores time_node_id in prop.
            time_node_id = rel['prop'].get('time_node_id')
            time_node = None
            if time_node_id:
                # Placeholder as we don't have the full Time Node object here without fetching it
                # But QuadrupletCreator can handle a generic Time node if ID is present?
                # Actually, strictly speaking we should fetch it, but let's default to "Always" if missing
                # or create a dummy TimeNode with just ID if possible?
                # DataStructs implementation: QuadrupletCreator doesn't fetch.
                # Let's create a partial TimeNode.
                time_node = NodeCreator.create(NodeType.time, "Unknown_Time", add_stringified_node=False)
                time_node.id = time_node_id
            
            if not time_node: # Default
                 time_node = NodeCreator.create(NodeType.time, "Always", add_stringified_node=False)

            quadruplet = QuadrupletCreator.create(
                start_node=subj_node,
                relation=rel_edge,
                end_node=obj_node,
                time=time_node, # MANDATORY now
                add_stringified_quadruplet=False
            )
            return quadruplet

        def quadruplet_from_hyper(text, seed_entity, subj_props, obj_props, rel_props, rel_id):
            subj_node = NodeCreator.create(name=seed_entity, n_type=NodeType.object, prop=subj_props)
            subj_node.id = '1'

            obj_node = NodeCreator.create(name=text, n_type=NodeType.hyper, prop=obj_props)
            obj_node.id = '1'

            rel_edge = RelationCreator.create(r_type=RelationType.hyper, prop=rel_props)
            rel_edge.id=rel_id
            
            # Default time for hyper/episodic texts? Likely "Always" unless specified
            time_node = NodeCreator.create(NodeType.time, "Always", add_stringified_node=False)

            quadruplet = QuadrupletCreator.create(
                start_node=subj_node,
                relation=rel_edge,
                end_node=obj_node,
                time=time_node,
                add_stringified_quadruplet=False
            )
            return quadruplet

        ex_quadruplets = []
        formatted_quadruplets = []
        for text, seed_entity, subj_props, obj_props, rel_props, rel_id in output_texts_hyper:
            quadruplet = quadruplet_from_hyper(text, seed_entity, subj_props, obj_props, rel_props, rel_id)
            formatted_quadruplets.append(quadruplet)
        for text, seed_entity, subj_props, obj_props, rel_props, rel_id in output_texts_episodic:
            quadruplet = quadruplet_from_hyper(text, seed_entity, subj_props, obj_props, rel_props, rel_id)
            formatted_quadruplets.append(quadruplet)

        len_he = len(formatted_quadruplets)
        for quadruplet_data in chain_quadruplets:
            subj, rel, obj, *_ = quadruplet_data
            # We must include rel in uniqueness check because different relations between same S-O matter
            if (subj, rel, obj) not in ex_quadruplets and (obj, rel, subj) not in ex_quadruplets:
                formatted_quadruplet = format_quadruplet(quadruplet_data)
                formatted_quadruplets.append(formatted_quadruplet)
                ex_quadruplets.append((subj, rel, obj))

        if self.config.strict_filter:
            if chain_quadruplets:
                thres = int(self.config.other_quadruplets_num * 0.5)
            else:
                thres = self.config.other_quadruplets_num
        else:
            thres = int(self.config.other_quadruplets_num * 1.5)

        len_he = len(output_texts_hyper) + len(output_texts_episodic)
        if (not chain_quadruplets and not prob_tr and len_he < 2) \
                or (not self.config.strict_filter and len(chain_quadruplets) + len_he < 20):
            total_f_quadruplets = []
            for (*_, seed_entity, _), quadruplets in quadruplets_dict.items():
                f_quadruplets = []
                for quadruplet in quadruplets:
                    reverse_quadruplet = [quadruplet[-1]] + quadruplet[1:-1] + [quadruplet[0]]
                    if quadruplet not in total_f_quadruplets and reverse_quadruplet not in total_f_quadruplets:
                        f_quadruplets.append(quadruplet)
                        total_f_quadruplets.append(quadruplet)
                for quadruplet in f_quadruplets[:thres]:
                    formatted_quadruplet = format_quadruplet(quadruplet)
                    formatted_quadruplets.append(formatted_quadruplet)
        return formatted_quadruplets

    def extract_thesis_for_entities(
            self,
            seed_entities: List[List[Tuple[str]]],
            entities_list: List[Tuple[str]],
            entity_type: str,
            texts_set: Set[str]
        ) -> Tuple[List[Tuple[str, str, Dict[str, str], Dict[str, str], int, str]], Set[str]]:
        
        cur_texts = []
        for seed_entity, *_ in entities_list:
            another_entities_list = [entities_list2 for entities_list2 in seed_entities
                                        if entities_list2 != entities_list]
            res = self.kg_model.graph_struct.db_conn.get_quadruplets_by_name(
                [seed_entity, seed_entity.lower(), seed_entity.replace(" ", "_"), seed_entity.lower().replace(" ", "_")],
                [],
                entity_type
            )
            for element in res:
                subj_dict = element.start_node.prop
                obj_dict = element.end_node.prop
                rel_dict = element.relation.prop
                rel_id = element.relation.id
                text = element.end_node.name
                obj_props = {key: value for key, value in obj_dict.items() if key != "name"}
                if self.config.do_text_pruning:
                    text = text.strip()
                    text_chunks = text.split("\n")
                else:
                    text_chunks = [text]
                for text_chunk in text_chunks:
                    init_text_chunk = copy.deepcopy(text_chunk)
                    text_chunk = text_chunk.strip()
                    if text_chunk not in texts_set:
                        num_inters = 0
                        for entities_list2 in another_entities_list:
                            found = False
                            for ent, *_ in entities_list2:
                                if ent.lower() in text_chunk.lower() \
                                        or ent.lower() in obj_props.values() \
                                        or ent.lower() in rel_dict.values():
                                    found = True
                                else:
                                    words = ent.lower().split()
                                    words_no_end = []
                                    for word in words:
                                        if len(word) > 4:
                                            words_no_end.append(word[:-2])
                                        elif len(word) == 4:
                                            words_no_end.append(word[:-1])
                                        else:
                                            words_no_end.append(word)
                                    if all([word in text_chunk.lower() for word in words_no_end]):
                                        found = True
                            if found:
                                num_inters += 1
                        cur_texts.append([init_text_chunk, seed_entity, subj_dict, obj_props, rel_dict, num_inters, rel_id])
                        texts_set.add(text_chunk)
        return cur_texts, texts_set

    def extract_thesis(self, seed_entities: List[List[Tuple[str]]], same_types: bool) -> List[str]:
        output_texts = {"hyper": [], "episodic": []}
        retr_texts = {"hyper": {ne: [] for ne in range(len(seed_entities))},
                      "episodic": {ne: [] for ne in range(len(seed_entities))}
                      }
        texts_set = set()
        for ne, entities_list in enumerate(seed_entities):
            cur_texts1, texts_set = self.extract_thesis_for_entities(seed_entities, entities_list, "hyper", texts_set)
            cur_texts2, texts_set = self.extract_thesis_for_entities(seed_entities, entities_list, "episodic", texts_set)
            retr_texts["hyper"][ne] = cur_texts1
            retr_texts["episodic"][ne] = cur_texts2

        for tr_type in ["hyper", "episodic"]:
            for key in retr_texts[tr_type]:
                retr_texts[tr_type][key] = sorted(retr_texts[tr_type][key], key=lambda x: x[-2], reverse=True)

        thres = {}
        if self.config.strict_filter:
            if len(seed_entities) == 1:
                thres["hyper"] = self.config.hyper_num
                thres["episodic"] = self.config.episodic_num
            elif len(seed_entities) == 2:
                thres["hyper"] = int(0.67 * self.config.hyper_num)
                thres["episodic"] = int(0.67 * self.config.episodic_num)
            else:
                thres["hyper"] = int(0.5 * self.config.hyper_num)
                thres["episodic"] = int(0.67 * self.config.episodic_num)
        else:
            thres["hyper"] = int(0.67 * self.config.hyper_num)
            thres["episodic"] = int(0.67 * self.config.episodic_num)

        for tr_type in ["hyper", "episodic"]:
            if same_types:
                for key in retr_texts[tr_type]:
                    cur_texts = [[text, seed_entity, subj_props, obj_props, rel_props, e_id]
                                for text, seed_entity, subj_props, obj_props, rel_props, _, e_id in retr_texts[tr_type][key]]
                    output_texts[tr_type] += cur_texts[:thres[tr_type]]
            else:
                for key in retr_texts[tr_type]:
                    cur_texts = [[text, seed_entity, subj_props, obj_props, rel_props, e_id]
                                for text, seed_entity, subj_props, obj_props, rel_props, cnt, e_id in retr_texts[tr_type][key]
                                if cnt > 0]
                    output_texts[tr_type] += cur_texts[:thres[tr_type]]
                if not output_texts[tr_type]:
                    for key in retr_texts[tr_type]:
                        cur_texts = [[text, seed_entity, subj_props, obj_props, rel_props, e_id]
                                    for text, seed_entity, subj_props, obj_props, rel_props, _, e_id in retr_texts[tr_type][key]]
                        output_texts[tr_type] += cur_texts[:thres[tr_type]]
        return output_texts["hyper"], output_texts["episodic"]

    def bfs(
            self,
            seed_entities: List[List[Tuple[str]]],
            depth: int = 1,
            subj_labels: List[str] = None,
            obj_labels: List[str] = None,
            use_rel_props: bool = False
        ) -> Tuple[Dict[tuple, Tuple[List[dict], List[Tuple[str]], List[List[dict]]]],
                   List[List[List[str]]],
                   List[List[List[str]]]]:
        
        quadruplets_dict = {}
        inters_chains1, inters_chains2 = {}, {}
        used_entities = {}
        entities = {}
        for step in range(depth):
            for ne, entities_list in enumerate(seed_entities):
                for seed_entity, prop_name, entity_type in entities_list:
                    ent_inters_chains1, ent_inters_chains2 = [], []
                    another_entities_list = [entities_list2 for entities_list2 in seed_entities
                                            if entities_list2 != entities_list]
                    another_entities1, another_entities2 = [], {}
                    for entities_list2 in another_entities_list:
                        for ent, *_ in entities_list2:
                            another_entities1.append(ent.lower())

                    seed_entity = seed_entity.lower()
                    if step == 0:
                        used_entities[(seed_entity, ne)] = set()
                        entities[(seed_entity, ne)] = [(seed_entity, prop_name, entity_type, [])]
                    for (cur_seed_entity, cur_ne), entities_info in entities.items():
                        if cur_ne != ne:
                            for entity, *_, chain in entities_info:
                                if entity.lower() != cur_seed_entity.lower() and entity.lower() != seed_entity.lower() \
                                        and entity not in another_entities1 and entity not in another_entities2:
                                    another_entities2[entity.lower()] = chain
                    quadruplets_info = []
                    new_entities = []
                    for entity, prop_name, tp, chain in entities[(seed_entity, ne)]:
                        if (entity, prop_name, tp) not in used_entities[(seed_entity, ne)]:
                            if tp == "node":
                                cur_quadruplets_info, cur_inters_chains1, cur_inters_chains2 = self.parse_quadruplet_output(
                                    "forw",
                                    [[entity, entity.replace(" ", "_")], [], "object"],
                                    another_entities1,
                                    another_entities2,
                                    chain
                                )
                                ent_inters_chains1, ent_inters_chains2 = \
                                    self.add_chains(ent_inters_chains1, ent_inters_chains2, cur_inters_chains1, cur_inters_chains2)
                                for quadruplet in cur_quadruplets_info:
                                    quadruplets_info.append([(step, "forw", seed_entity, quadruplet[0][1]["type"])] + quadruplet)
                                cur_quadruplets_info, cur_inters_chains1, cur_inters_chains2 = self.parse_quadruplet_output(
                                    "backw",
                                    [[], [entity, entity.replace(" ", "_")], "object"],
                                    another_entities1,
                                    another_entities2,
                                    chain
                                )
                                ent_inters_chains1, ent_inters_chains2 = \
                                    self.add_chains(ent_inters_chains1, ent_inters_chains2, cur_inters_chains1, cur_inters_chains2)
                                for quadruplet in cur_quadruplets_info:
                                    quadruplets_info.append([(step, "backw", seed_entity, quadruplet[0][1]["type"])] + quadruplet)
                                used_entities[(seed_entity, ne)].add((entity, prop_name, tp))
                            elif tp == "rel_prop" and use_rel_props:
                                query = self.extract_quadruplets_rel_prop_template.format(
                                    prop_name=prop_name,
                                    prop_value=entity.capitalize()
                                )
                                cur_quadruplets_info, cur_inters_chains1, cur_inters_chains2 = self.parse_quadruplet_output(
                                    "forw/backw", query, another_entities1, another_entities2, chain, subj_labels, obj_labels
                                )
                                ent_inters_chains1, ent_inters_chains2 = \
                                    self.add_chains(ent_inters_chains1, ent_inters_chains2, cur_inters_chains1, cur_inters_chains2)
                                for quadruplet in cur_quadruplets_info:
                                    quadruplets_info.append([(step, "forw", seed_entity, quadruplet[0][1]["type"])] + quadruplet)
                                used_entities[(seed_entity, ne)].add((entity, prop_name, tp))

                    for step_dir_seed_rel, quadruplet, cur_entities, new_chain in quadruplets_info:
                        for (cur_ent, cur_prop_name, cur_prop_type) in cur_entities:
                            if (cur_ent, cur_prop_name, cur_prop_type, new_chain) not in new_entities:
                                new_entities.append((cur_ent, cur_prop_name, cur_prop_type, new_chain))
                        if step_dir_seed_rel not in quadruplets_dict:
                            quadruplets_dict[step_dir_seed_rel] = []
                        quadruplets_dict[step_dir_seed_rel].append(quadruplet)
                    entities[(seed_entity, ne)] += new_entities

                    if seed_entity not in inters_chains1:
                        inters_chains1[seed_entity] = ent_inters_chains1
                    else:
                        inters_chains1[seed_entity] += ent_inters_chains1
                    if seed_entity not in inters_chains2:
                        inters_chains2[seed_entity] = ent_inters_chains2
                    else:
                        inters_chains2[seed_entity] += ent_inters_chains2
        return quadruplets_dict, inters_chains1, inters_chains2
