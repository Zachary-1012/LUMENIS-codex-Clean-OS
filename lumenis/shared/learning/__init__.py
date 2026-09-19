"""LUMENIS Shared Learning canonical owner.

Learning is a Shared Capability. Agent memory, CTH/BMP, SYSTEM and runtime
surfaces consume this package; they must not own parallel learning engines.

Safety invariant:
- learning output is never Production Truth by itself;
- rule suggestions require human review and remain inactive until a separate
  governed activation step;
- AI-generated research must not be written into canonical external-event
  tables as if it were observed evidence.
"""
from .memory import LearningMemory, LearningType, LifecycleStage, SampleType
from .loop import LearningLoop, RuleSuggestion
from .collector import CodebaseScanner, LearningAnalyzer, run_learning_scan, get_learning_history
from .feedback import DataFeedbackLoop, data_feedback_loop
from .persistence import LearningPersistence
from .operations import (
    OperationLearning, get_operation_learning, get_learning_status,
    get_operation_history, get_optimization_suggestion, record_operation,
)

__all__ = [
    "LearningMemory", "LearningType", "LifecycleStage", "SampleType",
    "LearningLoop", "RuleSuggestion",
    "CodebaseScanner", "LearningAnalyzer", "run_learning_scan", "get_learning_history",
    "DataFeedbackLoop", "data_feedback_loop", "LearningPersistence",
    "OperationLearning", "get_operation_learning", "get_learning_status",
    "get_operation_history", "get_optimization_suggestion", "record_operation",
]
