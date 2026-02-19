from .logger import Logger
from .errors import ReturnInfo, ReturnStatus
from .data_structs import (
    Quadruplet, QuadrupletCreator, 
    Node, NodeCreator, NodeType, 
    Relation, RelationCreator, RelationType
)
from .task_solver import AgentTaskSolver, AgentTaskSolverConfig, AgentTaskSuite

# Optional import
try:
    from .language_detector import detect_lang
except ImportError:
    detect_lang = None
