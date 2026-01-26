import sys
from copy import deepcopy
from functools import reduce

# TO CHANGE
PROJECT_BASE_DIR = '../'
TEST_VOLUME_DIR = './volumes'
sys.path.insert(0, PROJECT_BASE_DIR)

from src.pipelines.qa import QAPipelineConfig
from src.agents.AgentDriver import AgentDriverConfig, AgentConnectorConfig
from src.db_drivers.kv_driver import KeyValueDriverConfig, KVDBConnectionConfig
from src.utils.data_structs import NodeType

from src.pipelines.qa.kg_reasoning.KGReasoner import KnowledgeGraphReasonerConfig
from src.pipelines.qa.kg_reasoning.weak_reasoner import WeakKGReasonerConfig
from src.pipelines.qa.kg_reasoning.weak_reasoner.query_parser import QueryLLMParserConfig
from src.pipelines.qa.kg_reasoning.weak_reasoner.knowledge_comparator import KnowledgeComparatorConfig
from src.pipelines.qa.kg_reasoning.weak_reasoner.knowledge_retriever import KnowledgeRetrieverConfig, AStarGraphSearchConfig, \
    AStarMetricsConfig, WaterCirclesSearchConfig,  MixturedGraphSearchConfig, NaiveBFSGraphSearchConfig, \
        NaiveGraphSearchConfig, GraphBeamSearchConfig, TripletsFilterConfig
from src.pipelines.qa.kg_reasoning.weak_reasoner.answer_generator import QALLMGeneratorConfig

from src.pipelines.qa.kg_reasoning.weak_reasoner.query_parser.agent_tasks.kw_extraction import AgentKWETaskConfigSelector
from src.pipelines.qa.kg_reasoning.weak_reasoner.answer_generator.agent_tasks.ag import AgentSimpleAGTaskConfigSelector

#
from src.pipelines.qa.answers_aggregation import AnswersAggregatorConfig
from src.pipelines.qa.answers_aggregation.agent_tasks.answers_summarisation import AgentSubASummTaskConfigSelector

from src.pipelines.qa.query_preprocessing import QueryPreprocessorConfig
from src.pipelines.qa.query_preprocessing.decomposition import QueryDecomposerConfig
from src.pipelines.qa.query_preprocessing.decomposition.agent_tasks.decomposition_classifier import AgentDecompClsTaskConfigSelector
from src.pipelines.qa.query_preprocessing.decomposition.agent_tasks.query_decomposition import AgentQueryDecompTaskConfigSelector

from src.pipelines.qa.kg_reasoning.medium_reasoner import MediumKGReasonerConfig
from src.pipelines.qa.kg_reasoning.medium_reasoner.searchplan_enhancer import SearchPlanEnhancerConfig
from src.pipelines.qa.kg_reasoning.medium_reasoner.searchplan_enhancer.agent_tasks.enhance_classifier import AgentEnhanceClassifierTaskConfigSelector
from src.pipelines.qa.kg_reasoning.medium_reasoner.searchplan_enhancer.agent_tasks.plan_enhancer import AgentPlanEnhancingTaskConfigSelector
from src.pipelines.qa.kg_reasoning.medium_reasoner.searchplan_enhancer.agent_tasks.plan_initializer import AgentPlanInitTaskConfigSelector

from src.pipelines.qa.kg_reasoning.medium_reasoner.entities_extractor import EntitiesExtractorConfig
from src.pipelines.qa.kg_reasoning.medium_reasoner.entities_extractor.agent_tasks.entities_extractor import AgentEntitiesExtrTaskConfigSelector

from src.pipelines.qa.kg_reasoning.medium_reasoner.entities2nodes_matching import Entities2NodesMatcherConfig

from src.pipelines.qa.kg_reasoning.medium_reasoner.cluequeries_generator import ClueQueriesGeneratorConfig
from src.pipelines.qa.kg_reasoning.medium_reasoner.cluequeries_generator.agent_tasks.query_generator import AgentCQueryGenTaskConfigSelector

from src.pipelines.qa.kg_reasoning.medium_reasoner.clueanswers_summarisation import ClueAnswersSummarizerConfig
from src.pipelines.qa.kg_reasoning.medium_reasoner.clueanswers_summarisation.agent_tasks.answers_summarisation import AgentClueAnswersSummTaskConfigSelector

