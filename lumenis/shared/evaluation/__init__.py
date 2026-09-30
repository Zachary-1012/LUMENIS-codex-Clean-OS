"""LUMENIS Shared Evaluation canonical owner.

Evaluation is a Shared Capability. Domain and Agent runtimes consume this
package; they do not own parallel evaluation implementations.
"""
from .recorder import (
    DEFAULT_DB_PATH, VALID_DIMENSIONS, VALID_STATUSES, EvaluationRecord,
    get_evaluation_record, get_evaluation_records, get_evaluation_summary, init_db, judge_status,
    record_evaluation, record_evaluation_raw, threshold_to_str,
)
from .dimensions import (
    THRESHOLDS, evaluate_ai_dimension, evaluate_collector_dimension,
    evaluate_data_dimension, evaluate_report_dimension, evaluate_runtime_dimension,
)
from .runner import EvaluationRunner, run_full_evaluation
from .trajectory import (
    DimensionScore, TrajectoryEvaluation, TrajectoryEvaluator, TrajectoryMetrics,
)

__all__ = [
    "DEFAULT_DB_PATH", "VALID_DIMENSIONS", "VALID_STATUSES", "EvaluationRecord",
    "get_evaluation_record", "get_evaluation_records", "get_evaluation_summary", "init_db", "judge_status",
    "record_evaluation", "record_evaluation_raw", "threshold_to_str", "THRESHOLDS",
    "evaluate_ai_dimension", "evaluate_collector_dimension", "evaluate_data_dimension",
    "evaluate_report_dimension", "evaluate_runtime_dimension", "EvaluationRunner",
    "run_full_evaluation", "DimensionScore", "TrajectoryEvaluation",
    "TrajectoryEvaluator", "TrajectoryMetrics",
]
