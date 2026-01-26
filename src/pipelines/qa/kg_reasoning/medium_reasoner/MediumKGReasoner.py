from dataclasses import dataclass, field
from typing import Tuple, List

from .searchplan_enhancer import SearchPlanEnhancerConfig, SearchPlanEnhancer
from .entities_extractor import EntitiesExtractorConfig, EntitiesExtractor
from .cluequeries_generator import ClueQueriesGeneratorConfig, ClueQueriesGenerator
from .clueanswer_generator import ClueAnswerGenerator, ClueAnswerGeneratorConfig
from .clueanswers_summarisation import ClueAnswersSummarizerConfig, ClueAnswersSummarizer
from .answer_generator import AnswerGeneratorConfig, AnswerGenerator
from .entities2nodes_matching import Entities2NodesMatcher, Entities2NodesMatcherConfig

from .utils import SearchPlanInfo
from .config import MDGR_MAIN_LOG_PATH
from ..utils import AbstractKGReasoner, BaseKGReasonerConfig
from ..weak_reasoner.knowledge_retriever import KnowledgeRetrieverConfig, KnowledgeRetriever
from .....utils.data_structs import create_id
from .....utils import Logger, ReturnInfo, ReturnStatus
from .....kg_model import KnowledgeGraphModel
from .....db_drivers.kv_driver import KeyValueDriverConfig

@dataclass
class MediumKGReasonerConfig(BaseKGReasonerConfig):
    """_summary_

    :param searchplan_enhancer_config: ...
    :type searchplan_enhancer_config: SearchPlanEnhancerConfig, optional
    :param entities_extractor_config: ...
    :type entities_extractor_config: EntitiesExtractorConfig, optional
    :param e2n_matcher_config: ...
    :type e2n_matcher_config: Entities2NodesMatcherConfig, optional

    :param cluequeries_generator_config: ...
    :type cluequeries_generator_config: ClueQueriesGeneratorConfig, optional
    :param knowledge_retriever_config: ...
    :type knowledge_retriever_config: KnowledgeRetrieverConfig, optional
    :param clueanswer_generator_config: ...
    :type clueanswer_generator_config: ClueAnswerGeneratorConfig, optional
    :param clueanswers_summarizer_confif: ...
    :type clueanswers_summarizer_confif: ClueAnswersSummarizerConfig, optional

    :param answer_generator_config: ...
    :type answer_generator_config: AnswerGeneratorConfig, optional

    :param max_searchplan_steps: ...
    :type max_searchplan_steps: int, optional

    :param answer_something: ...
    :type answer_something: bool, optional

    :param log: Отладочный класс для журналирования/мониторинга поведения инициализируемой компоненты. Значение по умолчанию Logger(LOG_PATH).
    :type log: Logger
    :param verbose: Если True, то информация о поведении класса будет сохраняться в stdout и файл-журналирования (log), иначе только в файл. Значение по умолчанию False.
    :type verbose: bool
    """

    searchplan_enhancer_config: SearchPlanEnhancerConfig = field(default_factory=lambda: SearchPlanEnhancerConfig())
    entities_extractor_config: EntitiesExtractorConfig = field(default_factory=lambda: EntitiesExtractorConfig())
    e2n_matcher_config: Entities2NodesMatcherConfig = field(default_factory=lambda: Entities2NodesMatcherConfig())

    cluequeries_generator_config: ClueQueriesGeneratorConfig = field(default_factory=lambda: ClueQueriesGeneratorConfig())
    knowledge_retriever_config: KnowledgeRetrieverConfig = field(default_factory=lambda: KnowledgeRetrieverConfig())
    clueanswer_generator_config: ClueAnswerGeneratorConfig = field(default_factory=lambda: ClueAnswerGeneratorConfig())
    clueanswers_summarizer_confif: ClueAnswersSummarizerConfig = field(default_factory=lambda: ClueAnswersSummarizerConfig())

    answer_generator_config: AnswerGeneratorConfig = field(default_factory=lambda: AnswerGeneratorConfig())

    max_searchplan_steps: int = 5
    answer_something: bool = True

    log: Logger = field(default_factory=lambda: Logger(MDGR_MAIN_LOG_PATH))
    verbose: bool = False

