from neo4j import GraphDatabase
from typing import List, Dict, Union
import json

from ..utils import GraphDBConnectionConfig, AbstractGraphDatabaseConnection
from ....utils.data_structs import Triplet, Node, Relation, TripletCreator, NodeCreator, NodeType, RelationCreator, RelationType, NODES_TYPES_MAP, RELATIONS_TYPES_MAP

DEFAULT_NEO4J_CONFIG = GraphDBConnectionConfig(
    host='localhost', port=7687, params={'user': "neo4j", 'pwd': 'password'})

class Neo4jConnector(AbstractGraphDatabaseConnection):

    def __init__(self, config: GraphDBConnectionConfig = DEFAULT_NEO4J_CONFIG):
        self.config = config

    def open_connection(self) -> None:
        self.driver = None
        try:
            self.driver = GraphDatabase.driver(
                f"bolt://{self.config.host}:{self.config.port}",
                auth=(self.config.params['user'], self.config.params['pwd']))
        except Exception as e:
            print("Failed to create the driver:", e)

        #
        self.execute_query(f'CREATE DATABASE {self.config.db_info["db"]} IF NOT EXISTS', db_flag=False)

        # Creating indexes
        self.execute_query("CREATE INDEX name_object_node IF NOT EXISTS FOR (n:object) ON n.name")
        self.execute_query("CREATE INDEX name_hyper_node IF NOT EXISTS FOR (n:hyper) ON n.name ")
        self.execute_query("CREATE INDEX name_episodic_node IF NOT EXISTS FOR (n:episodic) ON n.name")

        self.execute_query("CREATE INDEX strid_object_node IF NOT EXISTS FOR (n:object) ON n.str_id")
        self.execute_query("CREATE INDEX strid_hyper_node IF NOT EXISTS FOR (n:hyper) ON n.str_id")
        self.execute_query("CREATE INDEX strid_episodic_node IF NOT EXISTS FOR (n:episodic) ON n.str_id")

        self.execute_query("CREATE INDEX strid_simple_relation IF NOT EXISTS FOR ()-[r:simple]->() ON r.str_id")
        self.execute_query("CREATE INDEX strid_hyper_relation IF NOT EXISTS FOR ()-[r:hyper]->() ON r.str_id ")
        self.execute_query("CREATE INDEX strid_episodic_relation IF NOT EXISTS FOR ()-[r:episodic]->() ON r.str_id")

        self.execute_query("CREATE INDEX tid_simple_relation IF NOT EXISTS FOR ()-[r:simple]->() ON r.t_id")
        self.execute_query("CREATE INDEX tid_hyper_relation IF NOT EXISTS FOR ()-[r:hyper]->() ON r.t_id")
        self.execute_query("CREATE INDEX tid_episodic_relation IF NOT EXISTS FOR ()-[r:episodic]->() ON r.t_id")

        self.execute_query("CREATE INDEX name_simple_relation IF NOT EXISTS FOR ()-[r:simple]->() ON r.name")
        self.execute_query("CREATE INDEX name_hyper_relation IF NOT EXISTS FOR ()-[r:hyper]->() ON r.name")
        self.execute_query("CREATE INDEX name_episodic_relation IF NOT EXISTS FOR ()-[r:episodic]->() ON r.name")

        if self.config.need_to_clear:
            self.clear()

    def is_open(self) -> None:
        # TODO
        pass

    def close_connection(self) -> None:
        if self.driver is not None:
            self.driver.close()

    def __del__(self):
        self.close_connection()

    def create_node_query(self, node: Node) -> str:
        query_props = {}
        for prop_name, prop_value in node.prop.items():
            p_name, p_value = prop_name.replace(" ", "_"), json.dumps(prop_value, ensure_ascii=False)
            query_props[p_name] = p_value

        query_props['name'] = json.dumps(node.name, ensure_ascii=False)
        query_props['str_id'] = json.dumps(node.id, ensure_ascii=False)

        str_props = ", ".join([f"{k}: {v}" for k, v in query_props.items()])
        query = f"CREATE (n:{node.type.value} " + "{" + str_props + "}) RETURN elementId(n) as node_id"
        return query


    def create_rel_query(self, triplet: Triplet) -> str:
        rel_props = {}
        for prop_name, prop_value in triplet.relation.prop.items():
            p_name, p_value = prop_name.replace(' ', '_'), json.dumps(prop_value, ensure_ascii=False)
            rel_props[p_name] = p_value

        rel_props['name'] = json.dumps(triplet.relation.name, ensure_ascii=False)
        rel_props['t_id'] = json.dumps(triplet.id, ensure_ascii=False)
        rel_props['str_id'] = json.dumps(triplet.relation.id, ensure_ascii=False)

        str_props = ", ".join([f"{k}: {v}" for k, v in rel_props.items()])
        subj_t, subj_id = triplet.start_node.type.value, triplet.start_node.id
        obj_t, obj_id = triplet.end_node.type.value, triplet.end_node.id
        rel_t = triplet.relation.type.value
        query = ""
        query += f'MATCH (subj:{subj_t}), (obj:{obj_t}) WHERE subj.str_id = "{subj_id}" AND obj.str_id = "{obj_id}" '
        query += f'CREATE (subj)-[rel:{rel_t}' + '{' + str_props + '}' + ']->(obj) '
        query += 'RETURN elementId(rel) as rel_id'
        return query

    def create(self, triplets: List[Triplet], creation_info: Dict[int, Dict[str, bool]] = dict()) -> None:
        # triplet-ids checking
        for triplet in triplets:
            if type(triplet.id) is not str:
                raise ValueError
        unique_ids = set(map(lambda triplet: triplet.id, triplets))
        if len(triplets) != len(unique_ids):
            raise ValueError

        for i, triplet in enumerate(triplets):
            cur_info = creation_info.get(i, None)
            if cur_info is None or cur_info['s_node']:
                insert_subj_query = self.create_node_query(triplet.start_node)
                self.execute_query(insert_subj_query)
            if cur_info is None or cur_info['e_node']:
                insert_obj_query = self.create_node_query(triplet.end_node)
                self.execute_query(insert_obj_query)

            insert_rel_query = self.create_rel_query(triplet)
            self.execute_query(insert_rel_query)


    def read(self, ids: List[str]) -> List[Triplet]:
        for t_id in ids:
            if type(t_id) is not str:
                raise ValueError

        str_ids = '['+', '.join(list(map(lambda id: f'"{id}"', ids))) + ']'
        query = f"MATCH (n1)-[rel]->(n2) WHERE any(id IN {str_ids} WHERE rel.t_id = id) RETURN n1, rel, n2"
        raw_output = self.execute_query(query)
        triplets = self.parse_query_triplets_output(raw_output)
        return triplets

    def update(self, items: List[Triplet]) -> None:
        # TODO
        pass

    def delete(self, ids: List[str], delete_info: Dict[int,Dict[str,bool]] = dict()) -> None:
        for t_id in ids:
            if type(t_id) is not str:
                raise ValueError

        for i, t_id in enumerate(ids):
            cur_info = delete_info.get(i, None)
            nodes_to_delete = []

            if cur_info is None or cur_info['s_node']:
                nodes_to_delete.append('sn_id')

            if cur_info is None or cur_info['e_node']:
                nodes_to_delete.append('en_id')


            output = self.execute_query(f'MATCH (s_node)-[rel]->(e_node) WHERE rel.t_id = "{t_id}" DELETE rel RETURN elementId(s_node) as sn_id, elementId(e_node) as en_id')
            if len(output) < 1:
                continue

            assert len(output) == 1

            if len(nodes_to_delete) > 0:
                where_statement = []
                for n_name in nodes_to_delete:
                    where_statement.append(f'elementId(n) = "{output[0][n_name]}"')
                where_statement = ' or '.join(where_statement)
                self.execute_query(f'MATCH (n) WHERE {where_statement} DELETE n')

    def read_by_name(self, name: str, object_type: Union[RelationType, NodeType], object: str = 'relation') -> List[Union[Triplet, Node]]:
        if type(object_type) not in [RelationType, NodeType]:
            raise ValueError

        if type(name) is not str:
            raise ValueError

        if len(name) < 1:
            raise ValueError

        dump_name = json.dumps(name, ensure_ascii=False)
        if object == 'relation':
            output = self.execute_query(f'MATCH (n1)-[rel:{object_type.value}]->(n2) WHERE rel.name = {dump_name} RETURN n1,rel,n2;')
            formated_output = self.parse_query_triplets_output(output)
        elif object == 'node':
            output = self.execute_query(f'MATCH (n:{object_type.value}) WHERE n.name = {dump_name} RETURN n;')
            formated_output = self.parse_query_nodes_output(output)
        else:
            raise ValueError

        return formated_output

    def execute_query(self, query: str, db_flag: bool = True) -> List[object]:
        assert self.driver is not None, "Driver not initialized!"
        session = None
        response = None
        try:
            session = self.driver.session(database=self.config.db_info['db']) if db_flag else self.driver.session()
            response = list(session.run(query))
        except Exception as e:
            print("Query failed:", e)
            print("Error query: ", query)
        finally:
            if session is not None:
                session.close()
        return response

    def get_adjecent_nids(self, base_node_id: str,
            accepted_n_types: List[NodeType] = [NodeType.object, NodeType.hyper, NodeType.episodic]) -> List[str]:
        if type(base_node_id) is not str:
            raise ValueError

        str_accepted_nodes = ', '.join(list(map(lambda tpe: f'"{tpe.value}"', accepted_n_types)))

        raw_nodes = self.execute_query(
            f'MATCH (a)-[r]-(b) WHERE a.str_id = "{base_node_id}" AND ANY(lbl in [{str_accepted_nodes}] where lbl in labels(b)) RETURN b')
        formated_nodes = [node['b']['str_id'] for node in raw_nodes]
        return formated_nodes

    def get_nodes_shared_ids(self, node1_id: str, node2_id: str, id_type: str = 'both') -> List[Dict[str,str]]:
        if (type(node1_id) is not str) or (type(node2_id) is not str):
            raise ValueError(node1_id, node2_id)
        if type(id_type) is not str:
            raise ValueError(id_type)

        if id_type == 'triplet':
            str_return_info = 'r.t_id as t_id'
        elif id_type == 'relation':
            str_return_info = 'r.str_id as r_id'
        elif id_type == 'both':
            str_return_info = 'r.t_id as t_id, r.str_id as r_id'
        else:
            raise ValueError(id_type)

        raw_rels = self.execute_query(
            f'MATCH (a)-[r]-(b) WHERE a.str_id = "{node1_id}" AND b.str_id = "{node2_id}" RETURN {str_return_info};')

        formated_info = []
        for raw_rel in raw_rels:
            tmp_info = dict()
            if id_type in ['both', 'triplet']:
                tmp_info['t_id'] = raw_rel['t_id']

            if id_type in ['both', 'relation']:
                tmp_info['r_id'] = raw_rel['r_id']

            formated_info.append(tmp_info)

        return formated_info

    # TO THINK (do we need field serialization because we do json.dumps)
    def _load_dumped_dict(self, raw_dict: dict) -> Dict:
        loaded_dict = dict()
        for k,v in raw_dict.items():
            try:
                loaded_dict[k] = json.loads(v)
            except json.decoder.JSONDecodeError as e:
                loaded_dict[k] = v
        return loaded_dict

    def parse_query_nodes_output(self, output: List[object]) -> List[Node]:
        formated_nodes = []
        for raw_node in output:

            n_dict = dict(raw_node['n'])

            node = NodeCreator.create(
                n_type=NODES_TYPES_MAP[list(raw_node['n'].labels)[0]],
                name=n_dict['name'], prop={**n_dict})

            formated_nodes.append(node)
        return formated_nodes

    def parse_query_triplets_output(self, output: List[object]) -> List[Triplet]:
        formated_triplets = []
        for raw_triplet in output:

            n1_dict = dict(raw_triplet['n1'])
            n2_dict = dict(raw_triplet['n2'])
            rel_dict = dict(raw_triplet['rel'])

            node1 = NodeCreator.create(
                n_type=NODES_TYPES_MAP[list(raw_triplet['n1'].labels)[0]],
                name=n1_dict['name'], prop=n1_dict, add_stringified_node=False)

            node2 = NodeCreator.create(
                n_type=NODES_TYPES_MAP[list(raw_triplet['n2'].labels)[0]],
                name=n2_dict['name'], prop=n2_dict, add_stringified_node=False)

            relation = RelationCreator.create(
                r_type=RELATIONS_TYPES_MAP[raw_triplet['rel'].type],
                name=rel_dict['name'], prop=rel_dict)

            start_node_id = raw_triplet['rel'].nodes[0].element_id
            if start_node_id == raw_triplet['n1'].element_id:
                start_node, end_node = (node1, node2)
            elif start_node_id == raw_triplet['n2'].element_id:
                start_node, end_node = (node2, node1)
            else:
                raise ValueError

            triplet = TripletCreator.create(
                start_node, relation, end_node, add_stringified_triplet=True)
            formated_triplets.append(triplet)

        # print("PARSED_TRIPLETS: ")
        # for triplet in formated_triplets:
        #     print(f"* triplet_id = {triplet.id}")
        #     print(f"\t s_node: id = {triplet.start_node.id}; str_id = {triplet.start_node.prop['str_id']}")
        #     print(f"\t rel: id = {triplet.relation.id}; t_id = {triplet.relation.prop['t_id']} str_id = {triplet.relation.prop['str_id']}")
        #     print(f"\t e_node: id = {triplet.end_node.id}; str_id = {triplet.end_node.prop['str_id']}")

        return formated_triplets

    def get_triplets(self, node1_id: str, node2_id: str) -> List[Triplet]:
        if (type(node1_id) is not str) or (type(node2_id) is not str):
            raise ValueError
        if (not self.item_exist(node1_id, id_type='node')) or (not self.item_exist(node2_id, id_type='node')):
            raise ValueError

        output = self.execute_query(
            f'MATCH (n1)-[rel]-(n2) WHERE n1.str_id = "{node1_id}" AND n2.str_id = "{node2_id}" RETURN n1, rel, n2')

        formated_triplets = self.parse_query_triplets_output(output)
        return formated_triplets

    def get_triplets_by_name(self, subj_names: List[str], obj_names: List[str], obj_type: str) -> List[Triplet]:
        formated_triplets = []
        if subj_names:
            for subj_name in subj_names:
                subj_dump = json.dumps(subj_name, ensure_ascii=False)
                output = self.execute_query(
                    f'MATCH (n1:object)-[rel]-(n2:{obj_type}) WHERE LOWER(n1.name) = LOWER({subj_dump}) RETURN n1, rel, n2')
                formated_triplets += self.parse_query_triplets_output(output)
        elif obj_names:
            for obj_name in obj_names:
                obj_dump = json.dumps(obj_name, ensure_ascii=False)
                output = self.execute_query(
                    f'MATCH (n1:object)-[rel]-(n2:{obj_type}) WHERE LOWER(n2.name) = LOWER({obj_dump}) RETURN n1, rel, n2')
                formated_triplets += self.parse_query_triplets_output(output)
        else:
            output = self.execute_query(
                f'MATCH (n1:object)-[rel]-(n2:{obj_type}) RETURN n1, rel, n2')
            formated_triplets += self.parse_query_triplets_output(output)

        return formated_triplets

    def count_items(self, id: str = None, id_type: str = None) -> Union[Dict[str,int],int]:
        if id_type is None:
            n_raw = self.execute_query("MATCH (a) RETURN count(a) as n_count")
            r_raw = self.execute_query("MATCH (a)-[rel]->(b) RETURN count(rel) as r_count")
            
            n_count = n_raw[0]['n_count'] if n_raw and len(n_raw) > 0 else 0
            r_count = r_raw[0]['r_count'] if r_raw and len(r_raw) > 0 else 0
            result = {'triplets': r_count, 'nodes': n_count}

        elif id_type == 'node':
            n_raw = self.execute_query(f'MATCH (a) WHERE a.str_id = "{id}" RETURN COUNT(a) as n_count')
            result = n_raw[0]['n_count'] if n_raw and len(n_raw) > 0 else 0

        elif id_type == 'relation':
            r_raw = self.execute_query(f'MATCH (a)-[rel]->(b) WHERE rel.str_id = "{id}" RETURN COUNT(rel) as r_count')
            result = r_raw[0]['r_count'] if r_raw and len(r_raw) > 0 else 0

        elif id_type == 'triplet':
            r_raw = self.execute_query(f'MATCH (a)-[rel]->(b) WHERE rel.t_id = "{id}" RETURN COUNT(rel) as r_count')
            result = r_raw[0]['r_count'] if r_raw and len(r_raw) > 0 else 0

        else:
            raise ValueError

        return result

    def item_exist(self, id: str, id_type='triplet') -> bool:
        if type(id) is not str:
            raise ValueError

        if id_type == 'node':
            query = f'MATCH (n) WHERE n.str_id = "{id}" RETURN n'
        elif id_type == 'relation':
            query = f'MATCH (n1)-[rel]-(n2) WHERE rel.str_id = "{id}" RETURN rel'
        elif id_type == 'triplet':
            query = f'MATCH (n1)-[rel]-(n2) WHERE rel.t_id = "{id}" RETURN rel'
        else:
            raise ValueError

        output = self.execute_query(query)
        return len(output) > 0
    
    def get_node_type(self, id: str) -> NodeType:
        if not self.item_exist(id, id_type="node"):
            raise ValueError
        
        raw_output = self.execute_query(f'MATCH (n) WHERE n.str_id = "{id}" RETURN n')
        formated_node = self.parse_query_nodes_output(raw_output)[0]
        return formated_node.type

    def clear(self) -> None:
        self.execute_query("MATCH (n)-[rel]->() DELETE n,rel")
        self.execute_query("MATCH (n) DELETE n")
