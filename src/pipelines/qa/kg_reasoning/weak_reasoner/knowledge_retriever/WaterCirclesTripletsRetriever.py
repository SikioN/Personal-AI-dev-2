import copy
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple, Union

from .utils import AbstractTripletsRetriever, BaseGraphSearchConfig

from ......kg_model import KnowledgeGraphModel
from ......utils.data_structs import QueryInfo, TripletCreator, create_id, Triplet, NodeCreator, RelationCreator, NodeType, RelationType, NODES_TYPES_MAP
from ......utils import Logger
from ......utils.cache_kv import CacheKV
from ......db_drivers.kv_driver import KeyValueDriverConfig

@dataclass
class WaterCirclesSearchConfig(BaseGraphSearchConfig):
    """_summary_
    """
    strict_filter: bool = True
    hyper_num: int = 15
    episodic_num: int = 15
    chain_triplets_num: int = 25
    other_triplets_num: int = 6
    do_text_pruning: bool = False
    cache_table_name: str = 'qa_watercircles_t_retriever_cache'
    accepted_node_types: List[NodeType] = field(default_factory=lambda:[NodeType.object, NodeType.hyper, NodeType.episodic, NodeType.time])

    def to_str(self):
        str_accepted_nodes = ";".join(sorted(list(map(lambda v: v.value, self.accepted_node_types))))
        str_values = f"{self.hyper_num};{self.episodic_num};{self.chain_triplets_num};{self.other_triplets_num}"
        return f"{self.strict_filter}|{str_values}|{self.do_text_pruning}|{str_accepted_nodes}"

def process_chain(
        chain: List[List[str]],
        chain_subj_obj: List[Tuple[str]],
        chain_triplets: List[List[str]]
    ) -> Tuple[List[Tuple[str]], List[List[str]]]:
    """_summary_

    :param chain: пути в графе, которые начинаются от сущностей из вопроса
    :type chain: List[List[str]]
    :param chain_subj_obj: список субъектов и объектов триплетов из путей в графе
    :type chain_subj_obj: List[Tuple[str]]
    :param chain_triplets: список триплетов из путей в графе
    :type chain_triplets: List[List[str]]
    :return: список субъектов и объектов триплетов из путей в графе, список триплетов из путей в графе
    :rtype: Tuple[List[Tuple[str]], List[List[str]]]
    """
    for triplet in chain:
        subj = triplet[0]
        subj_no_props = {key: value for key, value in subj.items() if key != "prop"}
        subj_props = subj["prop"]
        subj = list(subj_no_props.items()) + list(subj_props.items())
        subj = [(key, str(value)) for key, value in subj]
        subj = sorted(subj, key=lambda x: str(x[1]))
        obj = triplet[2]
        obj_no_props = {key: value for key, value in obj.items() if key != "prop"}
        obj_props = obj["prop"]
        obj = list(obj_no_props.items()) + list(obj_props.items())
        obj = [(key, str(value)) for key, value in obj]
        obj = sorted(obj, key=lambda x: x[1])
        subj = str(subj)
        obj = str(obj)
        rel_props = triplet[1]["prop"].items()
        rel_props = [(key, value) for key, value in rel_props if key not in ["raw_time", "time"]]
        rel_props = sorted(rel_props, key=lambda x: x[0])
        rel_props = str(rel_props)
        if (subj, obj, rel_props) not in chain_subj_obj and (obj, subj, rel_props) not in chain_subj_obj \
                and triplet not in chain_triplets:
            chain_triplets.append(triplet)
            chain_subj_obj.add((subj, obj, rel_props))
    return chain_subj_obj, chain_triplets


def process_inters_chains1(inters_chains1: List[List[List[str]]]) -> List[List[str]]:
    """_summary_

    :param inters_chains1: пути в графе, которые начинаются от сущностей из вопроса и пересекаются
    :type inters_chains1: List[List[List[str]]]
    :return: список триплетов из путей в графе
    :rtype: List[List[str]]
    """
    chain_triplets1 = []
    chain_subj_obj1 = set()
    for chain in inters_chains1:
        chain_subj_obj1, chain_triplets1 = process_chain(chain, chain_subj_obj1, chain_triplets1)
    return chain_triplets1