from src.pipelines.qa.kg_reasoning.medium_reasoner.answer_generator import AnswerGeneratorConfig
from src.pipelines.qa.kg_reasoning.medium_reasoner.answer_generator.agent_tasks.answer_generator import AgentAnswerGeneratorTaskConfigSelector
from src.pipelines.qa.kg_reasoning.medium_reasoner.answer_generator.agent_tasks.answer_trying_classifier import AgentAnswerClassifierTaskConfigSelector

####################

RAW_TEXTS_EN = [
    "Students living in the dormitory have the right to 24-hour access to their place of residence.",
    "Students living in the dormitory have the right to apply to the administration of the Federal State Budgetary Institution 'MSG' with an application, certified by the head of the dormitory, for the placement of relatives in the guest rooms of the dormitory (for a short period of stay, at least 2 days), parents - for any period (upon presentation of a document confirming the degree of kinship).",
    "Students living in the dormitory have the right to use the rooms for independent study and cultural and household premises, equipment, inventory of the dormitory.",
    "Students living in the dormitory have the right to contact the administration of the building with requests for timely repairs, replacement of equipment and inventory that failed through no fault of theirs.",
    "Students living in the dormitory have the right to move from one room to another in the same building, as well as to move from one building to another if there are vacancies, with the consent of the administration buildings.",
    "Students living in the dormitory have the right to participate in the formation and election of the MSG Student Council and to be elected to its composition.",
    "Students living in the dormitory have the right to participate (make proposals) through the MSG Student Council and the youth policy department of the FSBI 'MSG' in resolving issues of improving housing and living conditions, organizing educational work and leisure.",
    "Students living in the dormitory have the right to take part in social, sports and cultural and leisure events organized by the administration of the FSBI 'MSG' and the MSG Student Council.",
]

EN_QUESTIONS = [
    "Do students living in a dormitory have 24-hour access to their accommodation?",
    "Can students contact the administration with questions?",
    "Can students living in the dormitory take part in events organized by the administration of 'MSG'?"
]

AGENT_DRIVER_CONFIG = AgentDriverConfig(
    name='ollama',
    agent_config=AgentConnectorConfig(
        gen_strategy={"num_predict": 2048, "seed": 42, "top_k": 1, "temperature": 0.0},
        credentials={"model": 'qwen2.5:7b'},
        ext_params={"host": 'localhost', "port": 11438, "timeout": 560, "keep_alive": -1}))

KV_CACHE_CONFIG = KeyValueDriverConfig(
    db_vendor='mixed_kv',
    db_config=KVDBConnectionConfig(
        need_to_clear=False,
        params={
            'mongo_config': KVDBConnectionConfig(
                host='localhost', port=27010,
                db_info={'db': 'memorize_db', 'table': None},
                params={'username': 'user', 'password': 'pass', 'max_storage': -1},
                need_to_clear=False),
            'redis_config': KVDBConnectionConfig(
                host='localhost', port=6370,
                db_info={'db': 0, 'table': None},
                params={'ss_name': 'sorted_node_pairs', 'hs_name': 'node_pairs', 'max_storage': 50000000},
                need_to_clear=False)}))

###########################

WEAK_QA_CONFIG = QAPipelineConfig(
    reasoner_config=KnowledgeGraphReasonerConfig(
        reasoner_name='weak',
        reasoner_hyperparameters=WeakKGReasonerConfig(
            query_parser_config=QueryLLMParserConfig(
                lang='en', adriver_config=AGENT_DRIVER_CONFIG,
                kw_extraction_task_config=...),
            knowledge_comparator_config=KnowledgeComparatorConfig(),
            knowledge_retriever_config=KnowledgeRetrieverConfig(
                retriever_method=...,
                retriever_config=...,
                filter_method=...,
                filter_config=...),
            answer_generator_config=QALLMGeneratorConfig(
                lang='en',
                adriver_config=AGENT_DRIVER_CONFIG,
                ag_task_config=...))))

