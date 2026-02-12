from .WaterCirclesQuadrupletsRetriever import WaterCirclesQuadrupletsRetriever, WaterCirclesSearchConfig
from .MixturedQuadrupletsRetriever import MixturedTripletsRetriever, MixturedGraphSearchConfig
from .QuadrupletsFilter import QuadrupletsFilter, QuadrupletsFilterConfig
from .AStarQuadrupletsRetriever import AStarTripletsRetriever, AStarGraphSearchConfig
from .NaiveBFSQuadrupletsRetriever import NaiveBFSTripletsRetriever, NaiveBFSGraphSearchConfig
from .NaiveQuadrupletsRetriever import NaiveTripletsRetriever, NaiveGraphSearchConfig
from .BeamSearchQuadrupletsRetriever import BeamSearchTripletsRetriever, GraphBeamSearchConfig

KR_MAIN_LOG_PATH = "logs/knowledge_retriever/main.log"

AVAILABLE_QUADRUPLETS_RETRIEVERS = {
    'astar': {
        'config': AStarGraphSearchConfig,
        'class': AStarTripletsRetriever},
    'water_circles': {
        'config': WaterCirclesSearchConfig,
        'class': WaterCirclesQuadrupletsRetriever
    },
    'mixtured': {
        'config': MixturedGraphSearchConfig,
        'class': MixturedTripletsRetriever},
    'naive_bfs': {
        'config': NaiveBFSGraphSearchConfig,
        'class': NaiveBFSTripletsRetriever},
    'naive': {
        'config': NaiveGraphSearchConfig,
        'class': NaiveTripletsRetriever},
    'beamsearch': {
        'config': GraphBeamSearchConfig,
        'class': BeamSearchTripletsRetriever}
}

AVAILABLE_QUADRUPLETS_FILTERS = {
    'naive': {
        'config': QuadrupletsFilterConfig,
        'class': QuadrupletsFilter}
}
