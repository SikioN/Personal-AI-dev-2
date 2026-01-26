from .WaterCirclesTripletsRetriever import WaterCirclesRetriever, WaterCirclesSearchConfig
from .MixturedTripletsRetriever import MixturedTripletsRetriever, MixturedGraphSearchConfig
from .TripletsFilter import TripletsFilter, TripletsFilterConfig
from .AStarTripletsRetriever import AStarTripletsRetriever, AStarGraphSearchConfig
from .NaiveBFSTripletsRetriever import NaiveBFSTripletsRetriever, NaiveBFSGraphSearchConfig
from .NaiveTripletsRetriever import NaiveTripletsRetriever, NaiveGraphSearchConfig
from .BeamSearchTripletsRetriever import BeamSearchTripletsRetriever, GraphBeamSearchConfig

KR_MAIN_LOG_PATH = 'log/qa/kg_reasoner/weak/knowledge_retriever/main'

AVAILABLE_TRIPLETS_RETRIEVERS  = {
    'astar': {
        'config': AStarGraphSearchConfig,
        'class': AStarTripletsRetriever},

    'watercircles': {
        'config': WaterCirclesSearchConfig,
        'class': WaterCirclesRetriever},

    'mixture': {
        'config': MixturedGraphSearchConfig,
        'class': MixturedTripletsRetriever},

    'naive_bfs': {
        'config': NaiveBFSGraphSearchConfig,
        'class': NaiveBFSTripletsRetriever},

    'naive_retriever': {
        'config': NaiveGraphSearchConfig,
        'class': NaiveTripletsRetriever},

    'beamsearch': {
        'config': GraphBeamSearchConfig,
        'class': BeamSearchTripletsRetriever}
}

AVAILABLE_TRIPLETS_FILTERS = {
    'naive': {
        'config': TripletsFilterConfig,
        'class': TripletsFilter}
}