MEDIUM_QA_CONFIG = QAPipelineConfig(
    preprocessor_config=QueryPreprocessorConfig(
        decomposition_config=QueryDecomposerConfig(
            lang='en', adriver_config=AGENT_DRIVER_CONFIG,
            classify_agent_task_config=...,
            decompose_agent_task_config=...,
        )
    ),
    reasoner_config=KnowledgeGraphReasonerConfig(
        reasoner_name='medium',
        reasoner_hyperparameters=MediumKGReasonerConfig(
            searchplan_enhancer_config=SearchPlanEnhancerConfig(
                lang='en', adriver_config=AGENT_DRIVER_CONFIG, 
                plan_initing_agent_task_config=...,
                enhance_classifier_agent_task_config=...,
                plan_enhancing_agent_task_config=...
            ),
            entities_extractor_config=EntitiesExtractorConfig(
                lang='en', adriver_config=AGENT_DRIVER_CONFIG,
                entities_extraction_agent_task_config=...
            ),
            e2n_matcher_config=Entities2NodesMatcherConfig(),
            cluequeries_generator_config=ClueQueriesGeneratorConfig(
                lang='en', adriver_config=AGENT_DRIVER_CONFIG,
                cquerie_generator_agent_task_config=...
            ),
            knowledge_retriever_config=KnowledgeRetrieverConfig(
                retriever_method='beamsearch',
                retriever_config=GraphBeamSearchConfig(
                    max_depth=2, max_paths=50, 
                    accepted_node_types=[NodeType.object, NodeType.hyper, NodeType.episodic]),
                filter_method='naive',
                filter_config=TripletsFilterConfig()
            ),
            clueanswer_generator_config=QALLMGeneratorConfig(
                lang='en', adriver_config=AGENT_DRIVER_CONFIG,
                ag_task_config=...
            ),
            clueanswers_summarizer_confif=ClueAnswersSummarizerConfig(
                lang='en', adriver_config=AGENT_DRIVER_CONFIG,
                canswers_summarisation_agent_task_config=...
            ),
            answer_generator_config=AnswerGeneratorConfig(
                lang='en', adriver_config=AGENT_DRIVER_CONFIG,
                answer_classifier_agent_task_config=...,
                answer_generator_agent_task_config=...
            ),
            max_searchplan_steps=5
        )
    ),

    aggregator_config=AnswersAggregatorConfig(
        lang='en', adriver_config=AGENT_DRIVER_CONFIG,
        suba_summarisation_agent_task_config=...
    )
)

###########################

# Различные конфиги weak qa-пайплайна

# astar (w and w/o caching)
QA_V1_CONFIG1 = deepcopy(WEAK_QA_CONFIG)
QA_V1_CONFIG1.reasoner_config.reasoner_hyperparameters.query_parser_config.kw_extraction_task_config= AgentKWETaskConfigSelector.select(base_config_version='v1')
QA_V1_CONFIG1.reasoner_config.reasoner_hyperparameters.knowledge_retriever_config.retriever_method='astar'
QA_V1_CONFIG1.reasoner_config.reasoner_hyperparameters.knowledge_retriever_config.retriever_config=AStarGraphSearchConfig()
QA_V1_CONFIG1.reasoner_config.reasoner_hyperparameters.knowledge_retriever_config.filter_method='naive'
QA_V1_CONFIG1.reasoner_config.reasoner_hyperparameters.knowledge_retriever_config.filter_config=TripletsFilterConfig()
QA_V1_CONFIG1.reasoner_config.reasoner_hyperparameters.answer_generator_config.ag_task_config=AgentSimpleAGTaskConfigSelector.select(base_config_version='v1')

QA_V2_CONFIG1 = deepcopy(QA_V1_CONFIG1)
QA_V2_CONFIG1.reasoner_config.reasoner_hyperparameters.query_parser_config.kw_extraction_task_config= AgentKWETaskConfigSelector.select(base_config_version='v2')
QA_V2_CONFIG1.reasoner_config.reasoner_hyperparameters.answer_generator_config.ag_task_config=AgentSimpleAGTaskConfigSelector.select(base_config_version='v2')

# beamsearch (w and w/o caching)
QA_V1_CONFIG2 = deepcopy(WEAK_QA_CONFIG)
QA_V1_CONFIG2.reasoner_config.reasoner_hyperparameters.query_parser_config.kw_extraction_task_config= AgentKWETaskConfigSelector.select(base_config_version='v1')
QA_V1_CONFIG2.reasoner_config.reasoner_hyperparameters.knowledge_retriever_config.retriever_method='beamsearch'
QA_V1_CONFIG2.reasoner_config.reasoner_hyperparameters.knowledge_retriever_config.retriever_config=GraphBeamSearchConfig()
QA_V1_CONFIG2.reasoner_config.reasoner_hyperparameters.knowledge_retriever_config.filter_method='naive'
QA_V1_CONFIG2.reasoner_config.reasoner_hyperparameters.knowledge_retriever_config.filter_config=TripletsFilterConfig()
QA_V1_CONFIG2.reasoner_config.reasoner_hyperparameters.answer_generator_config.ag_task_config=AgentSimpleAGTaskConfigSelector.select(base_config_version='v1')

