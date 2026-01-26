from dataclasses import dataclass, field
from typing import Tuple, Union, List, Dict
from copy import deepcopy
import json
from itertools import product

from .config import DEFAULT_CQGEN_TASK_CONFIG, CQGEN_MAIN_LOG_PATH
from ......utils.data_structs import QueryInfo
from ......utils.errors import ReturnStatus
from ......utils import ReturnInfo, Logger, AgentTaskSolverConfig, AgentTaskSolver
from ......agents import AgentDriver, AgentDriverConfig
from ......utils.data_structs import create_id
from ......db_drivers.kv_driver import KeyValueDriverConfig
from ......db_drivers.vector_driver import VectorDBInstance
from ......utils.cache_kv import CacheKV, CacheUtils

@dataclass
class ClueQueriesGeneratorConfig:
    lang: str = 'auto'
    adriver_config: AgentDriverConfig = field(default_factory=lambda: AgentDriverConfig())
    cquerie_generator_agent_task_config: AgentTaskSolverConfig = field(default_factory=lambda: DEFAULT_CQGEN_TASK_CONFIG)

    cache_table_name: str = "medreasn_cquerygen_main_stage_cache"
    log: Logger = field(default_factory=lambda: Logger(CQGEN_MAIN_LOG_PATH))
    verbose: bool = False

    def to_str(self):
        return f"{self.lang}|{self.adriver_config.to_str()}|{self.cquerie_generator_agent_task_config.version}"

class ClueQueriesGenerator(CacheUtils):
    def __init__(self, config: ClueQueriesGeneratorConfig = ClueQueriesGeneratorConfig(), 
                 cache_kvdriver_config: KeyValueDriverConfig = None, cache_llm_inference: bool = True):
        self.config = config

        if cache_kvdriver_config is not None and self.config.cache_table_name is not None:
            cache_config = deepcopy(cache_kvdriver_config)
            cache_config.db_config.db_info['table'] = self.config.cache_table_name
            self.cachekv = CacheKV(cache_config)
        else:
            self.cachekv = None

        self.agent = AgentDriver.connect(config.adriver_config)
        agents_cache_config = None
        if cache_llm_inference:
            agents_cache_config = cache_kvdriver_config

        self.cluequery_gen_solver = AgentTaskSolver(
            self.agent, self.config.cquerie_generator_agent_task_config, agents_cache_config)
        
        self.log = self.config.log
        self.verbose = self.config.verbose

    def get_cache_key(self, search_query: str, matched_kg_objects: Dict[str, List[VectorDBInstance]]) -> List[object]:
        str_matchedobject = json.dumps({k: list(map(lambda vv: vv.document, v))for k,v in matched_kg_objects.items()}, ensure_ascii=False)
        return [search_query, str_matchedobject, self.config.to_str()]

    @CacheUtils.cache_method_output
    def perform(self, search_query: str, matched_kg_objects: Dict[str, List[VectorDBInstance]]) -> Tuple[List[QueryInfo], ReturnInfo]:
        self.log("START CLUE-QUERIES GENERATION...", verbose=self.config.verbose)
        self.log(f"SEARCH_QUERY ID: {create_id(search_query)}", verbose=self.config.verbose)
        self.log(f"SEARCH_QUERY: {search_query}", verbose=self.config.verbose)
        str_matchedobjects = ';'.join([f'{k} - {[vv.document for vv in v]}' for k,v in matched_kg_objects.items()])
        self.log(f"MATCHED_KG_OBJECT: {str_matchedobjects}", verbose=self.config.verbose)
        clue_queries, info = [], ReturnInfo()
        unique_cqueries = set()

        if len(search_query) < 1 or len(matched_kg_objects) < 1:
            raise ValueError
        m_objects_amount = sum(list(map(lambda m_objects: len(m_objects), matched_kg_objects.values())))
        if m_objects_amount < 1:
            raise ValueError

        self.log(f"Получаем декартово произведение всех комбинаций объектов (по сущностям)...", verbose=self.config.verbose)
        base_entities = sorted(list(filter(lambda entitie: len(matched_kg_objects[entitie]) > 0, matched_kg_objects.keys())))
        objects_groups = list(product(*[matched_kg_objects[k] for k in base_entities]))
        str_objectspermuts = ';'.join([f'[{k}] {len(v)}' for k, v in matched_kg_objects.items()])
        self.log(f"RESULT:\n- всего сущностей: {len(matched_kg_objects)}\n- после фильтрации: {len(base_entities)}\n- объектов для каждой сущности: {str_objectspermuts}\n- полученное количество комбинаций: {len(objects_groups)}", verbose=self.config.verbose)
        
        self.log("Генерируем clue-queries...", verbose=self.config.verbose)
        for i, cur_group in enumerate(objects_groups):
            self.log(f"Текущий cleu-query #: {i} / {len(objects_groups)}", verbose=self.config.verbose)
            formated_objects_group = list(map(lambda item: item.document, cur_group))

            self.log("Выполняем генерацию clue-query с помощью LLM-агента...", verbose=self.config.verbose)
            cur_cluequery, status = self.cluequery_gen_solver.solve(
                lang=self.config.lang, query=search_query, base_entities=base_entities, 
                matched_objects=formated_objects_group)
            self.log(f"RESULT: {cur_cluequery}", verbose=self.verbose)

            if status != ReturnStatus.success:
                info.status = status
                break
            else:
                if cur_cluequery in unique_cqueries:
                    self.log("Сгенерированное clue-query уже было получено ранее. Отбрасываем.", verbose=self.config.verbose)
                    continue
                else:
                    self.log("Сгенерированое clue-query ещё получено не было. Сохраняем.", verbose=self.config.verbose)
                    unique_cqueries.add(cur_cluequery)
                    clue_queries.append(QueryInfo(
                        query=cur_cluequery, entities=base_entities, linked_nodes=list(cur_group), 
                        linked_nodes_by_entities=list(map(lambda pair: [base_entities[pair[0]],pair[1]], enumerate(formated_objects_group)))))

        self.log(f"RESULT:\n- Количество clue-queries после фильтрации по строкоовму представлению: {len(clue_queries)}", verbose=self.verbose)
        self.log(f"STATUS: {info.status}", verbose=self.verbose)

        return clue_queries, info
