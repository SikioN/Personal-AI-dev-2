from typing import List, Dict, Union
import kuzu
import json
import os

from ....utils.errors import ReturnInfo
from ....utils.data_structs import Node, NodeCreator, NODES_TYPES_MAP, RelationCreator, TripletCreator, Relation, RELATIONS_TYPES_MAP, NodeType, RelationType

from ..utils import GraphDBConnectionConfig, AbstractGraphDatabaseConnection
from ....utils import Triplet, NodeType

DEFAULT_KUZU_CONFIG = GraphDBConnectionConfig(
    params={'path': '../../kuzu_volume', 'buffer_pool_size': 1024**3,
            'schema': [
                "CREATE NODE TABLE IF NOT EXISTS object (id SERIAL, name STRING, prop MAP(STRING, STRING), str_id STRING, PRIMARY KEY(id));",
                "CREATE NODE TABLE IF NOT EXISTS hyper (id SERIAL, name STRING, prop MAP(STRING, STRING), str_id STRING, PRIMARY KEY(id));",
                "CREATE NODE TABLE IF NOT EXISTS episodic (id SERIAL, name STRING, prop MAP(STRING, STRING), str_id STRING, PRIMARY KEY(id));",
                "CREATE REL TABLE IF NOT EXISTS simple (FROM object TO object, name STRING, t_id STRING, str_id STRING, prop MAP(STRING, STRING));",
                "CREATE REL TABLE IF NOT EXISTS hyper_rel (FROM object TO hyper, name STRING, t_id STRING, str_id STRING, prop MAP(STRING, STRING));",
                "CREATE REL TABLE GROUP IF NOT EXISTS episodic_rel (FROM object TO episodic, FROM hyper TO episodic, name STRING, t_id STRING, str_id STRING, prop MAP(STRING, STRING));"
            ],
            'table_type_map': {
                'relations': {'forward': {RelationType.simple.value: 'simple', RelationType.hyper.value: 'hyper_rel', RelationType.episodic.value: 'episodic_rel'},},
                'nodes': {'forward': {NodeType.object.value: 'object', NodeType.hyper.value: 'hyper', NodeType.episodic.value: 'episodic'}}
            }
    }
)