QA_V2_CONFIG2 = deepcopy(QA_V1_CONFIG2)
QA_V2_CONFIG2.reasoner_config.reasoner_hyperparameters.query_parser_config.kw_extraction_task_config= AgentKWETaskConfigSelector.select(base_config_version='v2')
QA_V2_CONFIG2.reasoner_config.reasoner_hyperparameters.answer_generator_config.ag_task_config=AgentSimpleAGTaskConfigSelector.select(base_config_version='v2')


# water circles (w and w/o caching)
QA_V1_CONFIG3 = deepcopy(WEAK_QA_CONFIG)
QA_V1_CONFIG3.reasoner_config.reasoner_hyperparameters.query_parser_config.kw_extraction_task_config= AgentKWETaskConfigSelector.select(base_config_version='v1')
QA_V1_CONFIG3.reasoner_config.reasoner_hyperparameters.knowledge_retriever_config.retriever_method='watercircles'
QA_V1_CONFIG3.reasoner_config.reasoner_hyperparameters.knowledge_retriever_config.retriever_config=WaterCirclesSearchConfig()
QA_V1_CONFIG3.reasoner_config.reasoner_hyperparameters.knowledge_retriever_config.filter_method='naive'
QA_V1_CONFIG3.reasoner_config.reasoner_hyperparameters.knowledge_retriever_config.filter_config=TripletsFilterConfig()
QA_V1_CONFIG3.reasoner_config.reasoner_hyperparameters.answer_generator_config.ag_task_config=AgentSimpleAGTaskConfigSelector.select(base_config_version='v1')

QA_V2_CONFIG3 = deepcopy(QA_V1_CONFIG3)
QA_V2_CONFIG3.reasoner_config.reasoner_hyperparameters.query_parser_config.kw_extraction_task_config= AgentKWETaskConfigSelector.select(base_config_version='v2')
QA_V2_CONFIG3.reasoner_config.reasoner_hyperparameters.answer_generator_config.ag_task_config=AgentSimpleAGTaskConfigSelector.select(base_config_version='v2')

# naive rag (w and w/o caching)
QA_V1_CONFIG4 = deepcopy(WEAK_QA_CONFIG)
QA_V1_CONFIG4.reasoner_config.reasoner_hyperparameters.query_parser_config =None
QA_V1_CONFIG4.reasoner_config.reasoner_hyperparameters.knowledge_retriever_config.retriever_method='naive_retriever'
QA_V1_CONFIG4.reasoner_config.reasoner_hyperparameters.knowledge_retriever_config.retriever_config=NaiveGraphSearchConfig()
QA_V1_CONFIG4.reasoner_config.reasoner_hyperparameters.knowledge_retriever_config.filter_method=None
QA_V1_CONFIG4.reasoner_config.reasoner_hyperparameters.knowledge_retriever_config.filter_config=None
QA_V1_CONFIG4.reasoner_config.reasoner_hyperparameters.answer_generator_config.ag_task_config=AgentSimpleAGTaskConfigSelector.select(base_config_version='v1')

QA_V2_CONFIG4 = deepcopy(QA_V1_CONFIG4)
QA_V2_CONFIG4.reasoner_config.reasoner_hyperparameters.answer_generator_config.ag_task_config=AgentSimpleAGTaskConfigSelector.select(base_config_version='v2')

# bfs (w and w/o caching)
QA_V1_CONFIG5 = deepcopy(WEAK_QA_CONFIG)
QA_V1_CONFIG5.reasoner_config.reasoner_hyperparameters.query_parser_config.kw_extraction_task_config= AgentKWETaskConfigSelector.select(base_config_version='v1')
QA_V1_CONFIG5.reasoner_config.reasoner_hyperparameters.knowledge_retriever_config.retriever_method='naive_bfs'
QA_V1_CONFIG5.reasoner_config.reasoner_hyperparameters.knowledge_retriever_config.retriever_config=NaiveBFSGraphSearchConfig()
QA_V1_CONFIG5.reasoner_config.reasoner_hyperparameters.knowledge_retriever_config.filter_method='naive'
QA_V1_CONFIG5.reasoner_config.reasoner_hyperparameters.knowledge_retriever_config.filter_config=TripletsFilterConfig()
QA_V1_CONFIG5.reasoner_config.reasoner_hyperparameters.answer_generator_config.ag_task_config=AgentSimpleAGTaskConfigSelector.select(base_config_version='v1')

