from typing import List, Dict, Tuple
from neo4j import GraphDatabase
import json

from ..utils import AbstractTreeDatabaseConnection, TreeDBConnectionConfig, \
    TreeNode, TreeNodeType, TreeIdType, TREENODES_TYPES_MAP

DEFAULT_NEO4JTREE_CONFIG = TreeDBConnectionConfig(
    host="localhost", port="7688", db_info={'db': 'testingtree', 'table': 'testingtree'},
    params={'user': "neo4j", 'pwd': 'password'}, need_to_clear=False)

class Neo4jTreeConnector(AbstractTreeDatabaseConnection):

    def __init__(self, config: TreeDBConnectionConfig = DEFAULT_NEO4JTREE_CONFIG):
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
        self.execute_query("CREATE INDEX extid_leaf_node IF NOT EXISTS FOR (n:leaf) ON n.external_id")
        self.execute_query("CREATE INDEX strid_leaf_node IF NOT EXISTS FOR (n:leaf) ON n.str_id")
        self.execute_query("CREATE INDEX extid_summ_node IF NOT EXISTS FOR (n:summarized) ON n.external_id")
        self.execute_query("CREATE INDEX extid_root_node IF NOT EXISTS FOR (n:root) ON n.external_id")

        # Добавляем корневую вершину
        if self.count_items()['root'] < 1:
            self.execute_query("CREATE (n:root {" + 'external_id: "' + self.root_node_id + '", depth: 0});')

        if self.config.need_to_clear:
            self.clear()

    def is_open(self) -> bool:
        # TODO
        pass

    def close_connection(self) -> None:
        if self.driver is not None:
            self.driver.close()

    def check_consistency(self) -> None:
        # У всех leaf-вершин есть str_id-поле
        leafs_wo_strid = self.execute_query("MATCH (n:leaf) WHERE n.str_id IS NULL RETURN COUNT(n) as badleafs")[0]['badleafs']
        assert leafs_wo_strid < 1

        # количество компонент связности равно 1
        #components_amount = self.execute_query(f"CALL gds.wcc.stats('{self.config.db_info['db']}') YIELD componentCount")[0]['componentCount']
        #assert components_amount < 2

        # нет summarized-вершин без детей
        summarized_wo_childs = self.execute_query("MATCH (parent:summarized) WHERE COUNT { (parent)-[rel]->() } < 1 RETURN parent")
        assert len(summarized_wo_childs) < 1
        # нет leaf-вершин c детьми
        leafs_with_childs = self.execute_query("MATCH (parent:leaf) WHERE COUNT { (parent)-[rel]->() } > 1 RETURN parent")
        assert len(leafs_with_childs) < 1

        nodes_count = self.count_items()
        # есть 1 root-вершина
        assert nodes_count['root'] < 2 and nodes_count['root'] > 0
        # summarized-вершин <= leaf-вершин
        assert nodes_count['summarized'] <= nodes_count['leaf']

    def create(self, parent_id: str, new_node: TreeNode) -> None:
        # Подвешиваем новую вершину к уже существующей
        # parent_id должен быть валидным и сущесутвовать
        # У new_node должен быть валидный id, type, text, не должно храниться зарезервированных полей
        # если вершина с таким id уже существует, то вызыватеся исключение

        if type(parent_id) is not str:
            raise ValueError
        if not self.is_node_valid(new_node):
            raise ValueError
        if not self.item_exist(parent_id, TreeIdType.external):
            raise ValueError
        if self.item_exist(new_node.id, TreeIdType.external):
            raise ValueError

        # добавляем новую вершину
        query_props = {}
        for p_name, p_value in new_node.props.items():
            p_name, p_value = p_name.replace(" ", "_"), json.dumps(p_value, ensure_ascii=False)
            query_props[p_name] = p_value
        query_props['external_id'] = json.dumps(new_node.id, ensure_ascii=False)
        query_props['text'] = json.dumps(new_node.text, ensure_ascii=False)
        str_props = ", ".join([f"{k}: {v}" for k, v in query_props.items()])
        query = f"CREATE (n:{new_node.type.value} " + "{" + str_props + "}) RETURN elementId(n) as node_id"
        self.execute_query(query)

        # добавляем связь между parent- и её новой child-вершиной
        query = f'MATCH (parent), (child) WHERE parent.external_id = "{parent_id}" AND child.external_id = "{new_node.id}" '
        query += f'CREATE (parent)-[rel:relation]->(child) '
        query += 'RETURN elementId(rel) as rel_id'
        self.execute_query(query)

    def read(self, ids: List[str], ids_type: TreeIdType = TreeIdType.external) -> List[TreeNode]:
        if type(ids_type) is not TreeIdType:
            raise ValueError
        for id in ids:
            if type(id) is not str:
                raise ValueError

        formated_ids = '['+', '.join(list(map(lambda id: f'"{id}"', ids))) + ']'
        query = f"MATCH (n) WHERE any(id IN {formated_ids} WHERE n.{ids_type.value} = id) RETURN n"
        raw_nodes = self.execute_query(query)

        # Приводим информацию о полученных вершинах к нужному формату
        formated_nodes = self.formate_nodes_output(raw_nodes)

        return formated_nodes

    def update(self, items: List[TreeNode]) -> None:

        new_items_map = dict()
        for item in items:
            if not self.is_node_valid(item):
                raise ValueError
            if not self.item_exist(item.id):
                raise ValueError
            new_items_map[item.id] = item

        old_items = self.read(list(new_items_map.keys()))
        for cur_old_item in old_items:
            cur_new_item = new_items_map[cur_old_item.id]

            # Получаем набор полей, которые нужно удалить из текущей вершины
            props_to_delete = set(set(cur_old_item.props.keys())).difference(set(cur_new_item.props.keys()))

            # Формируем строковое представление полей для удаления из и добавления в текущую вершину
            formated_delete_props = list(map(lambda p_name: f"n.{p_name} = null", props_to_delete))
            formated_set_props = []
            for k,v in cur_new_item.props.items():
                formated_set_props.append(f"n.{k} = {json.dumps(v, ensure_ascii=False)}")
            formated_set_props.append(f"n.text = {json.dumps(cur_new_item.text, ensure_ascii=False)}")
            formated_set_props.append(f"n:{cur_new_item.type.value}")

            formated_props = ', '.join(formated_delete_props + formated_set_props)

            # Модифицируем содержание полей в текущей вершине
            query = "MATCH (n {external_id: '" + cur_old_item.id + "'}) SET " + formated_props + ";"
            self.execute_query(query)

            # Меняем тип вершины, если необходимо
            if cur_new_item.type != cur_old_item.type:
                query = "MATCH (n {external_id: '" + cur_old_item.id + "'})" + f"REMOVE n:{cur_old_item.type.value} SET n:{cur_new_item.type.value};"
                self.execute_query(query)

    def delete(self, ids: List[str], ids_type: TreeIdType = TreeIdType.external) -> None:
        if type(ids_type) is not TreeIdType:
            raise ValueError
        for id in ids:
            if type(id) is not str:
                raise ValueError
            # Проверка: у удаляемой вершины не должно быть детей
            if self.item_exist(id, id_type=ids_type):
                cur_node = self.read([id], ids_type=ids_type)[0]
                childs_amount = len(self.get_child_nodes(cur_node.id))
                if childs_amount > 0:
                    raise ValueError

        for id in ids:
            self.execute_query(f'MATCH (grand_p)-[rel]->(parent) WHERE parent.{ids_type.value} = "{id}" DELETE rel;')
            self.execute_query(f'MATCH (n) WHERE n.{ids_type.value} = "{id}" DELETE n;')


    def get_leaf_descendants(self, id: str, id_type: str=TreeIdType.external) -> List[TreeNode]:
        if type(id) is not str:
            raise ValueError
        if type(id_type) is not TreeIdType:
            raise ValueError

        raw_output = self.execute_query(f'MATCH (parent)-[:relation*0..]->(n:leaf) WHERE parent.{id_type.value} = "{id}" RETURN n')
        leaf_nodes = self.formate_nodes_output(raw_output)
        return leaf_nodes

    def count_items(self) -> Dict[str, int]:

        leafs_amount = self.execute_query("MATCH (n:leaf) return COUNT(n) as l_amount")[0]['l_amount']
        summarized_amount = self.execute_query("MATCH (n:summarized) return COUNT(n) as s_amount")[0]['s_amount']
        root_amount = self.execute_query("MATCH (n:root) return COUNT(n) as r_amount")[0]['r_amount']

        return {'leaf': leafs_amount, 'summarized': summarized_amount, 'root': root_amount}

    def item_exist(self, id: str, id_type: str = TreeIdType.external) -> bool:
        if type(id) is not str:
            raise ValueError

        if id_type == TreeIdType.external:
            query = f'MATCH (n) WHERE n.external_id = "{id}" RETURN n'
        elif id_type == TreeIdType.str:
            query = f'MATCH (n) WHERE n.str_id = "{id}" RETURN n'
        else:
            raise ValueError

        output = self.execute_query(query)
        return len(output) > 0

    def get_child_nodes(self, parent_id: str) -> List[TreeNode]:
        if type(parent_id) is not str:
            raise ValueError
        if not self.item_exist(parent_id, id_type= TreeIdType.external):
            raise ValueError

        raw_nodes = self.execute_query(f'MATCH (parent)-[rel]->(n) WHERE parent.external_id = "{parent_id}" RETURN n')
        formated_nodes = self.formate_nodes_output(raw_nodes)
        return formated_nodes

    def get_tree_maxdepth(self) -> int:
        return self.execute_query("MATCH (n) RETURN MAX(n.depth) as max_depth")[0]['max_depth']

    def clear(self) -> None:
        self.execute_query("MATCH (n)-[rel]->() DELETE n,rel")
        self.execute_query("MATCH (n) DELETE n")
        # Добавляем корневую вершину
        self.execute_query("CREATE (n:root {" + 'external_id: "' + self.root_node_id + '", depth: 0});')


    def execute_query(self, query: str, db_flag: bool = True) -> List[object]:
        """_summary_

        :param query: _description_
        :type query: str
        :param db_flag: _description_, defaults to True
        :type db_flag: bool, optional
        :return: _description_
        :rtype: List[object]
        """
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

    def is_node_valid(self, node: TreeNode) -> bool:
        """_summary_

        :param node: _description_
        :type node: TreeNode
        :return: _description_
        :rtype: bool
        """
        if type(node.type) is not TreeNodeType:
            return False
        if type(node.id) is not str:
            return False
        if type(node.text) is not str:
            return False
        if type(node.props) is not dict:
            return False

        for k in node.props.keys():
            if type(k) is not str:
                return False

        if 'external_id' in node.props:
            return False

        return True

    def formate_nodes_output(self, raw_nodes: object) -> List[TreeNode]:
        """_summary_

        :param raw_nodes: _description_
        :type raw_nodes: object
        :return: _description_
        :rtype: List[TreeNode]
        """
        formated_nodes = []
        for raw_node in raw_nodes:
            cur_f_node = TreeNode(
                id=raw_node['n']['external_id'], text=raw_node['n']['text'],
                type=TREENODES_TYPES_MAP[list(raw_node['n'].labels)[0]], props=dict(raw_node['n']))
            del cur_f_node.props['external_id']

            if cur_f_node.type != TreeNodeType.root:
                del cur_f_node.props['text']

            formated_nodes.append(cur_f_node)
        return formated_nodes

    def __del__(self):
        self.close_connection()
