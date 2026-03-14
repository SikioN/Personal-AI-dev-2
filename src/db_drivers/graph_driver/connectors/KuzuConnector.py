from typing import List, Dict, Union
import kuzu
import json
import os

from ....utils.errors import ReturnInfo
from ....utils.data_structs import Node, NodeCreator, NODES_TYPES_MAP, RelationCreator, QuadrupletCreator, Relation, RELATIONS_TYPES_MAP, NodeType, RelationType

from ..utils import GraphDBConnectionConfig, AbstractGraphDatabaseConnection
from ....utils import Quadruplet, NodeType

DEFAULT_KUZU_CONFIG = GraphDBConnectionConfig(
    params={'path': '../../kuzu_volume', 'buffer_pool_size': 1024**3,
            'schema': [
                "CREATE NODE TABLE IF NOT EXISTS object (id SERIAL, name STRING, prop MAP(STRING, STRING), str_id STRING, PRIMARY KEY(id));",
                "CREATE NODE TABLE IF NOT EXISTS hyper (id SERIAL, name STRING, prop MAP(STRING, STRING), str_id STRING, PRIMARY KEY(id));",
                "CREATE NODE TABLE IF NOT EXISTS episodic (id SERIAL, name STRING, prop MAP(STRING, STRING), str_id STRING, PRIMARY KEY(id));",
                "CREATE NODE TABLE IF NOT EXISTS time (id SERIAL, name STRING, prop MAP(STRING, STRING), str_id STRING, PRIMARY KEY(id));", # Added Time node
                "CREATE REL TABLE IF NOT EXISTS simple (FROM object TO object, name STRING, t_id STRING, str_id STRING, prop MAP(STRING, STRING));",
                "CREATE REL TABLE IF NOT EXISTS hyper_rel (FROM object TO hyper, name STRING, t_id STRING, str_id STRING, prop MAP(STRING, STRING));",
                "CREATE REL TABLE GROUP IF NOT EXISTS episodic_rel (FROM object TO episodic, FROM hyper TO episodic, name STRING, t_id STRING, str_id STRING, prop MAP(STRING, STRING));",
                # Ideally we need generic relations or mapping for time, but sticking to previous structure where Time is property or implicit
                # But Kuzu is strict schema.
            ],
            'table_type_map': {
                'relations': {'forward': {RelationType.simple.value: 'simple', RelationType.hyper.value: 'hyper_rel', RelationType.episodic.value: 'episodic_rel', RelationType.time.value: 'simple'},}, # Mapping time relation to simple for now
                'nodes': {'forward': {NodeType.object.value: 'object', NodeType.hyper.value: 'hyper', NodeType.episodic.value: 'episodic', NodeType.time.value: 'time'}}
            }
    }
)