QA_V2_CONFIG5 = deepcopy(QA_V1_CONFIG5)
QA_V2_CONFIG5.reasoner_config.reasoner_hyperparameters.query_parser_config.kw_extraction_task_config= AgentKWETaskConfigSelector.select(base_config_version='v2')
QA_V2_CONFIG5.reasoner_config.reasoner_hyperparameters.answer_generator_config.ag_task_config=AgentSimpleAGTaskConfigSelector.select(base_config_version='v2')

# mixture (astar + beamsearch) (w and w/o caching)
QA_V1_CONFIG6 = deepcopy(WEAK_QA_CONFIG)
QA_V1_CONFIG6.reasoner_config.reasoner_hyperparameters.query_parser_config.kw_extraction_task_config= AgentKWETaskConfigSelector.select(base_config_version='v1')
QA_V1_CONFIG6.reasoner_config.reasoner_hyperparameters.knowledge_retriever_config.retriever_method='mixture'
QA_V1_CONFIG6.reasoner_config.reasoner_hyperparameters.knowledge_retriever_config.retriever_config=MixturedGraphSearchConfig(
    retriever1_name='astar', retriever1_config=AStarGraphSearchConfig(),
    retriever2_name='beamsearch', retriever2_config=GraphBeamSearchConfig())
QA_V1_CONFIG6.reasoner_config.reasoner_hyperparameters.knowledge_retriever_config.filter_method='naive'
QA_V1_CONFIG6.reasoner_config.reasoner_hyperparameters.knowledge_retriever_config.filter_config=TripletsFilterConfig()
QA_V1_CONFIG6.reasoner_config.reasoner_hyperparameters.answer_generator_config.ag_task_config=AgentSimpleAGTaskConfigSelector.select(base_config_version='v1')

QA_V2_CONFIG6 = deepcopy(QA_V1_CONFIG6)
QA_V2_CONFIG6.reasoner_config.reasoner_hyperparameters.query_parser_config.kw_extraction_task_config= AgentKWETaskConfigSelector.select(base_config_version='v2')
QA_V2_CONFIG6.reasoner_config.reasoner_hyperparameters.answer_generator_config.ag_task_config=AgentSimpleAGTaskConfigSelector.select(base_config_version='v2')

# mixture (astar + watercircles) (w and w/o caching)
QA_V1_CONFIG7 = deepcopy(WEAK_QA_CONFIG)
QA_V1_CONFIG7.reasoner_config.reasoner_hyperparameters.query_parser_config.kw_extraction_task_config= AgentKWETaskConfigSelector.select(base_config_version='v1')
QA_V1_CONFIG7.reasoner_config.reasoner_hyperparameters.knowledge_retriever_config.retriever_method='mixture'
QA_V1_CONFIG7.reasoner_config.reasoner_hyperparameters.knowledge_retriever_config.retriever_config=MixturedGraphSearchConfig(
    retriever1_name='astar', retriever1_config=AStarGraphSearchConfig(),
    retriever2_name='watercircles', retriever2_config=WaterCirclesSearchConfig())
QA_V1_CONFIG7.reasoner_config.reasoner_hyperparameters.knowledge_retriever_config.filter_method='naive'
QA_V1_CONFIG7.reasoner_config.reasoner_hyperparameters.knowledge_retriever_config.filter_config=TripletsFilterConfig()
QA_V1_CONFIG7.reasoner_config.reasoner_hyperparameters.answer_generator_config.ag_task_config=AgentSimpleAGTaskConfigSelector.select(base_config_version='v1')

QA_V2_CONFIG7 = deepcopy(QA_V1_CONFIG7)
QA_V2_CONFIG7.reasoner_config.reasoner_hyperparameters.query_parser_config.kw_extraction_task_config= AgentKWETaskConfigSelector.select(base_config_version='v2')
QA_V2_CONFIG7.reasoner_config.reasoner_hyperparameters.answer_generator_config.ag_task_config=AgentSimpleAGTaskConfigSelector.select(base_config_version='v2')

