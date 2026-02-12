from neo4j import GraphDatabase
from typing import List, Dict, Union
import json

from ..utils import GraphDBConnectionConfig, AbstractGraphDatabaseConnection
from ....utils.data_structs import Quadruplet, Node, Relation, QuadrupletCreator, NodeCreator, NodeType, RelationCreator, RelationType, NODES_TYPES_MAP, RELATIONS_TYPES_MAP

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
        try:
            self.execute_query(f'CREATE DATABASE {self.config.db_info["db"]} IF NOT EXISTS', db_flag=False)
        except Exception as e:
            # Ignore if database creation is not supported (e.g. Community Edition) or already exists
            print(f"Warning: Could not create database (might be Community Edition or already exists): {e}")

        # Creating indexes
        self.execute_query("CREATE INDEX name_object_node IF NOT EXISTS FOR (n:object) ON n.name")
        self.execute_query("CREATE INDEX name_hyper_node IF NOT EXISTS FOR (n:hyper) ON n.name ")
        self.execute_query("CREATE INDEX name_episodic_node IF NOT EXISTS FOR (n:episodic) ON n.name")
        self.execute_query("CREATE INDEX name_time_node IF NOT EXISTS FOR (n:time) ON n.name") # NEW

        self.execute_query("CREATE INDEX strid_object_node IF NOT EXISTS FOR (n:object) ON n.str_id")
        self.execute_query("CREATE INDEX strid_hyper_node IF NOT EXISTS FOR (n:hyper) ON n.str_id")
        self.execute_query("CREATE INDEX strid_episodic_node IF NOT EXISTS FOR (n:episodic) ON n.str_id")
        self.execute_query("CREATE INDEX strid_time_node IF NOT EXISTS FOR (n:time) ON n.str_id") # NEW

        self.execute_query("CREATE INDEX strid_simple_relation IF NOT EXISTS FOR ()-[r:simple]->() ON r.str_id")
        self.execute_query("CREATE INDEX strid_hyper_relation IF NOT EXISTS FOR ()-[r:hyper]->() ON r.str_id ")
        self.execute_query("CREATE INDEX strid_episodic_relation IF NOT EXISTS FOR ()-[r:episodic]->() ON r.str_id")
        self.execute_query("CREATE INDEX strid_time_relation IF NOT EXISTS FOR ()-[r:time]->() ON r.str_id") # NEW

        self.execute_query("CREATE INDEX tid_simple_relation IF NOT EXISTS FOR ()-[r:simple]->() ON r.t_id")
        self.execute_query("CREATE INDEX tid_hyper_relation IF NOT EXISTS FOR ()-[r:hyper]->() ON r.t_id")
        self.execute_query("CREATE INDEX tid_episodic_relation IF NOT EXISTS FOR ()-[r:episodic]->() ON r.t_id")
        self.execute_query("CREATE INDEX tid_time_relation IF NOT EXISTS FOR ()-[r:time]->() ON r.t_id") # NEW

        self.execute_query("CREATE INDEX name_simple_relation IF NOT EXISTS FOR ()-[r:simple]->() ON r.name")
        self.execute_query("CREATE INDEX name_hyper_relation IF NOT EXISTS FOR ()-[r:hyper]->() ON r.name")
        self.execute_query("CREATE INDEX name_episodic_relation IF NOT EXISTS FOR ()-[r:episodic]->() ON r.name")
        self.execute_query("CREATE INDEX name_time_relation IF NOT EXISTS FOR ()-[r:time]->() ON r.name") # NEW

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


    def create_rel_query(self, quadruplet: Quadruplet) -> str:
        # This creates the main relation S->O.
        # Ideally for a quadruplet S,R,O,T we might want (Event)-[at]->(Time) or similar,
        # but adhering to the previous schema where T was a property or implicit,
        # we will add T info to the relation properties AND potentially create a link if needed?
        # For now, let's keep the graph simple: (S)-[R {t_id: ...}]->(O) and optionally link to Time if we want explicit time nodes.
        # But wait, the update creates Time nodes now.
        # So we should probably stick to S->O and just store t_id on the edge to reference the time node,
        # OR actually link it.
        # Given the previous code just stored `t_id` as a property, we will continue that for compatibility
        # but we effectively have "Quadruplet" logic now.

        rel_props = {}
        for prop_name, prop_value in quadruplet.relation.prop.items():
            p_name, p_value = prop_name.replace(' ', '_'), json.dumps(prop_value, ensure_ascii=False)
            rel_props[p_name] = p_value

        rel_props['name'] = json.dumps(quadruplet.relation.name, ensure_ascii=False)
        rel_props['t_id'] = json.dumps(quadruplet.id, ensure_ascii=False) # This is the QUADRUPLET ID
        rel_props['str_id'] = json.dumps(quadruplet.relation.id, ensure_ascii=False)
        
        # Add Time Node Reference
        if quadruplet.time:
             rel_props['time_node_id'] = json.dumps(quadruplet.time.id, ensure_ascii=False)

        str_props = ", ".join([f"{k}: {v}" for k, v in rel_props.items()])
        subj_t, subj_id = quadruplet.start_node.type.value, quadruplet.start_node.id
        obj_t, obj_id = quadruplet.end_node.type.value, quadruplet.end_node.id
        rel_t = quadruplet.relation.type.value
        
        query = ""
        query += f'MATCH (subj:{subj_t}), (obj:{obj_t}) WHERE subj.str_id = "{subj_id}" AND obj.str_id = "{obj_id}" '
        query += f'CREATE (subj)-[rel:{rel_t}' + '{' + str_props + '}' + ']->(obj) '
        query += 'RETURN elementId(rel) as rel_id'
        return query

    def create(self, quadruplets: List[Quadruplet], creation_info: Dict[int, Dict[str, bool]] = dict()) -> None:
        # quadruplet-ids checking
        for quadruplet in quadruplets:
            if type(quadruplet.id) is not str:
                raise ValueError
        unique_ids = set(map(lambda q: q.id, quadruplets))
        if len(quadruplets) != len(unique_ids):
            # This might happen if duplicates are passed, strictly speaking we can just warn or allow?
            # Original code raised ValueError.
            raise ValueError

        for i, quadruplet in enumerate(quadruplets):
            cur_info = creation_info.get(i, None)
            
            # Create S
            if cur_info is None or cur_info['s_node']:
                insert_subj_query = self.create_node_query(quadruplet.start_node)
                self.execute_query(insert_subj_query)
            
            # Create O
            if cur_info is None or cur_info['e_node']:
                insert_obj_query = self.create_node_query(quadruplet.end_node)
                self.execute_query(insert_obj_query)

            # Create T (New)
            if cur_info is None or cur_info.get('t_node', False):
                 if quadruplet.time:
                    insert_time_query = self.create_node_query(quadruplet.time)
                    self.execute_query(insert_time_query)

            # Create R
            insert_rel_query = self.create_rel_query(quadruplet)
            self.execute_query(insert_rel_query)


    def read(self, ids: List[str]) -> List[Quadruplet]:
        for t_id in ids:
            if type(t_id) is not str:
                raise ValueError

        str_ids = '['+', '.join(list(map(lambda id: f'"{id}"', ids))) + ']'
        # Note: 'rel.t_id' here refers to the Quadruplet ID stored on the relation
        query = f"MATCH (n1)-[rel]->(n2) WHERE any(id IN {str_ids} WHERE rel.t_id = id) " \
                f"OPTIONAL MATCH (t:time) WHERE t.str_id = rel.time_node_id " \
                f"RETURN n1, rel, n2, t"
        raw_output = self.execute_query(query)
        quadruplets = self.parse_query_triplets_output(raw_output) # Renaming this method below would be better but let's see
        return quadruplets

    def update(self, items: List[Quadruplet]) -> None:
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

    def read_by_name(self, name: str, object_type: Union[RelationType, NodeType], object: str = 'relation') -> List[Union[Quadruplet, Node]]:
        if type(object_type) not in [RelationType, NodeType]:
            raise ValueError
        
        # Mapping for safety if object_type is string - but type hint says Enum
        # Original code didn't map here, assuming Enum passed
        
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

        if id_type == 'quadruplet': # Renamed from triplet
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
            if id_type in ['both', 'quadruplet']:
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

    # Renamed from parse_query_triplets_output
    def parse_query_triplets_output(self, output: List[object]) -> List[Quadruplet]:
        formated_quadruplets = []
        for raw_row in output:

            n1_dict = dict(raw_row['n1'])
            n2_dict = dict(raw_row['n2'])
            rel_dict = dict(raw_row['rel'])

            node1 = NodeCreator.create(
                n_type=NODES_TYPES_MAP[list(raw_row['n1'].labels)[0]],
                name=n1_dict['name'], prop=n1_dict, add_stringified_node=False)

            node2 = NodeCreator.create(
                n_type=NODES_TYPES_MAP[list(raw_row['n2'].labels)[0]],
                name=n2_dict['name'], prop=n2_dict, add_stringified_node=False)

            relation = RelationCreator.create(
                r_type=RELATIONS_TYPES_MAP[raw_row['rel'].type],
                name=rel_dict['name'], prop=rel_dict)

            start_node_id = raw_row['rel'].nodes[0].element_id
            if start_node_id == raw_row['n1'].element_id:
                start_node, end_node = (node1, node2)
            elif start_node_id == raw_row['n2'].element_id:
                start_node, end_node = (node2, node1)
            else:
                raise ValueError

            # Try to recover Time node
            time_node = None
            if 't' in raw_row and raw_row['t']:
                t_dict = dict(raw_row['t'])
                time_name = t_dict.get('name', 'Unknown')
                # print(f"DEBUG: [Neo4j] Found Time Node: {time_name}") # Uncomment for verbose
                time_node = NodeCreator.create(
                    n_type=NodeType.time,
                    name=time_name,
                    prop=t_dict,
                    add_stringified_node=True
                )
            
            time_node_id = rel_dict.get('time_node_id')
            
            # Fallback: If 't' is missing but we have an ID, try to fetch it directly
            if time_node is None and time_node_id:
                # Try raw ID and cleaned ID
                tid_clean = time_node_id.replace('"', '')
                # print(f"DEBUG: [Neo4j] Fallback fetching Time Node for ID: {time_node_id} / {tid_clean}")
                
                # Careful with quotes in the query string itself
                t_fallback_query = (
                    f'MATCH (t:time) '
                    f'WHERE t.str_id = \'{time_node_id}\' OR t.str_id = \'{tid_clean}\' '
                    f'RETURN t LIMIT 1'
                )
                t_res = self.execute_query(t_fallback_query)
                if t_res:
                    t_dict = dict(t_res[0]['t'])
                    time_name = t_dict.get('name', 'Unknown')
                    # print(f"DEBUG: [Neo4j] Fallback FOUND: {time_name}")
                    time_node = NodeCreator.create(
                        n_type=NodeType.time,
                        name=time_name,
                        prop=t_dict,
                        add_stringified_node=True
                    )

            if time_node is None:
                 # print(f"DEBUG: [Neo4j] Time Node MISSING for relation {rel_dict.get('name')} (ID: {time_node_id})")
                 # Use 'Always' as default only if no time info is present, otherwise 'Unknown'
                 time_node = NodeCreator.create(NodeType.time, "Unknown", add_stringified_node=True) 

            quadruplet = QuadrupletCreator.create(
                start_node, relation, end_node, time=time_node, add_stringified_quadruplet=True)
            formated_quadruplets.append(quadruplet)

        return formated_quadruplets

    def get_quadruplets(self, node1_id: str, node2_id: str) -> List[Quadruplet]:
        if (type(node1_id) is not str) or (type(node2_id) is not str):
            raise ValueError
        if (not self.item_exist(node1_id, id_type='node')) or (not self.item_exist(node2_id, id_type='node')):
            raise ValueError

        # Updated query to optionally fetch the time node linked by time_node_id
        # We use single quotes for the f-string, so we can use double quotes for string literals in Cypher easily? 
        # Actually, using tripple quotes is safer for complex strings.
        # We want to execute: replace(rel.time_node_id, '"', '')
        
        query = (
            f'MATCH (n1)-[rel]-(n2) WHERE n1.str_id = "{node1_id}" AND n2.str_id = "{node2_id}" '
            f'OPTIONAL MATCH (t:time) WHERE t.str_id = rel.time_node_id OR t.str_id = replace(rel.time_node_id, \'"\', \'\') '
            f'RETURN n1, rel, n2, t'
        )
        
        output = self.execute_query(query)

        formated_quadruplets = self.parse_query_triplets_output(output)
        return formated_quadruplets

    def get_quadruplets_by_name(self, subj_names: List[str], obj_names: List[str], obj_type: str) -> List[Quadruplet]:
        formated_quadruplets = []
        if subj_names:
            for subj_name in subj_names:
                subj_dump = json.dumps(subj_name, ensure_ascii=False)
                output = self.execute_query(
                    f'MATCH (n1:object)-[rel]-(n2:{obj_type}) WHERE LOWER(n1.name) = LOWER({subj_dump}) '
                    f'OPTIONAL MATCH (t:time) WHERE t.str_id = rel.time_node_id OR t.str_id = replace(rel.time_node_id, "\\"", "") '
                    f'RETURN n1, rel, n2, t')
                formated_quadruplets += self.parse_query_triplets_output(output)
        elif obj_names:
            for obj_name in obj_names:
                obj_dump = json.dumps(obj_name, ensure_ascii=False)
                output = self.execute_query(
                    f'MATCH (n1:object)-[rel]-(n2:{obj_type}) WHERE LOWER(n2.name) = LOWER({obj_dump}) '
                    f'OPTIONAL MATCH (t:time) WHERE t.str_id = rel.time_node_id OR t.str_id = replace(rel.time_node_id, "\\"", "") '
                    f'RETURN n1, rel, n2, t')
                formated_quadruplets += self.parse_query_triplets_output(output)
        else:
            output = self.execute_query(
                f'MATCH (n1:object)-[rel]-(n2:{obj_type}) '
                f'OPTIONAL MATCH (t:time) WHERE t.str_id = rel.time_node_id OR t.str_id = replace(rel.time_node_id, "\\"", "") '
                f'RETURN n1, rel, n2, t')
            formated_quadruplets += self.parse_query_triplets_output(output)

        return formated_quadruplets

    def count_items(self, id: str = None, id_type: str = None) -> Union[Dict[str,int],int]:
        if id_type is None:
            n_raw = self.execute_query("MATCH (a) RETURN count(a) as n_count")
            r_raw = self.execute_query("MATCH (a)-[rel]->(b) RETURN count(rel) as r_count")
            
            n_count = n_raw[0]['n_count'] if n_raw and len(n_raw) > 0 else 0
            r_count = r_raw[0]['r_count'] if r_raw and len(r_raw) > 0 else 0
            result = {'quadruplets': r_count, 'nodes': n_count}

        elif id_type == 'node':
            n_raw = self.execute_query(f'MATCH (a) WHERE a.str_id = "{id}" RETURN COUNT(a) as n_count')
            result = n_raw[0]['n_count'] if n_raw and len(n_raw) > 0 else 0

        elif id_type == 'relation':
            r_raw = self.execute_query(f'MATCH (a)-[rel]->(b) WHERE rel.str_id = "{id}" RETURN COUNT(rel) as r_count')
            result = r_raw[0]['r_count'] if r_raw and len(r_raw) > 0 else 0

        elif id_type == 'quadruplet':
            r_raw = self.execute_query(f'MATCH (a)-[rel]->(b) WHERE rel.t_id = "{id}" RETURN COUNT(rel) as r_count')
            result = r_raw[0]['r_count'] if r_raw and len(r_raw) > 0 else 0

        else:
            raise ValueError

        return result

    def item_exist(self, id: str, id_type='quadruplet') -> bool:
        if type(id) is not str:
            raise ValueError

        if id_type == 'node':
            query = f'MATCH (n) WHERE n.str_id = "{id}" RETURN n'
        elif id_type == 'relation':
            query = f'MATCH (n1)-[rel]-(n2) WHERE rel.str_id = "{id}" RETURN rel'
        elif id_type == 'quadruplet':
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
