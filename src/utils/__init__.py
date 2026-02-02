from .logger import Logger
from .data_structs import Triplet, TripletCreator, NodeCreator, NodeType, RelationCreator, RelationType
from .task_solver import AgentTaskSolver, AgentTaskSolverConfig, AgentTaskSuite

# Опциональный импорт - polyglot может отсутствовать
try:
    from .language_detector import detect_lang
except ImportError:
    detect_lang = None  # polyglot не установлен

from .errors import ReturnStatus, ReturnInfo