# mixture (watercircles + beamsearch) (w and w/o caching)
QA_V1_CONFIG8 = deepcopy(WEAK_QA_CONFIG)
QA_V1_CONFIG8.reasoner_config.reasoner_hyperparameters.query_parser_config.kw_extraction_task_config= AgentKWETaskConfigSelector.select(base_config_version='v1')
QA_V1_CONFIG8.reasoner_config.reasoner_hyperparameters.knowledge_retriever_config.retriever_method='mixture'
QA_V1_CONFIG8.reasoner_config.reasoner_hyperparameters.knowledge_retriever_config.retriever_config=MixturedGraphSearchConfig(
    retriever1_name='beamsearch', retriever1_config=GraphBeamSearchConfig(),
    retriever2_name='watercircles', retriever2_config=WaterCirclesSearchConfig())
QA_V1_CONFIG8.reasoner_config.reasoner_hyperparameters.knowledge_retriever_config.filter_method='naive'
QA_V1_CONFIG8.reasoner_config.reasoner_hyperparameters.knowledge_retriever_config.filter_config=TripletsFilterConfig()
QA_V1_CONFIG8.reasoner_config.reasoner_hyperparameters.answer_generator_config.ag_task_config=AgentSimpleAGTaskConfigSelector.select(base_config_version='v1')

QA_V2_CONFIG8 = deepcopy(QA_V1_CONFIG8)
QA_V2_CONFIG8.reasoner_config.reasoner_hyperparameters.query_parser_config.kw_extraction_task_config= AgentKWETaskConfigSelector.select(base_config_version='v2')
QA_V2_CONFIG8.reasoner_config.reasoner_hyperparameters.answer_generator_config.ag_task_config=AgentSimpleAGTaskConfigSelector.select(base_config_version='v2')

# Различные конфиги medium qa-пайплайна

QA_MEDIUM_V1_CONFIG1 = deepcopy(MEDIUM_QA_CONFIG)
QA_MEDIUM_V1_CONFIG1.preprocessor_config.decomposition_config.classify_agent_task_config = AgentDecompClsTaskConfigSelector.select(base_config_version='v1')
QA_MEDIUM_V1_CONFIG1.preprocessor_config.decomposition_config.decompose_agent_task_config = AgentQueryDecompTaskConfigSelector.select(base_config_version='v1')

QA_MEDIUM_V1_CONFIG1.reasoner_config.reasoner_hyperparameters.searchplan_enhancer_config.plan_initing_agent_task_config = AgentPlanInitTaskConfigSelector.select(base_config_version='v1')
QA_MEDIUM_V1_CONFIG1.reasoner_config.reasoner_hyperparameters.searchplan_enhancer_config.enhance_classifier_agent_task_config = AgentEnhanceClassifierTaskConfigSelector.select(base_config_version='v1')
QA_MEDIUM_V1_CONFIG1.reasoner_config.reasoner_hyperparameters.searchplan_enhancer_config.plan_enhancing_agent_task_config = AgentPlanEnhancingTaskConfigSelector.select(base_config_version='v1')

QA_MEDIUM_V1_CONFIG1.reasoner_config.reasoner_hyperparameters.entities_extractor_config.entities_extraction_agent_task_config = AgentEntitiesExtrTaskConfigSelector.select(base_config_version='v1')
QA_MEDIUM_V1_CONFIG1.reasoner_config.reasoner_hyperparameters.cluequeries_generator_config.cquerie_generator_agent_task_config = AgentCQueryGenTaskConfigSelector.select(base_config_version='v1')
QA_MEDIUM_V1_CONFIG1.reasoner_config.reasoner_hyperparameters.clueanswer_generator_config.ag_task_config = AgentSimpleAGTaskConfigSelector.select(base_config_version='v3')
QA_MEDIUM_V1_CONFIG1.reasoner_config.reasoner_hyperparameters.clueanswers_summarizer_confif.canswers_summarisation_agent_task_config = AgentClueAnswersSummTaskConfigSelector.select(base_config_version='v1')
QA_MEDIUM_V1_CONFIG1.reasoner_config.reasoner_hyperparameters.answer_generator_config.answer_classifier_agent_task_config = AgentAnswerClassifierTaskConfigSelector.select(base_config_version='v1')
QA_MEDIUM_V1_CONFIG1.reasoner_config.reasoner_hyperparameters.answer_generator_config.answer_generator_agent_task_config = AgentAnswerGeneratorTaskConfigSelector.select(base_config_version='v1')