class KuzuConnector(AbstractGraphDatabaseConnection):

    def __init__(self, config: GraphDBConnectionConfig = DEFAULT_KUZU_CONFIG) -> None:
        self.config = config

    def open_connection(self) -> ReturnInfo:
        load_path = self.config.params['path']

        if not os.path.exists(load_path):
            print(f"warning: graph-dump '{load_path}' doesn't exist. creating empty graph-store")

        self.db = kuzu.Database(load_path, buffer_pool_size=self.config.params['buffer_pool_size'])
        self.conn = kuzu.Connection(self.db)

        for schema_statement in self.config.params['schema']:
            try:
                self.conn.execute(schema_statement)
            except Exception as e:
                # Ignore if exists
                pass

        if self.config.need_to_clear:
            self.clear()

        self.config.params['table_type_map']['relations']['inverse'] = {v: k for k,v in self.config.params['table_type_map']['relations']['forward'].items()}
        self.config.params['table_type_map']['nodes']['inverse'] = {v: k for k,v in self.config.params['table_type_map']['nodes']['forward'].items()}

    def close_connection(self) -> ReturnInfo:
        # Kuzu connection doesn't strictly need close, but good practice if available
        # self.conn.close() 
        pass

    def __del__(self):
        self.close_connection()

    def is_open(self) -> bool:
        # Simpler check
        return hasattr(self, 'conn')

    def create_node_query(self, node: Node) -> tuple[str, dict]:
        props = dict(node.prop)
        props['name'] = node.name
        props['str_id'] = node.id
        
        node_t = self.config.params['table_type_map']['nodes']['forward'][node.type.value]
        
        # In Kuzu, MAP literals can take parameter values.
        # Format: CREATE (n:LABEL {name: $name, str_id: $str_id, prop: $prop})
        query = f"CREATE (n:{node_t} {{name: $name, str_id: $str_id, prop: $prop}});"
        return query, {"name": node.name, "str_id": node.id, "prop": props}


    def create_rel_query(self, quadruplet: Quadruplet) -> tuple[str, dict]:
        # Add time_name to properties for persistence
        time_name = quadruplet.time.name if quadruplet.time else "Unknown"
        
        # Merge properties
        combined_prop = dict(quadruplet.relation.prop)
        combined_prop['time_name'] = time_name
        
        s_type = self.config.params['table_type_map']['nodes']['forward'][quadruplet.start_node.type.value]
        o_type = self.config.params['table_type_map']['nodes']['forward'][quadruplet.end_node.type.value]
        rel_type = self.config.params['table_type_map']['relations']['forward'][quadruplet.relation.type.value]

        s_id = quadruplet.start_node.id
        o_id = quadruplet.end_node.id
        rel_name = quadruplet.relation.name
        t_id = quadruplet.id
        r_id = quadruplet.relation.id

        # Kuzu supports parameterized variables. Use $var syntax.
        query = (
            f"MATCH (s:{s_type}), (o:{o_type}) "
            f"WHERE s.str_id = $s_id AND o.str_id = $o_id "
            f"CREATE (s)-[rel:{rel_type} {{ "
            f"name: $rel_name, t_id: $t_id, str_id: $r_id, "
            f"prop: $prop "
            f"}}]->(o)"
        )
        params = {
            "s_id": s_id,
            "o_id": o_id,
            "rel_name": rel_name,
            "t_id": t_id,
            "r_id": r_id,
            "prop": combined_prop
        }
        return query, params

    def create(self, quadruplets: List[Quadruplet], creation_info: Dict[int,Dict[str,bool]] = dict()) -> ReturnInfo:
        # quadruplet-ids checking
        for quadruplet in quadruplets:
            if type(quadruplet.id) is not str:
                raise ValueError
        unique_ids = set(map(lambda quadruplet: quadruplet.id, quadruplets))
        if len(quadruplets) != len(unique_ids):
            raise ValueError

        for i, quadruplet in enumerate(quadruplets):
            cur_info = creation_info.get(i, None)
            if cur_info is None or cur_info['s_node']:
                insert_subj_query, p = self.create_node_query(quadruplet.start_node)
                self.conn.execute(insert_subj_query, p)
            if cur_info is None or cur_info['e_node']:
                insert_obj_query, p = self.create_node_query(quadruplet.end_node)
                self.conn.execute(insert_obj_query, p)
            
            # Time node
            if (cur_info is None or cur_info.get('t_node', False)) and quadruplet.time:
                 insert_time_query, p = self.create_node_query(quadruplet.time)
                 self.conn.execute(insert_time_query, p)

            insert_rel_query, p = self.create_rel_query(quadruplet)

            self.conn.execute(insert_rel_query, p)

    def read(self, ids: List[str]) -> List[Quadruplet]:
        for t_id in ids:
            if type(t_id) is not str:
                raise ValueError

        query = "MATCH (n1)-[rel]->(n2) WHERE rel.t_id IN $ids RETURN n1, rel, n2;"
        raw_output = self.conn.execute(query, {"ids": ids})
        quadruplets = self.parse_query_quadruplets_output(raw_output)
        return quadruplets

    def update(self, items: List[Quadruplet]) -> ReturnInfo:
        # TODO
        pass

    def delete(self, ids: List[str], delete_info: Dict[int,Dict[str,bool]] = dict()) -> None:
        for t_id in ids:
            if type(t_id) is not str:
                raise ValueError

        for i, t_id in enumerate(ids):
            self.conn.execute(
                'MATCH (s_node)-[rel]->(e_node) WHERE rel.t_id = $tid RETURN s_node.str_id AS sn_id, e_node.str_id AS en_id;',
                {"tid": t_id}
            )
            self.conn.execute(
                'MATCH (s_node)-[rel]->(e_node) WHERE rel.t_id = $tid DELETE rel;',
                {"tid": t_id}
            )


    def read_by_name(self, name: str, object_type: Union[RelationType, NodeType], object: str = 'relation') -> List[Union[Quadruplet, Node]]:
        if type(object_type) not in [RelationType, NodeType]:
            raise ValueError

        if type(name) is not str:
            raise ValueError

        if len(name) < 1:
            raise ValueError

        dump_name = json.dumps(name, ensure_ascii=False)
        if object == 'relation':
            rel_t = self.config.params['table_type_map']['relations']['forward'][object_type.value]

            query = f"MATCH (n1)-[rel:{rel_t}]->(n2) WHERE rel.name = $name RETURN n1,rel,n2;"
            output = self.conn.execute(query, {"name": name})

            formated_output = self.parse_query_quadruplets_output(output)
        elif object == 'node':
            node_t = self.config.params['table_type_map']['nodes']['forward'][object_type.value]

            query = f"MATCH (n:{node_t}) WHERE n.name = $name RETURN n;"
            output = self.conn.execute(query, {"name": name})

            formated_output = self.parse_query_nodes_output(output)
        else:
            raise ValueError

        return formated_output

    def parse_query_nodes_output(self, output: List[object]) -> List[Node]:
        formated_nodes = []
        output = output.get_as_df()
        if 'n' not in output: return []
        triplets_count = len(output['n'])
        for i in range(triplets_count):
            raw_node = output['n'][i]
            # _label is internal Kuzu field
            # Assuming we can map back
            
            # Simple fallback
            prop = dict(raw_node.get('prop', {}))
            
            # Infer type from label if possible, else defaulting might fail
            node = Node(id=raw_node.get('str_id'), name=str(raw_node.get('name')),
                         type=NodeType.object, prop=prop) # Type inference from label needed
            formated_nodes.append(node)

        return formated_nodes

    def parse_query_quadruplets_output(self, output: List[object]) -> List[Quadruplet]:
        formated_quadruplets = []
        output = output.get_as_df()
        if 'rel' not in output: return []
        triplets_count = len(output['rel'])

        for i in range(triplets_count):
            cur_n1, cur_rel, cur_n2 = output['n1'][i], output['rel'][i], output['n2'][i]

            node1 = Node(id=cur_n1.get('str_id'), name=str(cur_n1.get('name')),
                         type=NodeType.object, prop=dict(cur_n1.get('prop', {})))
            node2 = Node(id=cur_n2.get('str_id'), name=str(cur_n2.get('name')),
                         type=NodeType.object, prop=dict(cur_n2.get('prop', {})))

            relation = Relation(id=cur_rel.get('str_id'), name=str(cur_rel.get('name')),
                type=RelationType.simple, prop=dict(cur_rel.get('prop', {})))

            start_node, end_node = (node1, node2) # Simplified direction assumption for rebuild
            
            # Create Quadruplet
            # Time node missing in return?
            # 1.3: Reconstruct time from properties if available
            r_prop = dict(cur_rel.get('prop', {}))
            time_name = r_prop.get('time_name', 'Unknown')
            time_node = NodeCreator.create(NodeType.time, time_name, add_stringified_node=True)
            
            quadruplet = QuadrupletCreator.create(
                start_node=start_node, relation=relation, end_node=end_node,
                time=time_node, t_id=cur_rel.get('t_id')
            )
            formated_quadruplets.append(quadruplet)
        return formated_quadruplets

    def get_adjacent_nids(self, base_node_id: str,
            accepted_n_types: List[NodeType] = [NodeType.object, NodeType.hyper, NodeType.episodic]) -> List[str]:
        if type(base_node_id) is not str:
            raise ValueError

        str_accepted_nodes = ''.join(list(map(lambda tpe: f':{tpe.value}', accepted_n_types)))

        raw_nodes = self.conn.execute(
            f'MATCH (a)-[r]-(b{str_accepted_nodes}) WHERE a.str_id = $bid RETURN b;',
            {"bid": base_node_id}
        )
        formated_nodes = [node['str_id'] for node in raw_nodes.get_as_df()['b']]
        return formated_nodes

    def get_nodes_shared_ids(self, node1_id: str, node2_id: str, id_type: str = 'both') -> List[Dict[str, str]]:
        r1 = self.conn.execute(
            "MATCH (a)-[r]-(b) WHERE a.str_id = $id RETURN b.str_id AS bid",
            {"id": node1_id}
        ).get_as_df()
        r2 = self.conn.execute(
            "MATCH (a)-[r]-(b) WHERE a.str_id = $id RETURN b.str_id AS bid",
            {"id": node2_id}
        ).get_as_df()
        if r1.empty or r2.empty or 'bid' not in r1.columns:
            return []
        shared = set(r1['bid'].tolist()) & set(r2['bid'].tolist())
        return [{"str_id": sid} for sid in shared]

    def get_quadruplets_by_name(self, subj_names: List[str], obj_names: List[str], obj_type: str) -> List[Quadruplet]:
        all_quads = []
        rel_tables = list(self.config.params['table_type_map']['relations']['forward'].values())
        rel_tables = list(dict.fromkeys(rel_tables))
        for sn in subj_names:
            for on in obj_names:
                for rel_t in rel_tables:
                    try:
                        result = self.conn.execute(
                            f"MATCH (n1)-[rel:{rel_t}]->(n2) WHERE n1.name = $sn AND n2.name = $on RETURN n1, rel, n2;",
                            {"sn": sn, "on": on}
                        )
                        all_quads.extend(self.parse_query_quadruplets_output(result))
                    except Exception:
                        pass
        return all_quads

    def get_quadruplets(self, node1_id: str, node2_id: str) -> List[Quadruplet]:
        all_quads = []
        rel_tables = list(dict.fromkeys(
            self.config.params['table_type_map']['relations']['forward'].values()
        ))
        for rel_t in rel_tables:
            try:
                result = self.conn.execute(
                    f"MATCH (n1)-[rel:{rel_t}]->(n2) WHERE n1.str_id = $id1 AND n2.str_id = $id2 RETURN n1, rel, n2;",
                    {"id1": node1_id, "id2": node2_id}
                )
                all_quads.extend(self.parse_query_quadruplets_output(result))
            except Exception:
                pass
        return all_quads

    def get_node_type(self, id: str) -> NodeType:
        node_tables = self.config.params['table_type_map']['nodes']['forward']
        for node_type_val, tbl in node_tables.items():
            try:
                result = self.conn.execute(
                    f"MATCH (n:{tbl}) WHERE n.str_id = $id RETURN count(n) AS cnt;",
                    {"id": id}
                ).get_as_df()
                if not result.empty and result['cnt'][0] > 0:
                    return NodeType(node_type_val)
            except Exception:
                pass
        return NodeType.object
        

    def count_items(self, id: str = None, id_type: str = None) -> Union[Dict[str,int], int]:
        if id_type is None:
            try:
                node_tables = self.config.params.get('table_type_map', {}).get('nodes', {}).get('forward', {})
                obj_tbl = node_tables.get('object', 'object')
                n_df = self.conn.execute(f"MATCH (n:{obj_tbl}) RETURN count(n) as n_count").get_as_df()
                n_count = int(n_df['n_count'][0])
            except Exception:
                n_count = 0
            try:
                r_df = self.conn.execute("MATCH (a)-[rel]->(b) RETURN count(rel) as r_count").get_as_df()
                r_count = int(r_df['r_count'][0])
            except Exception:
                r_count = 0
            return {'quadruplets': r_count, 'nodes': n_count}
        return None

    def item_exist(self, id: str, id_type: str = 'quadruplet') -> bool:
        if id_type == 'quadruplet':
            result = self.conn.execute(
                "MATCH (n1)-[rel]->(n2) WHERE rel.t_id = $id RETURN count(rel) AS cnt;",
                {"id": id}
            ).get_as_df()
            return not result.empty and int(result['cnt'][0]) > 0
        if id_type == 'node':
            node_tables = self.config.params['table_type_map']['nodes']['forward'].values()
            for tbl in dict.fromkeys(node_tables):
                try:
                    r = self.conn.execute(
                        f"MATCH (n:{tbl}) WHERE n.str_id = $id RETURN count(n) AS cnt;",
                        {"id": id}
                    ).get_as_df()
                    if not r.empty and int(r['cnt'][0]) > 0:
                        return True
                except Exception:
                    pass
        return False
        
    def clear(self) -> None:
        self.conn.execute("MATCH (n1)-[rel]->(n2) DELETE rel;")
        self.conn.execute("MATCH (n) DELETE n;")