class MediumKGReasoner(AbstractKGReasoner):
    """_summary_
    """

    def __init__(self, kg_model: KnowledgeGraphModel, config: MediumKGReasonerConfig = MediumKGReasonerConfig(),
                 cache_kvdriver_config: KeyValueDriverConfig = None) -> None:
        """_summary_

        :param kg_model: _description_
        :type kg_model: KnowledgeGraphModel
        :param config: _description_, defaults to MediumKGReasonerConfig()
        :type config: MediumKGReasonerConfig, optional
        :param cache_kvdriver_config: _description_, defaults to None
        :type cache_kvdriver_config: KeyValueDriverConfig, optional
        """
        self.config = config
        self.kg_model = kg_model

        self.searchplan_enhancer = SearchPlanEnhancer(self.config.searchplan_enhancer_config, cache_kvdriver_config)

        self.entities_extractor = EntitiesExtractor(self.config.entities_extractor_config, cache_kvdriver_config)
        self.entities2nodes_matcher = Entities2NodesMatcher(self.kg_model, self.config.e2n_matcher_config, cache_kvdriver_config)

        self.cluequeries_generator = ClueQueriesGenerator(self.config.cluequeries_generator_config, cache_kvdriver_config)
        self.knowledge_retriever = KnowledgeRetriever(self.kg_model, self.config.knowledge_retriever_config, cache_kvdriver_config)
        self.clueanswer_generator = ClueAnswerGenerator(self.config.clueanswer_generator_config, cache_kvdriver_config)
        self.clueanswers_summariser = ClueAnswersSummarizer(self.config.clueanswers_summarizer_confif, cache_kvdriver_config)

        self.answer_generator = AnswerGenerator(self.config.answer_generator_config, cache_kvdriver_config)

        self.log = config.log
        self.verbose = config.verbose

    def clear_kv_caches(self):
        # planing
        self.searchplan_enhancer.cachekv.kv_conn.clear()
        self.searchplan_enhancer.plan_initialing_solver.cachekv.kv_conn.clear()
        self.searchplan_enhancer.enhance_classify_solver.cachekv.kv_conn.clear()
        self.searchplan_enhancer.plan_enhancing_solver.cachekv.kv_conn.clear()

        # matching
        self.entities_extractor.cachekv.kv_conn.clear()
        self.entities_extractor.entities_extractor_solver.cachekv.kv_conn.clear()
        #
        self.entities2nodes_matcher.cachekv.kv_conn.clear()

        # retrieving
        self.cluequeries_generator.cachekv.kv_conn.clear()
        self.cluequeries_generator.cluequery_gen_solver.cachekv.kv_conn.clear()
        #
        self.knowledge_retriever.cachekv.kv_conn.clear()
        self.knowledge_retriever.graph_retriever.cachekv.kv_conn.clear()
        if self.knowledge_retriever.triplets_filter is not None:
            self.knowledge_retriever.triplets_filter.cachekv.kv_conn.clear()
        #
        self.clueanswer_generator.cachekv.kv_conn.clear()
        self.clueanswer_generator.clueanswer_generator_solver.cachekv.kv_conn.clear()
        #
        self.clueanswers_summariser.cachekv.kv_conn.clear()
        self.clueanswers_summariser.clueanswers_summ_solver.cachekv.kv_conn.clear()

        # answering
        self.answer_generator.cachekv.kv_conn.clear()
        self.answer_generator.answer_classify_solver.cachekv.kv_conn.clear()
        self.answer_generator.answer_gen_solver.cachekv.kv_conn.clear()

    def perform(self, query: str) -> Tuple[str, ReturnInfo]:
        self.log("START MEDIUM KG-REASONING...", verbose=self.config.verbose)
        self.log(f"BASE_QUESTION ID: {create_id(query)}", verbose=self.config.verbose)
        self.log(f"BASE_QUESTION: {query}", verbose=self.config.verbose)
        answer, info = None, ReturnInfo()
        search_plan = SearchPlanInfo(base_query=query)

        self.log("Start iterative search...", verbose=self.verbose)
        for search_step in range(self.config.max_searchplan_steps):
            self.log(f"CURRENT SEARCH STEP: {search_step} / {self.config.max_searchplan_steps}", verbose=self.verbose)

            self.log("STAGE#1 - SEARCH PLAN INITING/ENHANCING", verbose=self.config.verbose)
            search_plan, info = self.searchplan_enhancer.perform(search_step, search_plan)
            if info.status != ReturnStatus.success:
                self.log(f"RESULT:\n- {info.status}\n- {search_plan}", verbose=self.config.verbose)
                break
            else:
                str_searchsteps = '\n'.join([ f'{i}. {step}' for i, step in enumerate(search_plan.search_steps)])
                self.log(f"RESULT:\n{str_searchsteps}", verbose=self.config.verbose)


            search_query = search_plan.search_steps[search_step]
            self.log(f"Current step #{search_step}: {search_query}", verbose=self.config.verbose)

            self.log("STAGE#2.1 - ENTITIES EXTRACTION", verbose=self.config.verbose)
            entities, info = self.entities_extractor.perform(search_query)
            self.log(f"RESULT: {entities}", verbose=self.config.verbose)
            if info.status != ReturnStatus.success:
                break

            self.log("STAGE#2.2 - ENTITIES-TO-KGOBJECTS MATCHING", verbose=self.config.verbose)
            matched_kg_objects, info = self.entities2nodes_matcher.perform(entities)
            str_matched_kgobject = '\n'.join([f'- [{entitie}][{len(objects)}] ' + ', '.join(list(map(lambda obj: obj.document, objects))) for entitie, objects in matched_kg_objects.items()])
            self.log(f"RESULT:\n{str_matched_kgobject}", verbose=self.config.verbose)
            if info.status != ReturnStatus.success:
                break

            self.log("STAGE#3 - CLUE-QUERIES GENERATION", verbose=self.config.verbose)
            cluequeries, info = self.cluequeries_generator.perform(search_query, matched_kg_objects)
            str_cluequeries = '\n'.join([f'- [{list(map(lambda obj: obj.document, clueq.linked_nodes))}] {clueq.query}' for clueq in cluequeries])
            self.log(f"RESULT: {len(cluequeries)}\n{str_cluequeries}", verbose=self.config.verbose)
            if info.status != ReturnStatus.success:
                break

            self.log("STAGE#4 - RETRIEVING INFORMATION FROM KG BASED ON CLUE-QUERIES", verbose=self.config.verbose)
            clueanswers, error_occurred = [], False
            for j, cur_cluequery in enumerate(cluequeries):
                self.log(f"Current clue-query ({j} / {len(cluequeries)}): {cur_cluequery.query}", verbose=self.config.verbose)
                self.log(f"Current clue-query id: {create_id(cur_cluequery.query)}", verbose=self.config.verbose)

                self.log("STAGE#4.1 - KNOWLEDGE RETRIEVING", verbose=self.config.verbose)
                retrieved_triplets, info = self.knowledge_retriever.retrieve(cur_cluequery)
                self.log(f"RESULT: {len(retrieved_triplets)}", verbose=self.config.verbose)
                for triplet in retrieved_triplets:
                    self.log(f"* {triplet}", verbose=self.config.verbose)
                if info.status != ReturnStatus.success:
                    error_occurred = True
                    break

                self.log("STAGE#4.2 - CLUE-ANSWER GENERATION", verbose=self.config.verbose)
                cur_clueanswer, info = self.clueanswer_generator.perform(search_query, retrieved_triplets)
                self.log(f"RESULT: {cur_clueanswer}", verbose=self.config.verbose)
                if info.status != ReturnStatus.success:
                    error_occurred = True
                    break

                clueanswers.append(cur_clueanswer)

            if error_occurred:
                break

            self.log("STAGE#5 - CLUE-ANSWERS SUMMARISATION", verbose=self.config.verbose)
            search_step_answer, info = self.clueanswers_summariser.perform(
                search_query, list(map(lambda cq_info: cq_info.query, cluequeries)), clueanswers)
            self.log(f"RESULT: {search_step_answer}", verbose=self.config.verbose)
            if info.status != ReturnStatus.success:
                break
            else:
                search_plan.steps_answers.append(search_step_answer)

            self.log("STAGE#6 - ANSWER-GENERATION TRYING", verbose=self.config.verbose)
            answer, info = self.answer_generator.perform(search_plan)
            self.log(f"RESULT: {answer}", verbose=self.config.verbose)
            if info.status != ReturnStatus.success:
                break

            #
            if answer is not None:
                self.log("Удалось сгененирвоать ответа на вопрос. Завершаем поиск.", verbose=self.config.verbose)
                break
            else:
                self.log("Недостаточно информации для генерации релевантного ответа на вопрос. Продолжаем поиск.", verbose=self.config.verbose)

        self.log("Завершаем поиск.", verbose=self.config.verbose)
        self.log(f"Информация по выполненному поиску: {search_plan}", verbose=self.config.verbose)
        if answer is None and info.status == ReturnStatus.success:
            if self.config.answer_something:
                self.log("Пытаемся сгенерировать ответа на основе имеющейся информации...", verbose=self.config.verbose)
                answer, info.status = self.answer_generator.answer_gen_solver.solve(lang=self.answer_generator.config.lang, search_plan=search_plan)
            else:
                self.log("В рамках заданных ограничений поиска не удалось сгенерировать релевантный ответ.", verbose=self.config.verbose)
                answer = "<|NotEnoughtInfo|>"

        self.log(f"RETURNED ANSWER: {answer}", verbose=self.config.verbose)
        self.log(f"STATUS: {info.status}", verbose=self.config.verbose)

        return answer, info