QA_MEDIUM_V1_CONFIG1.aggregator_config.suba_summarisation_agent_task_config = AgentSubASummTaskConfigSelector.select(base_config_version='v1')

def populate_configs_with_diff_accepted_nodes(config: QAPipelineConfig):
    anodes_packs = [[NodeType.object, NodeType.hyper, NodeType.episodic, NodeType.time],
                    [NodeType.object, NodeType.hyper, NodeType.time],
                    [NodeType.object, NodeType.episodic, NodeType.time],
                    [NodeType.hyper, NodeType.episodic, NodeType.time]]

    populated_configs = []
    if config.reasoner_config.reasoner_hyperparameters.knowledge_retriever_config.retriever_method == 'naive_retriever':
        populated_configs = [config]
    else:
        for n_pack in anodes_packs:
            modif_config = deepcopy(config)
            modif_config.reasoner_config.reasoner_hyperparameters.knowledge_retriever_config.retriever_config.accepted_node_types = n_pack
            populated_configs.append(modif_config)

    return populated_configs

#############################

QA_V1_CONFIGS = reduce(lambda acc, v: acc + v,list(map(populate_configs_with_diff_accepted_nodes,[
    QA_V1_CONFIG1, QA_V1_CONFIG2, QA_V1_CONFIG3, QA_V1_CONFIG4,
    QA_V1_CONFIG5, QA_V1_CONFIG6, QA_V1_CONFIG7, QA_V1_CONFIG8])),[])

QA_V2_CONFIGS = reduce(lambda acc, v: acc + v,list(map(populate_configs_with_diff_accepted_nodes,[
    QA_V2_CONFIG1, QA_V2_CONFIG2, QA_V2_CONFIG3, QA_V2_CONFIG4,
    QA_V2_CONFIG5, QA_V2_CONFIG6, QA_V2_CONFIG7, QA_V2_CONFIG8])),[])

QA_MEDIUM_V1_CONFIGS = [QA_MEDIUM_V1_CONFIG1]

# Adding Weak QA-configs

POPULATED_QA_CONFIGS = []
#for i in range(len(QA_V1_CONFIGS)):
#    POPULATED_QA_CONFIGS.append((QA_V1_CONFIGS[i], EN_QUESTIONS, True, False, False))
#for i in range(len(QA_V1_CONFIGS)):
#    POPULATED_QA_CONFIGS.append((QA_V1_CONFIGS[i], EN_QUESTIONS, False, False, False))
#for i in range(len(QA_V1_CONFIGS)):
#    POPULATED_QA_CONFIGS.append((QA_V1_CONFIGS[i], [], True, True, False))

#for i in range(len(QA_V2_CONFIGS)):
#    POPULATED_QA_CONFIGS.append((QA_V2_CONFIGS[i], EN_QUESTIONS, True, False, False))
#for i in range(len(QA_V2_CONFIGS)):
#    POPULATED_QA_CONFIGS.append((QA_V2_CONFIGS[i], EN_QUESTIONS, False, False, False))
#for i in range(len(QA_V2_CONFIGS)):
#    POPULATED_QA_CONFIGS.append((QA_V2_CONFIGS[i], [], True, True, False))

# Adding Medium QA-configs

for i in range(len(QA_MEDIUM_V1_CONFIGS)):
    POPULATED_QA_CONFIGS.append((QA_MEDIUM_V1_CONFIGS[i], EN_QUESTIONS, True, False, False))
# for i in range(len(QA_MEDIUM_V1_CONFIGS)):
#     POPULATED_QA_CONFIGS.append((QA_MEDIUM_V1_CONFIGS[i], EN_QUESTIONS, False, False, False))
for i in range(len(QA_MEDIUM_V1_CONFIGS)):
    POPULATED_QA_CONFIGS.append((QA_MEDIUM_V1_CONFIGS[i], [], True, True, False))

#POPULATED_QA_CONFIGS.append((POPULATED_QA_CONFIGS[-1][0], [], False, False, True))


