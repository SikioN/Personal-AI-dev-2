from neo4j import GraphDatabase
from typing import List, Dict, Union, Tuple
import json
import re as _re

from ..utils import GraphDBConnectionConfig, AbstractGraphDatabaseConnection
from ....utils.data_structs import (
    Quadruplet, Node, Relation, QuadrupletCreator, NodeCreator, NodeType,
    RelationCreator, RelationType, NODES_TYPES_MAP, RELATIONS_TYPES_MAP,
)

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

        try:
            # 3.2: validate db name to prevent Cypher injection via config value
            db_name = self.config.db_info["db"]
            if not _re.match(r'^[A-Za-z0-9_]+$', db_name):
                raise ValueError(f"Invalid database name: {db_name!r} (only [A-Za-z0-9_] allowed)")
            self.execute_query(
                f'CREATE DATABASE {db_name} IF NOT EXISTS', db_flag=False)
        except Exception as e:
            print(f"Warning: Could not create database: {e}")

        # Scalar indexes
        self.execute_query("CREATE INDEX name_object_node IF NOT EXISTS FOR (n:object) ON n.name")
        self.execute_query("CREATE INDEX name_hyper_node IF NOT EXISTS FOR (n:hyper) ON n.name")
        self.execute_query("CREATE INDEX name_episodic_node IF NOT EXISTS FOR (n:episodic) ON n.name")
        self.execute_query("CREATE INDEX name_time_node IF NOT EXISTS FOR (n:time) ON n.name")

        self.execute_query("CREATE INDEX strid_object_node IF NOT EXISTS FOR (n:object) ON n.str_id")
        self.execute_query("CREATE INDEX strid_hyper_node IF NOT EXISTS FOR (n:hyper) ON n.str_id")
        self.execute_query("CREATE INDEX strid_episodic_node IF NOT EXISTS FOR (n:episodic) ON n.str_id")
        self.execute_query("CREATE INDEX strid_time_node IF NOT EXISTS FOR (n:time) ON n.str_id")

        self.execute_query("CREATE INDEX strid_simple_relation IF NOT EXISTS FOR ()-[r:simple]->() ON r.str_id")
        self.execute_query("CREATE INDEX strid_hyper_relation IF NOT EXISTS FOR ()-[r:hyper]->() ON r.str_id")
        self.execute_query("CREATE INDEX strid_episodic_relation IF NOT EXISTS FOR ()-[r:episodic]->() ON r.str_id")
        self.execute_query("CREATE INDEX strid_time_relation IF NOT EXISTS FOR ()-[r:time]->() ON r.str_id")

        self.execute_query("CREATE INDEX tid_simple_relation IF NOT EXISTS FOR ()-[r:simple]->() ON r.t_id")
        self.execute_query("CREATE INDEX tid_hyper_relation IF NOT EXISTS FOR ()-[r:hyper]->() ON r.t_id")
        self.execute_query("CREATE INDEX tid_episodic_relation IF NOT EXISTS FOR ()-[r:episodic]->() ON r.t_id")
        self.execute_query("CREATE INDEX tid_time_relation IF NOT EXISTS FOR ()-[r:time]->() ON r.t_id")

        self.execute_query("CREATE INDEX name_simple_relation IF NOT EXISTS FOR ()-[r:simple]->() ON r.name")
        self.execute_query("CREATE INDEX name_hyper_relation IF NOT EXISTS FOR ()-[r:hyper]->() ON r.name")
        self.execute_query("CREATE INDEX name_episodic_relation IF NOT EXISTS FOR ()-[r:episodic]->() ON r.name")
        self.execute_query("CREATE INDEX name_time_relation IF NOT EXISTS FOR ()-[r:time]->() ON r.name")

        # Fulltext index on name + aliases (for alias search)
        self.execute_query(
            "CREATE FULLTEXT INDEX entity_name_aliases IF NOT EXISTS "
            "FOR (n:object|hyper|episodic) ON EACH [n.name, n.aliases]"
        )

        if self.config.need_to_clear:
            self.clear()

    def is_open(self) -> None:
        pass

    def close_connection(self) -> None:
        if self.driver is not None:
            self.driver.close()

    def __del__(self):
        self.close_connection()

    # ------------------------------------------------------------------
    # Query builders — parameterized (no f-string injection)
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_label(label: str) -> str:
        """3.3: whitelist-validate node/relation type labels before interpolation."""
        if not _re.match(r'^[A-Za-z0-9_]+$', label):
            raise ValueError(f"Invalid node/relation label: {label!r}")
        return label

    def create_node_query(self, node: Node) -> Tuple[str, dict]:
        """Returns (cypher_query, params_dict). Uses MERGE + parameterized props."""
        props = {
            k: v for k, v in node.prop.items()
            if k not in ('str_id', 'type', 'name')
        }
        props['str_id'] = node.id
        props['name'] = node.name

        node_label = self._validate_label(node.type.value)
        alias = getattr(node, 'alias_to_add', None)
        if alias and alias != node.name:
            query = (
                f"MERGE (n:{node_label} {{str_id: $str_id}}) "
                "ON CREATE SET n += $props, n.aliases = [$alias] "
                "ON MATCH SET n.aliases = "
                "  [x IN COALESCE(n.aliases, []) WHERE x <> $alias] + [$alias] "
                "RETURN elementId(n) as node_id"
            )
            return query, {"str_id": node.id, "props": props, "alias": alias}
        else:
            query = (
                f"MERGE (n:{node_label} {{str_id: $str_id}}) "
                "ON CREATE SET n += $props "
                "RETURN elementId(n) as node_id"
            )
            return query, {"str_id": node.id, "props": props}

    def create_rel_query(self, quadruplet: Quadruplet) -> Tuple[str, dict]:
        rel_props = {
            k.replace(' ', '_'): v
            for k, v in quadruplet.relation.prop.items()
        }
        rel_props['name'] = quadruplet.relation.name
        rel_props['t_id'] = quadruplet.id
        rel_props['str_id'] = quadruplet.relation.id
        if quadruplet.time:
            rel_props['time_node_id'] = quadruplet.time.id

        # 3.3: validate labels before interpolating into Cypher
        subj_t = self._validate_label(quadruplet.start_node.type.value)
        obj_t = self._validate_label(quadruplet.end_node.type.value)
        rel_t = self._validate_label(quadruplet.relation.type.value)

        query = (
            f"MATCH (subj:{subj_t}), (obj:{obj_t}) "
            "WHERE subj.str_id = $subj_id AND obj.str_id = $obj_id "
            f"CREATE (subj)-[rel:{rel_t} $rel_props]->(obj) "
            "RETURN elementId(rel) as rel_id"
        )
        return query, {
            "subj_id": quadruplet.start_node.id,
            "obj_id": quadruplet.end_node.id,
            "rel_props": rel_props,
        }

    def create(self, quadruplets: List[Quadruplet], creation_info: Dict[int, Dict[str, bool]] = dict()) -> None:
        for quadruplet in quadruplets:
            if type(quadruplet.id) is not str:
                raise ValueError
        unique_ids = set(q.id for q in quadruplets)
        if len(quadruplets) != len(unique_ids):
            raise ValueError

        for i, quadruplet in enumerate(quadruplets):
            cur_info = creation_info.get(i, None)

            if cur_info is None or cur_info['s_node']:
                q, p = self.create_node_query(quadruplet.start_node)
                self.execute_query(q, params=p)

            if cur_info is None or cur_info['e_node']:
                q, p = self.create_node_query(quadruplet.end_node)
                self.execute_query(q, params=p)

            if cur_info is None or cur_info.get('t_node', False):
                if quadruplet.time:
                    q, p = self.create_node_query(quadruplet.time)
                    self.execute_query(q, params=p)

            q, p = self.create_rel_query(quadruplet)
            self.execute_query(q, params=p)

    def read(self, ids: List[str]) -> List[Quadruplet]:
        for t_id in ids:
            if type(t_id) is not str:
                raise ValueError

        query = (
            "MATCH (n1)-[rel]->(n2) WHERE any(id IN $ids WHERE rel.t_id = id) "
            "OPTIONAL MATCH (t:time) WHERE t.str_id = rel.time_node_id "
            "RETURN n1, rel, n2, t"
        )
        raw_output = self.execute_query(query, params={"ids": ids})
        return self.parse_query_triplets_output(raw_output)

    def update(self, items: List[Quadruplet]) -> None:
        pass

    def delete(self, ids: List[str], delete_info: Dict[int, Dict[str, bool]] = dict()) -> None:
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

            output = self.execute_query(
                'MATCH (s_node)-[rel]->(e_node) WHERE rel.t_id = $t_id '
                'DELETE rel RETURN elementId(s_node) as sn_id, elementId(e_node) as en_id',
                params={"t_id": t_id}
            )
            if not output:
                continue

            assert len(output) == 1
            if nodes_to_delete:
                for n_name in nodes_to_delete:
                    self.execute_query(
                        'MATCH (n) WHERE elementId(n) = $eid DELETE n',
                        params={"eid": output[0][n_name]}
                    )

    def read_by_name(self, name: str, object_type: Union[RelationType, NodeType],
                     object: str = 'relation') -> List[Union[Quadruplet, Node]]:
        if type(object_type) not in [RelationType, NodeType]:
            raise ValueError
        if type(name) is not str or len(name) < 1:
            raise ValueError

        if object == 'relation':
            output = self.execute_query(
                f'MATCH (n1)-[rel:{object_type.value}]->(n2) WHERE rel.name = $name RETURN n1,rel,n2',
                params={"name": name}
            )
            return self.parse_query_triplets_output(output)
        elif object == 'node':
            output = self.execute_query(
                f'MATCH (n:{object_type.value}) WHERE n.name = $name RETURN n',
                params={"name": name}
            )
            return self.parse_query_nodes_output(output)
        else:
            raise ValueError

    def execute_query(self, query: str, db_flag: bool = True, params: dict = None) -> List[object]:
        assert self.driver is not None, "Driver not initialized!"
        session = None
        response = None
        try:
            session = (self.driver.session(database=self.config.db_info['db'])
                       if db_flag else self.driver.session())
            response = list(session.run(query, **(params or {})))
        except Exception as e:
            print("Query failed:", e)
            print("Error query:", query)
        finally:
            if session is not None:
                session.close()
        return response

    def get_adjecent_nids(self, base_node_id: str,
                          accepted_n_types: List[NodeType] = None) -> List[str]:
        if accepted_n_types is None:
            accepted_n_types = [NodeType.object, NodeType.hyper, NodeType.episodic]
        if type(base_node_id) is not str:
            raise ValueError

        type_labels = [t.value for t in accepted_n_types]
        raw_nodes = self.execute_query(
            'MATCH (a)-[r]-(b) WHERE a.str_id = $nid '
            'AND any(lbl IN $lbls WHERE lbl IN labels(b)) RETURN b',
            params={"nid": base_node_id, "lbls": type_labels}
        )
        return [node['b']['str_id'] for node in raw_nodes]

    def get_nodes_shared_ids(self, node1_id: str, node2_id: str, id_type: str = 'both') -> List[Dict[str, str]]:
        if type(node1_id) is not str or type(node2_id) is not str:
            raise ValueError(node1_id, node2_id)

        if id_type == 'quadruplet':
            ret = 'r.t_id as t_id'
        elif id_type == 'relation':
            ret = 'r.str_id as r_id'
        elif id_type == 'both':
            ret = 'r.t_id as t_id, r.str_id as r_id'
        else:
            raise ValueError(id_type)

        raw_rels = self.execute_query(
            f'MATCH (a)-[r]-(b) WHERE a.str_id = $n1 AND b.str_id = $n2 RETURN {ret}',
            params={"n1": node1_id, "n2": node2_id}
        )
        formated_info = []
        for raw_rel in raw_rels:
            tmp_info = {}
            if id_type in ['both', 'quadruplet']:
                tmp_info['t_id'] = raw_rel['t_id']
            if id_type in ['both', 'relation']:
                tmp_info['r_id'] = raw_rel['r_id']
            formated_info.append(tmp_info)
        return formated_info

    def _load_dumped_dict(self, raw_dict: dict) -> Dict:
        loaded_dict = {}
        for k, v in raw_dict.items():
            try:
                loaded_dict[k] = json.loads(v)
            except (json.decoder.JSONDecodeError, TypeError):
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
                start_node, end_node = node1, node2
            elif start_node_id == raw_row['n2'].element_id:
                start_node, end_node = node2, node1
            else:
                raise ValueError

            time_node = None
            if 't' in raw_row and raw_row['t']:
                t_dict = dict(raw_row['t'])
                time_node = NodeCreator.create(
                    n_type=NodeType.time,
                    name=t_dict.get('name', 'Unknown'),
                    prop=t_dict, add_stringified_node=True)

            time_node_id = rel_dict.get('time_node_id')
            if time_node is None and time_node_id:
                tid_clean = time_node_id.replace('"', '')
                t_res = self.execute_query(
                    'MATCH (t:time) WHERE t.str_id = $tid OR t.str_id = $tid_clean RETURN t LIMIT 1',
                    params={"tid": time_node_id, "tid_clean": tid_clean}
                )
                if t_res:
                    t_dict = dict(t_res[0]['t'])
                    time_node = NodeCreator.create(
                        n_type=NodeType.time,
                        name=t_dict.get('name', 'Unknown'),
                        prop=t_dict, add_stringified_node=True)

            if time_node is None:
                time_node = NodeCreator.create(NodeType.time, "Unknown", add_stringified_node=True)

            quadruplet = QuadrupletCreator.create(
                start_node, relation, end_node, time=time_node, add_stringified_quadruplet=True)
            formated_quadruplets.append(quadruplet)
        return formated_quadruplets

    def get_quadruplets(self, node1_id: str, node2_id: str) -> List[Quadruplet]:
        if type(node1_id) is not str or type(node2_id) is not str:
            raise ValueError
        if not self.item_exist(node1_id, id_type='node') or not self.item_exist(node2_id, id_type='node'):
            raise ValueError

        query = (
            'MATCH (n1)-[rel]-(n2) WHERE n1.str_id = $n1 AND n2.str_id = $n2 '
            'OPTIONAL MATCH (t:time) WHERE t.str_id = rel.time_node_id '
            'RETURN n1, rel, n2, t'
        )
        output = self.execute_query(query, params={"n1": node1_id, "n2": node2_id})
        return self.parse_query_triplets_output(output)

    def get_quadruplets_by_name(self, subj_names: List[str], obj_names: List[str],
                                obj_type: str) -> List[Quadruplet]:
        formated_quadruplets = []
        if subj_names:
            for subj_name in subj_names:
                output = self.execute_query(
                    f'MATCH (n1:object)-[rel]-(n2:{obj_type}) WHERE toLower(n1.name) = toLower($name) '
                    'OPTIONAL MATCH (t:time) WHERE t.str_id = rel.time_node_id RETURN n1, rel, n2, t',
                    params={"name": subj_name}
                )
                formated_quadruplets += self.parse_query_triplets_output(output)
        elif obj_names:
            for obj_name in obj_names:
                output = self.execute_query(
                    f'MATCH (n1:object)-[rel]-(n2:{obj_type}) WHERE toLower(n2.name) = toLower($name) '
                    'OPTIONAL MATCH (t:time) WHERE t.str_id = rel.time_node_id RETURN n1, rel, n2, t',
                    params={"name": obj_name}
                )
                formated_quadruplets += self.parse_query_triplets_output(output)
        else:
            output = self.execute_query(
                f'MATCH (n1:object)-[rel]-(n2:{obj_type}) '
                'OPTIONAL MATCH (t:time) WHERE t.str_id = rel.time_node_id RETURN n1, rel, n2, t'
            )
            formated_quadruplets += self.parse_query_triplets_output(output)
        return formated_quadruplets

    def count_items(self, id: str = None, id_type: str = None) -> Union[Dict[str, int], int]:
        if id_type is None:
            n_raw = self.execute_query("MATCH (a) RETURN count(a) as n_count")
            r_raw = self.execute_query("MATCH (a)-[rel]->(b) RETURN count(rel) as r_count")
            n_count = n_raw[0]['n_count'] if n_raw else 0
            r_count = r_raw[0]['r_count'] if r_raw else 0
            return {'quadruplets': r_count, 'nodes': n_count}
        elif id_type == 'node':
            n_raw = self.execute_query(
                'MATCH (a) WHERE a.str_id = $id RETURN COUNT(a) as n_count', params={"id": id})
            return n_raw[0]['n_count'] if n_raw else 0
        elif id_type == 'relation':
            r_raw = self.execute_query(
                'MATCH (a)-[rel]->(b) WHERE rel.str_id = $id RETURN COUNT(rel) as r_count', params={"id": id})
            return r_raw[0]['r_count'] if r_raw else 0
        elif id_type == 'quadruplet':
            r_raw = self.execute_query(
                'MATCH (a)-[rel]->(b) WHERE rel.t_id = $id RETURN COUNT(rel) as r_count', params={"id": id})
            return r_raw[0]['r_count'] if r_raw else 0
        else:
            raise ValueError

    def item_exist(self, id: str, id_type: str = 'quadruplet') -> bool:
        if type(id) is not str:
            raise ValueError
        if id_type == 'node':
            query = 'MATCH (n) WHERE n.str_id = $id RETURN n'
        elif id_type == 'relation':
            query = 'MATCH (n1)-[rel]-(n2) WHERE rel.str_id = $id RETURN rel'
        elif id_type == 'quadruplet':
            query = 'MATCH (n1)-[rel]-(n2) WHERE rel.t_id = $id RETURN rel'
        else:
            raise ValueError
        output = self.execute_query(query, params={"id": id})
        return bool(output)

    def get_node_type(self, id: str) -> NodeType:
        if not self.item_exist(id, id_type="node"):
            raise ValueError
        raw_output = self.execute_query(
            'MATCH (n) WHERE n.str_id = $id RETURN n', params={"id": id})
        return self.parse_query_nodes_output(raw_output)[0].type

    def clear(self) -> None:
        self.execute_query("MATCH (n)-[rel]->() DELETE n,rel")
        self.execute_query("MATCH (n) DELETE n")