class KuzuConnector(AbstractGraphDatabaseConnection):

    def __init__(self, config: GraphDBConnectionConfig = DEFAULT_KUZU_CONFIG) -> None:
        self.config = config

    def open_connection(self) -> ReturnInfo:
        load_path = f"{self.config.params['path']}/{self.config.db_info['db']}"

        if not os.path.exists(load_path):
            print(f"warning: graph-dump '{load_path}' doesnt exists. creating empty graph-store")

        self.db = kuzu.Database(load_path, buffer_pool_size=self.config.params['buffer_pool_size'])
        self.conn = kuzu.Connection(self.db)

        for schema_statement in self.config.params['schema']:
            self.conn.execute(schema_statement)

        if self.config.need_to_clear:
            self.clear()

        self.config.params['table_type_map']['relations']['inverse'] = {v: k for k,v in self.config.params['table_type_map']['relations']['forward'].items()}
        self.config.params['table_type_map']['nodes']['inverse'] = {v: k for k,v in self.config.params['table_type_map']['nodes']['forward'].items()}

    def close_connection(self) -> ReturnInfo:
        self.conn.close()
        self.db.close()

    def __del__(self):
        self.close_connection()

    def is_open(self) -> bool:
        return not self.conn.is_closed

    def create_node_query(self, node: Node) -> str:
        prop_keys, prop_values = [], []
        for prop_name, prop_value in node.prop.items():
            prop_keys.append(prop_name.replace(" ", "_"))
            prop_values.append(prop_value)

        fields = {}
        fields['name'] = json.dumps(node.name, ensure_ascii=False)
        fields['str_id'] = json.dumps(node.id, ensure_ascii=False)
        fields['prop'] = f"map({prop_keys},{prop_values})"

        str_fields = ", ".join([f"{k}: {v}" for k, v in fields.items()])

        node_t = self.config.params['table_type_map']['nodes']['forward'][node.type.value]
        query = f"CREATE (n:{node_t} " + "{" + str_fields + "});"
        return query


    def create_rel_query(self, triplet: Triplet) -> str:
        prop_keys, prop_values = [], []
        for prop_name, prop_value in triplet.relation.prop.items():
            prop_keys.append(prop_name.replace(' ', '_'))
            prop_values.append(prop_value)

        fields = {}
        fields['name'] = json.dumps(triplet.relation.name, ensure_ascii=False)
        fields['t_id'] = json.dumps(triplet.id, ensure_ascii=False)
        fields['str_id'] = json.dumps(triplet.relation.id, ensure_ascii=False)
        fields['prop'] = f"map({prop_keys},{prop_values})"
        str_fields = ", ".join([f"{k}: {v}" for k, v in fields.items()])

        subj_t, subj_id = triplet.start_node.type.value, triplet.start_node.id
        obj_t, obj_id = triplet.end_node.type.value, triplet.end_node.id
        rel_t = self.config.params['table_type_map']['relations']['forward'][triplet.relation.type.value]
        query = f'MATCH (subj:{subj_t}), (obj:{obj_t}) WHERE subj.str_id = "{subj_id}" AND obj.str_id = "{obj_id}" '
        query += f'CREATE (subj)-[rel:{rel_t} ' + '{' + str_fields + '}' + ']->(obj);'
        return query

    def create(self, triplets: List[Triplet], creation_info: Dict[int,Dict[str,bool]] = dict()) -> ReturnInfo:
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
                self.conn.execute(insert_subj_query)
            if cur_info is None or cur_info['e_node']:
                insert_obj_query = self.create_node_query(triplet.end_node)
                self.conn.execute(insert_obj_query)

            insert_rel_query = self.create_rel_query(triplet)

            self.conn.execute(insert_rel_query)

    def read(self, ids: List[str]) -> List[Triplet]:
        for t_id in ids:
            if type(t_id) is not str:
                raise ValueError

        str_ids = '['+', '.join(list(map(lambda id: f'"{id}"', ids))) + ']'
        query = f"MATCH (n1)-[rel]->(n2) WHERE rel.t_id IN {str_ids} RETURN n1, rel, n2;"
        raw_output = self.conn.execute(query)
        triplets = self.parse_query_triplets_output(raw_output)
        return triplets

    def update(self, items: List[Triplet]) -> ReturnInfo:
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


            output = self.conn.execute(f'MATCH (s_node)-[rel]->(e_node) WHERE rel.t_id = "{t_id}" RETURN s_node.str_id AS sn_id, e_node.str_id AS en_id;')
            self.conn.execute(f'MATCH (s_node)-[rel]->(e_node) WHERE rel.t_id = "{t_id}" DELETE rel;')

            output = output.get_as_df()
            if output.shape[0] < 1:
                continue

            assert output.shape[0] == 1


            if len(nodes_to_delete) > 0:
                where_statement = []
                for n_name in nodes_to_delete:
                    where_statement.append(f'n.str_id = "{output[n_name][0]}"')
                where_statement = ' or '.join(where_statement)
                self.conn.execute(f'MATCH (n) WHERE {where_statement} DELETE n')

    def read_by_name(self, name: str, object_type: Union[RelationType, NodeType], object: str = 'relation') -> List[Union[Triplet, Node]]:
        if type(object_type) not in [RelationType, NodeType]:
            raise ValueError

        if type(name) is not str:
            raise ValueError

        if len(name) < 1:
            raise ValueError

        dump_name = json.dumps(name, ensure_ascii=False)
        if object == 'relation':
            rel_t = self.config.params['table_type_map']['relations']['forward'][object_type.value]

            query = f"MATCH (n1)-[rel:{rel_t}]->(n2) WHERE rel.name = {dump_name} RETURN n1,rel,n2;"
            output = self.conn.execute(query)

            formated_output = self.parse_query_triplets_output(output)
        elif object == 'node':
            node_t = self.config.params['table_type_map']['nodes']['forward'][object_type.value]

            query = f"MATCH (n:{node_t}) WHERE n.name = {dump_name} RETURN n;"
            output = self.conn.execute(query)

            formated_output = self.parse_query_nodes_output(output)
        else:
            raise ValueError

        return formated_output

    def parse_query_nodes_output(self, output: List[object]) -> List[Node]:
        formated_nodes = []
        output = output.get_as_df()
        triplets_count = len(output['n'])
        for i in range(triplets_count):
            raw_node = output['n'][i]
            node_type = self.config.params['table_type_map']['nodes']['inverse'][raw_node['_label']]

            node = Node(id=raw_node['str_id'], name=str(raw_node['name']),
                         type=NODES_TYPES_MAP[node_type], prop=dict(raw_node['prop']))

            formated_nodes.append(node)

        return formated_nodes

    def parse_query_triplets_output(self, output: List[object]) -> List[Triplet]:
        formated_triplets = []
        output = output.get_as_df()
        triplets_count = len(output['rel'])

        for i in range(triplets_count):
            cur_n1, cur_rel, cur_n2 = output['n1'][i], output['rel'][i], output['n2'][i]

            # костыль
            raw_rel_type = cur_rel['_label'][:12]

            n1_type = self.config.params['table_type_map']['nodes']['inverse'][cur_n1['_label']]
            n2_type = self.config.params['table_type_map']['nodes']['inverse'][cur_n2['_label']]
            rel_type = self.config.params['table_type_map']['relations']['inverse'][raw_rel_type]

            node1 = Node(id=cur_n1['str_id'], name=str(cur_n1['name']),
                         type=NODES_TYPES_MAP[n1_type], prop=dict(cur_n1['prop']))
            node2 = Node(id=cur_n2['str_id'], name=str(cur_n2['name']),
                         type=NODES_TYPES_MAP[n2_type], prop=dict(cur_n2['prop']))

            relation = Relation(id=cur_rel['str_id'], name=str(cur_rel['name']),
                type=RELATIONS_TYPES_MAP[rel_type], prop=dict(cur_rel['prop']))

            start_node_id = cur_rel['_src']
            start_node, end_node = (node1, node2) if start_node_id == cur_n1['_id'] else (node2, node1)
            triplet = TripletCreator.create(
                start_node, relation, end_node, add_stringified_triplet=False, t_id=cur_rel['t_id'])
            formated_triplets.append(triplet)
        return formated_triplets

    def get_adjecent_nids(self, base_node_id: str,
            accepted_n_types: List[NodeType] = [NodeType.object, NodeType.hyper, NodeType.episodic]) -> List[str]:
        if type(base_node_id) is not str:
            raise ValueError

        str_accepted_nodes = ''.join(list(map(lambda tpe: f':{tpe.value}', accepted_n_types)))

        raw_nodes = self.conn.execute(
            f'MATCH (a)-[r]-(b{str_accepted_nodes}) WHERE a.str_id = "{base_node_id}" RETURN b;')
        formated_nodes = [node['str_id'] for node in raw_nodes.get_as_df()['b']]
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

        raw_rels = self.conn.execute(
            f'MATCH (a)-[r]-(b) WHERE a.str_id = "{node1_id}" AND b.str_id = "{node2_id}" RETURN {str_return_info};')

        rinfo_df = raw_rels.get_as_df()
        formated_info = []
        for idx in range(rinfo_df.shape[0]):
            tmp_info = dict()
            if id_type in ['both', 'triplet']:
                tmp_info['t_id'] = rinfo_df['t_id'][idx]

            if id_type in ['both', 'relation']:
                tmp_info['r_id'] = rinfo_df['r_id'][idx]

            formated_info.append(tmp_info)

        return formated_info

    def get_triplets_by_name(self, subj_names: List[str], obj_names: List[str], obj_type: str) -> List[Triplet]:
        formatted_triplets = []
        if subj_names:
            for subj_name in subj_names:
                output = self.conn.execute(
                    f'MATCH (n1:object)-[rel]-(n2:{obj_type}) WHERE LOWER(n1.name) = LOWER("{subj_name}") RETURN n1, rel, n2;')
                formatted_triplets += self.parse_query_triplets_output(output)
        elif obj_names:
            for obj_name in obj_names:
                output = self.conn.execute(
                    f'MATCH (n1:object)-[rel]-(n2:{obj_type}) WHERE LOWER(n2.name) = LOWER("{obj_name}") RETURN n1, rel, n2;')
                formatted_triplets += self.parse_query_triplets_output(output)
        else:
            output = self.conn.execute(
                f'MATCH (n1:object)-[rel]-(n2:{obj_type}) RETURN n1, rel, n2;')
            formatted_triplets += self.parse_query_triplets_output(output)
        return formatted_triplets

    def get_triplets(self, node1_id: str, node2_id: str) -> List[Triplet]:
        if (type(node1_id) is not str) or (type(node2_id) is not str):
            raise ValueError
        if (not self.item_exist(node1_id, id_type='node')) or (not self.item_exist(node2_id, id_type='node')):
            raise ValueError

        output = self.conn.execute(
            f'MATCH (n1)-[rel]-(n2) WHERE n1.str_id = "{node1_id}" AND n2.str_id = "{node2_id}" RETURN n1, rel, n2;')

        formated_triplets = self.parse_query_triplets_output(output)
        unique_triplets = {triplet.id: triplet for triplet in formated_triplets}
        return list(unique_triplets.values())

    def get_node_type(self, id: str) -> NodeType:
        # TODO
        raise NotImplementedError
        

    def count_items(self, id: str = None, id_type: str = None) -> Union[Dict[str,int], int]:
        if id_type is None:
            n_output = self.conn.execute("MATCH (a) RETURN count(a) as n_count").get_as_df()['n_count'][0]
            r_output = self.conn.execute("MATCH (a)-[rel]->(b) RETURN count(rel) as r_count").get_as_df()['r_count'][0]
            result = {'triplets': int(r_output), 'nodes': int(n_output)}

        elif id_type == 'node':
            n_output = self.conn.execute(f'MATCH (a) WHERE a.str_id = "{id}" RETURN COUNT(a) as n_count').get_as_df()['n_count'][0]
            result = int(n_output)

        elif id_type == 'relation':
            r_output = self.conn.execute(f'MATCH (a)-[rel]->(b) WHERE rel.str_id = "{id}" RETURN COUNT(rel) as r_count').get_as_df()['r_count'][0]
            result = int(r_output)

        elif id_type == 'triplet':
            r_output = self.conn.execute(f'MATCH (a)-[rel]->(b) WHERE rel.t_id = "{id}" RETURN COUNT(rel) as r_count').get_as_df()['r_count'][0]
            result = int(r_output)

        else:
            raise ValueError

        return result

    def item_exist(self, id: str, id_type: str='triplet') -> bool:
        if type(id) is not str:
            raise ValueError

        if id_type == 'node':
            query = f'MATCH (n) WHERE n.str_id = "{id}" RETURN n;'
        elif id_type == 'relation':
            query = f'MATCH (n1)-[rel]-(n2) WHERE rel.str_id = "{id}" RETURN rel;'
        elif id_type == 'triplet':
            query = f'MATCH (n1)-[rel]-(n2) WHERE rel.t_id = "{id}" RETURN rel;'
        else:
            raise ValueError

        output = self.conn.execute(query)
        return output.get_as_df().shape[0] > 0

    def clear(self) -> None:
        self.conn.execute("MATCH (n1)-[rel]->(n2) DELETE rel;")
        self.conn.execute("MATCH (n) DELETE n;")
