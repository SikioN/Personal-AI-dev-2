from .logger import Logger
from .errors import ReturnInfo, ReturnStatus
from .data_structs import (
    Quadruplet, QuadrupletCreator,
    Node, NodeCreator, NodeType,
    Relation, RelationCreator, RelationType
)


class _LegacyStub:
    """No-op stub for legacy pipeline classes removed in production refactor."""
    def __init__(self, *args, **kwargs): pass
    def __call__(self, *args, **kwargs): return self
    def __getattr__(self, name): return self


AgentTaskSolverConfig = _LegacyStub
AgentTaskSolver = _LegacyStub
AgentTaskSuite = _LegacyStub
AgentConnectorConfig = _LegacyStub
