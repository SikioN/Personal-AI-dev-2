# import pytest

# import sys
# sys.path.insert(0, "../../")
# from src.pipelines.qa.knowledge_retriever.AStarTripletsRetriever import AStarTripletsRetriever

# CYCLED_PARENT = {"a": 'b', 'b': 'c', 'c': 'a'}
# INCONSISTENT_PARENT = {'a': 'b', 'b': 2, 'c': None}
# CONSISTENT_PARENT = {"a": 'b', 'b': 'c', 'c': None}
# EMPTY_PARENT = dict()

# @pytest.mark.parametrize("parent, end_node_id, expected_node_path, exception", [
#     # цикличный путь
#     (CYCLED_PARENT, 'a', None, True),
#     # пустой parent-словарь
#     (EMPTY_PARENT, 'a', None, True),
#     # Неконсистентный словарь с родителями в значениях есть идентификатор (кроме None), который не встречается в ключах.
#     (INCONSISTENT_PARENT, 'a', None, True),
#     # В словаре нет идентифкаторв конечной вершины
#     (CONSISTENT_PARENT, 'd', None, True),
#     # неверный формат идентификатора конечной вершины
#     (CONSISTENT_PARENT, 2, None, True),
#     # позитивный тест
#     (CONSISTENT_PARENT, 'a', ['a', 'b', 'c'], False)
# ])
# def test_get_nodes_path(parent, end_node_id, expected_node_path, exception):
#     try:
#         real_nodes_path = AStarTripletsRetriever.get_nodes_path(parent, end_node_id)
#     except (ValueError, KeyError) as e:
#         assert exception
#     else:
#         assert not exception
#         assert real_nodes_path == expected_node_path