def process_inters_chains2(inters_chains2: List[List[List[str]]]) -> List[List[str]]:
    """_summary_

    :param inters_chains2: пути в графе, которые начинаются от сущностей из вопроса и пересекаются
    :type inters_chains3: List[List[List[str]]]
    :return: список триплетов из путей в графе
    :rtype: List[List[str]]
    """
    chain_triplets2 = []
    chain_subj_obj2 = set()
    for chain1, chain2, *_ in inters_chains2:
        chain_subj_obj2, chain_triplets2 = process_chain(chain1, chain_subj_obj2, chain_triplets2)
        chain_subj_obj2, chain_triplets2 = process_chain(chain2, chain_subj_obj2, chain_triplets2)
    return chain_triplets2


class WaterCirclesRetriever(AbstractTripletsRetriever):
    """Класс с реализацией алгоритма BFS (поиск в ширину) по графу

    :param kg_model: класс для извлечения триплетов из графа
    :type kg_model: KnowledgeGraphModel
    :param log: класс для логирования
    :type log: Logger
    :param search_config: конфигурация поиска по графу
    :type search_config: WaterCirclesSearchConfig, optional
    """

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

        self.extract_triplets_name1_template = \
            'MATCH (a:object)-[r]-(b:object) WHERE a.name="{name1}" RETURN a, r, b'
        self.extract_triplets_name2_template = \
            'MATCH (a:object)-[r]-(b:object) WHERE b.name="{name2}" RETURN a, r, b'
        self.extract_triplets_rel_prop_template = \
            'MATCH (a:object)-[r]-(b:object) WHERE r.{prop_name}="{prop_value}" RETURN a, r, b'

        if cache_kvdriver_config is not None and self.config.cache_table_name is not None:
            cache_config = deepcopy(cache_kvdriver_config)
            cache_config.db_config.db_info['table'] = self.config.cache_table_name
            self.cachekv = CacheKV(cache_config)
        else:
            self.cachekv = None

    def get_cache_key(self, query_info: QueryInfo, depth: int = 1):
        return [self.config.to_str(), query_info.to_str(), str(depth)]

    def parse_triplet_output(
            self,
            direction: str,
            query: List[Union[list, str]],
            another_entities1: List[str],
            another_entities2: Dict[str, List[List[str]]],
            chain: List[List[str]]
        ) -> Tuple[Tuple[List[dict], List[Tuple[str]], List[List[dict]]], List[List[List[str]]], List[List[List[str]]]]:
        """_summary_

        :param direction: направление поиска
        :type direction: str
        :param query: запрос для поиска
        :type query: List[Union[list, str]]
        :param another_entities1: сущности из вопроса
        :type another_entities1: List[str]
        :param another_entities2: сущности, найденные в процессе поиска
        :type another_entities2: Dict[str, List[List[str]]]
        :param chain: путь в графе
        :type chain: List[List[str]]
        :return: информация об извлеченных триплетах и пути в графе
        :rtype: Tuple[List[List[dict], List[Tuple[str]], List[List[dict]]], List[List[List[str]]], List[List[List[str]]]]
        """
        triplets_info = []
        inters_chains1, inters_chains2 = [], []
        try:
            subj_name, obj_name, obj_type = query
            res = self.kg_model.graph_struct.db_conn.get_triplets_by_name(subj_name, obj_name, obj_type)
            for triplet_raw in res:
                triplet = [{"id": triplet_raw.start_node.id,
                            "type": triplet_raw.start_node.type,
                            "name": triplet_raw.start_node.name.replace("_", " "),
                            "prop": triplet_raw.start_node.prop},
                           {"id": triplet_raw.relation.id,
                            "type": triplet_raw.relation.type,
                            "name": triplet_raw.relation.name,
                            "prop": triplet_raw.relation.prop},
                           {"id": triplet_raw.end_node.id,
                            "type": triplet_raw.end_node.type,
                            "name": triplet_raw.end_node.name.replace("_", " "),
                            "prop": triplet_raw.end_node.prop},
                            direction]

                new_chain = copy.deepcopy(chain)

                def count_persons(new_chain, second_chain):
                    persons  = set()
                    for cur_chain in [new_chain, second_chain]:
                        for tr in cur_chain:
                            for ent in tr:
                                if "person" in ent:
                                    persons.add(ent["person"])
                    return persons

                if triplet not in new_chain:
                    subj = triplet[0]["name"].replace("_", " ")
                    obj = triplet[-2]["name"].replace("_", " ")
                    prop_values = [val.lower() for val in triplet[1]["prop"].values()]
                    cnt1 = 0
                    if subj.lower() in another_entities1:
                        cnt1 += 1
                    if obj.lower() in another_entities1:
                        cnt1 += 1
                    if any([prop_value.lower() in another_entities1 for prop_value in prop_values]):
                        cnt1 += 1

                    if cnt1 > 0:
                        new_chain.append(triplet)
                        inters_chains1.append([new_chain, cnt1])
                    elif "backw" in direction and subj.lower() in another_entities2:
                        new_chain.append(triplet)
                        second_chain = another_entities2[subj.lower()]
                        persons = count_persons(new_chain, second_chain)
                        if not ([ch[-1] for ch in new_chain] == ["forw", "backw"] \
                                and [ch[-1] for ch in second_chain] == ["forw", "backw"]) and len(persons) < 3:
                            inters_chains2.append([new_chain, second_chain, ["backw", subj]])
                    elif "forw" in direction and obj.lower() in another_entities2:
                        new_chain.append(triplet)
                        second_chain = another_entities2[obj.lower()]
                        persons = count_persons(new_chain, second_chain)
                        if not ([ch[-1] for ch in new_chain] == ["forw", "backw"] \
                                and [ch[-1] for ch in second_chain] == ["forw", "backw"]) and len(persons) < 3:
                            inters_chains2.append([new_chain, second_chain, ["forw", obj]])
                    elif any([prop_value.lower() in another_entities2 for prop_value in prop_values]):
                        for prop_value in triplet[1]["prop"].values():
                            if prop_value.lower() in another_entities2:
                                new_chain.append(triplet)
                                second_chain = another_entities2[prop_value.lower()]
                                persons = count_persons(new_chain, second_chain)
                                if len(persons) < 3:
                                    inters_chains2.append([new_chain, second_chain, ["prop", prop_value]])
                    else:
                        new_chain.append(triplet)
                else:
                    new_chain.append(triplet)
                new_entities = []
                if "forw" in direction:
                    new_entities.append((triplet_raw.end_node.name, "", "node"))
                if "backw" in direction:
                    new_entities.append((triplet_raw.start_node.name, "", "node"))
                triplets_info.append([triplet, new_entities, new_chain])
        except Exception as e:
            print(f"error in query execution: {e}")
        return triplets_info, inters_chains1, inters_chains2

    def add_chains(
            self,
            inters_chains1: List[List[List[str]]],
            inters_chains2: List[List[List[str]]],
            cur_inters_chains1: List[List[List[str]]],
            cur_inters_chains2: List[List[List[str]]]
        ) -> Tuple[List[List[List[str]]], List[List[List[str]]]]:
        """_summary_

        :param inters_chains1: пути в графе, которые пересекаются с сущностями из вопроса
        :type inters_chains1: List[List[List[str]]]
        :param inters_chains2: пути в графе, которые пересекаются с другими путями
        :type inters_chains2: List[List[List[str]]]
        :param cur_inters_chains1: пути в графе, которые пересекаются с сущностями из вопроса, на текущем шаге поиска
        :type cur_inters_chains1: List[List[List[str]]]
        :param cur_inters_chains2: пути в графе, которые пересекаются с другими путями, на текущем шаге поиска
        :type cur_inters_chains2: List[List[List[str]]]
        :return: пути в графе, которые пересекаются с сущностями из вопроса
        :rtype: Tuple[List[List[List[str]]], List[List[List[str]]]]
        """
        for ch in cur_inters_chains1:
            if ch not in inters_chains1:
                inters_chains1.append(ch)
        for ch in cur_inters_chains2:
            if ch not in inters_chains2:
                inters_chains2.append(ch)
        return inters_chains1, inters_chains2

    def make_triplet_key(self, triplet: List[Dict[str, str]]) -> Tuple[Tuple[str], Tuple[str]]:
        """_summary_

        :param triplet: триплет
        :type triplet: List[Dict[str, str]]
        :return: субъект, отношение и объект в триплете
        :rtype: Tuple[Tuple[str], Tuple[str]]
        """
        subj, rel, obj, *_ = triplet
        rel_data_items = list(rel["prop"].items())
        rel_data_items = [(key.replace("_", " "), value.replace("_", " ")) for key, value in rel_data_items
                          if key not in ["raw_time", "time", "sentiment"]]
        rel_data_items = sorted(rel_data_items, key=lambda x: x[0])
        rel_data_values = [element[1].lower().replace("_", " ") for element in rel_data_items]
        subj_name = [subj["name"].replace("_", " ")]
        obj_name = [obj["name"].replace("_", " ")]
        rel_type = rel["type"].replace("_", " ")
        keys = [subj_name, rel_type, obj_name] + rel_data_values
        keys_rev = [obj_name, rel_type, subj_name] + rel_data_values
        return tuple(keys), tuple(keys_rev)

    def get_relevant_triplets(self, query_info: QueryInfo, depth: int = 1) -> List[Triplet]:
        self.log("START KNOWLEDGE RETRIEVING ...", verbose=self.verbose)
        self.log("RETRIEVER: WaterCirclesTripletsRetriever", verbose=self.verbose)
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

        triplets_dict, inters_chains1, inters_chains2 = self.bfs(seed_entities, depth)
        output_texts_hyper, output_texts_episodic = self.extract_thesis(seed_entities, same_types)
        #print("texts_hyper", len(output_texts_hyper), "texts_episodic", len(output_texts_episodic))

        thres = self.config.chain_triplets_num
        if len(inters_chains1) == 1:
            thres = self.config.chain_triplets_num
        elif len(inters_chains1) == 2:
            thres = int(self.config.chain_triplets_num * 0.5)
        elif len(inters_chains1) >= 3:
            thres = int(self.config.chain_triplets_num * 0.3)

        chain_triplets = []
        for seed_entity in inters_chains1:
            ent_chain_triplets = []
            ent_inters_chains1 = inters_chains1[seed_entity]
            ent_inters_chains2 = inters_chains2[seed_entity]
            ent_inters_chains1 = sorted(ent_inters_chains1, key=lambda x: x[1], reverse=True)

            inters_chains1_more = [ch for ch, cnt in ent_inters_chains1 if cnt > 1]
            inters_chains1_less = [ch for ch, cnt in ent_inters_chains1 if cnt == 1]
            chain_triplets1_more = process_inters_chains1(inters_chains1_more)
            chain_triplets1_less = process_inters_chains1(inters_chains1_less)

            chain_triplets2 = process_inters_chains2(ent_inters_chains2)
            prob_tr = False
            if self.config.strict_filter:
                if inters_chains1_more:
                    #chain_triplets = chain_triplets1_more + chain_triplets1_less[:3] + chain_triplets2[:3]
                    ent_chain_triplets = chain_triplets1_more
                    prob_tr = True
                else:
                    ent_chain_triplets = chain_triplets1_less + chain_triplets2
                if not ent_chain_triplets:
                    ent_chain_triplets = chain_triplets1_more + chain_triplets1_less + chain_triplets2
            else:
                ent_chain_triplets = chain_triplets1_more + chain_triplets1_less + chain_triplets2
            chain_triplets += ent_chain_triplets[:thres]

        def format_triplet(triplet_data):
            subj, rel, obj, *_ = triplet_data
            subj_node = NodeCreator.create(name=subj["name"], n_type=subj["type"], prop=subj["prop"])
            subj_node.id = subj['id']

            obj_node = NodeCreator.create(name=obj["name"], n_type=obj["type"], prop=obj["prop"])
            obj_node.id = obj['id']

            rel_edge = RelationCreator.create(name=rel.get("name", None), r_type=rel["type"], prop=rel["prop"])
            rel_edge.id=rel["id"]

            triplet = TripletCreator.create(
                start_node=subj_node,
                relation=rel_edge,
                end_node=obj_node,
                add_stringified_triplet=False
            )
            return triplet

        def triplet_from_hyper(text, seed_entity, subj_props, obj_props, rel_props, rel_id):
            subj_node = NodeCreator.create(name=seed_entity, n_type=NodeType.object, prop=subj_props)
            subj_node.id = '1'

            obj_node = NodeCreator.create(name=text, n_type=NodeType.hyper, prop=obj_props)
            obj_node.id = '1'

            rel_edge = RelationCreator.create(r_type=RelationType.hyper, prop=rel_props)
            rel_edge.id=rel_id

            triplet = TripletCreator.create(
                start_node=subj_node,
                relation=rel_edge,
                end_node=obj_node,
                add_stringified_triplet=False
            )
            return triplet

        ex_triplets = []
        formatted_triplets = []
        for text, seed_entity, subj_props, obj_props, rel_props, rel_id in output_texts_hyper:
            triplet = triplet_from_hyper(text, seed_entity, subj_props, obj_props, rel_props, rel_id)
            formatted_triplets.append(triplet)
        for text, seed_entity, subj_props, obj_props, rel_props, rel_id in output_texts_episodic:
            triplet = triplet_from_hyper(text, seed_entity, subj_props, obj_props, rel_props, rel_id)
            formatted_triplets.append(triplet)

        len_he = len(formatted_triplets)
        for triplet in chain_triplets:
            subj, rel, obj, *_ = triplet
            if (subj, rel, obj) not in ex_triplets and (obj, rel, subj) not in ex_triplets:
                formatted_triplet = format_triplet(triplet)
                formatted_triplets.append(formatted_triplet)
                ex_triplets.append((subj, rel, obj))

        if self.config.strict_filter:
            if chain_triplets:
                thres = int(self.config.other_triplets_num * 0.5)
            else:
                thres = self.config.other_triplets_num
        else:
            thres = int(self.config.other_triplets_num * 1.5)

        len_he = len(output_texts_hyper) + len(output_texts_episodic)
        if (not chain_triplets and not prob_tr and len_he < 2) \
                or (not self.config.strict_filter and len(chain_triplets) + len_he < 20):
            total_f_triplets = []
            for (*_, seed_entity, _), triplets in triplets_dict.items():
                f_triplets = []
                for triplet in triplets:
                    reverse_triplet = [triplet[-1]] + triplet[1:-1] + [triplet[0]]
                    if triplet not in total_f_triplets and reverse_triplet not in total_f_triplets:
                        f_triplets.append(triplet)
                        total_f_triplets.append(triplet)
                for triplet in f_triplets[:thres]:
                    formatted_triplet = format_triplet(triplet)
                    formatted_triplets.append(formatted_triplet)
        return formatted_triplets

    def extract_thesis_for_entities(
            self,
            seed_entities: List[List[Tuple[str]]],
            entities_list: List[Tuple[str]],
            entity_type: str,
            texts_set: Set[str]
        ) -> Tuple[List[Tuple[str, str, Dict[str, str], Dict[str, str], int, str]], Set[str]]:
        """_summary_

        :param seed_entities: список сущностей из графа для сущностей из вопроса
        :type seed_entities: List[List[Tuple[str]]]
        :param entities_list: список сущностей из графа для данной сущности из вопроса
        :type entities_list: List[Tuple[str]]
        :param entity_type: тип сущности ("hyper" или "episodic")
        :type entity_type: str
        :param texts_set: набор текстов из триплетов
        :type texts_set: Set[str]
        :return: извлеченные тексты из триплетов типа hyper и episodic
        :rtype: Tuple[List[Tuple[str, str, Dict[str], Dict[str], int, str]], Set[str]]
        """
        cur_texts = []
        for seed_entity, *_ in entities_list:
            another_entities_list = [entities_list2 for entities_list2 in seed_entities
                                        if entities_list2 != entities_list]
            res = self.kg_model.graph_struct.db_conn.get_triplets_by_name(
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
        """_summary_

        :param seed_entities: список сущностей из графа для сущностей из вопроса
        :type seed_entities: List[List[Tuple[str]]]
        :param same_types: принадлежат ли сущности из вопроса к одному и тому же типу
        :type same_types: bool
        :return: список текстов тезисов
        :rtype: List[str]
        """
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
        """_summary_

        :param seed_entities: список сущностей из графа для сущностей из вопроса
        :type seed_entities: List[List[Tuple[str]]]
        :param depth: глубина поиска
        :type depth: int, optional
        :param subj_labels: список типов субъекта в триплетах, включаемых в пути в графе во время поиска
        :type subj_labels: List[str], optional
        :param obj_labels: список типов субъекта в триплетах, включаемых в пути в графе во время поиска
        :type obj_labels: List[str], optional
        :param use_rel_props: использовать ли при поиске свойства relations
        :type use_rel_props: bool, optional
        :return: извлеченные триплеты и пути в графе
        :rtype: Tuple[Dict[tuple, List[List[dict], List[Tuple[str]], List[List[dict]]]],
                      List[List[List[str]]],
                      List[List[List[str]]]]
        """
        triplets_dict = {}
        inters_chains1, inters_chains2 = {}, {}
        # seed_entity, prop_name="", entity_type="node"
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
                    triplets_info = []
                    new_entities = []
                    for entity, prop_name, tp, chain in entities[(seed_entity, ne)]:
                        if (entity, prop_name, tp) not in used_entities[(seed_entity, ne)]:
                            if tp == "node":
                                cur_triplets_info, cur_inters_chains1, cur_inters_chains2 = self.parse_triplet_output(
                                    "forw",
                                    [[entity, entity.replace(" ", "_")], [], "object"],
                                    another_entities1,
                                    another_entities2,
                                    chain
                                )
                                ent_inters_chains1, ent_inters_chains2 = \
                                    self.add_chains(ent_inters_chains1, ent_inters_chains2, cur_inters_chains1, cur_inters_chains2)
                                for triplet in cur_triplets_info:
                                    triplets_info.append([(step, "forw", seed_entity, triplet[0][1]["type"])] + triplet)
                                cur_triplets_info, cur_inters_chains1, cur_inters_chains2 = self.parse_triplet_output(
                                    "backw",
                                    [[], [entity, entity.replace(" ", "_")], "object"],
                                    another_entities1,
                                    another_entities2,
                                    chain
                                )
                                ent_inters_chains1, ent_inters_chains2 = \
                                    self.add_chains(ent_inters_chains1, ent_inters_chains2, cur_inters_chains1, cur_inters_chains2)
                                for triplet in cur_triplets_info:
                                    triplets_info.append([(step, "backw", seed_entity, triplet[0][1]["type"])] + triplet)
                                used_entities[(seed_entity, ne)].add((entity, prop_name, tp))
                            elif tp == "rel_prop" and use_rel_props:
                                query = self.extract_triplets_rel_prop_template.format(
                                    prop_name=prop_name,
                                    prop_value=entity.capitalize()
                                )
                                cur_triplets_info, cur_inters_chains1, cur_inters_chains2 = self.parse_triplet_output(
                                    "forw/backw", query, another_entities1, another_entities2, chain, subj_labels, obj_labels
                                )
                                ent_inters_chains1, ent_inters_chains2 = \
                                    self.add_chains(ent_inters_chains1, ent_inters_chains2, cur_inters_chains1, cur_inters_chains2)
                                for triplet in cur_triplets_info:
                                    triplets_info.append([(step, "forw", seed_entity, triplet[0][1]["type"])] + triplet)
                                used_entities[(seed_entity, ne)].add((entity, prop_name, tp))

                    for step_dir_seed_rel, triplet, cur_entities, new_chain in triplets_info:
                        for (cur_ent, cur_prop_name, cur_prop_type) in cur_entities:
                            if (cur_ent, cur_prop_name, cur_prop_type, new_chain) not in new_entities:
                                new_entities.append((cur_ent, cur_prop_name, cur_prop_type, new_chain))
                        if step_dir_seed_rel not in triplets_dict:
                            triplets_dict[step_dir_seed_rel] = []
                        triplets_dict[step_dir_seed_rel].append(triplet)
                    entities[(seed_entity, ne)] += new_entities

                    if seed_entity not in inters_chains1:
                        inters_chains1[seed_entity] = ent_inters_chains1
                    else:
                        inters_chains1[seed_entity] += ent_inters_chains1
                    if seed_entity not in inters_chains2:
                        inters_chains2[seed_entity] = ent_inters_chains2
                    else:
                        inters_chains2[seed_entity] += ent_inters_chains2
        return triplets_dict, inters_chains1, inters_chains2
