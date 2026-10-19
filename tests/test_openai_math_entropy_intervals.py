"""Bounded exact-enclosure regressions; no live data or product persistence."""

from decimal import Decimal, localcontext
from fractions import Fraction
import json
import sys
from types import SimpleNamespace

import pytest

from lumenis.shared.evaluation.openai_math_papers import entropy_intervals as intervals
from lumenis.shared.evaluation.openai_math_papers.core import (
    Budget, MathInputError, ResourceBound, digest,
)
from lumenis.shared.evaluation.openai_math_papers.dispatch import execute


@pytest.fixture(autouse=True)
def isolated_review_storage(tmp_path, monkeypatch):
    # Dispatch reads the canonical paper-review evidence. Use its real empty
    # schema in a unique temporary DB, never a developer/production database.
    from lumenis.shared import database
    from lumenis.shared.evidence.store import init_evidence_store

    path = str(tmp_path / "evidence.db")
    init_evidence_store(path)
    repository = database.DatabaseRepository(path)
    monkeypatch.setattr(database, "get_repository", lambda **kwargs: repository)


def _request(q=Fraction(1, 2)):
    return {
        "operation": "matching.entropy_bounds",
        "parameters": {
            "graph": {"vertices": 4, "edges": [[0, 1], [2, 3], [0, 2], [1, 3]]},
            "mixture": [
                {"matching": [0, 1], "probability": str(q)},
                {"matching": [2, 3], "probability": str(1 - q)},
            ],
        },
    }


def _assert_contains(interval, reference):
    # Decimal at 180 digits is an independent high-precision numeric regression
    # oracle, not a formal proof of the analytic interval or paper theorem.
    lo, hi = interval
    assert lo <= Fraction(reference) <= hi
    assert hi - lo < Fraction(1, 10**40)


@pytest.mark.parametrize("q", [Fraction(1), Fraction(2), Fraction(1, 2),
                              Fraction(3, 7), Fraction(7, 3), Fraction(16)])
def test_log_contains_high_precision_reference(q):
    with localcontext() as context:
        context.prec = 180
        reference = (Decimal(q.numerator) / Decimal(q.denominator)).ln()
    _assert_contains(intervals.log_interval(q, Budget()), reference)


def test_entropy_contains_high_precision_reference_and_endpoints():
    probabilities = [Fraction(0), Fraction(1, 3), Fraction(2, 3), Fraction(1)]
    with localcontext() as context:
        context.prec = 180
        reference = -sum((
            (Decimal(p.numerator) / Decimal(p.denominator))
            * (Decimal(p.numerator) / Decimal(p.denominator)).ln()
            for p in probabilities if p
        ), Decimal(0))
    _assert_contains(intervals.entropy_interval(probabilities, Budget()), reference)
    assert intervals.entropy_interval([Fraction(0)], Budget()) == (0, 0)


@pytest.mark.parametrize("q", [Fraction(0), Fraction(-1)])
def test_log_domain(q):
    with pytest.raises(MathInputError, match="LOG_POSITIVE_ARGUMENT_REQUIRED"):
        intervals.log_interval(q, Budget())


def test_normal_matching_result_still_completes():
    result = execute(_request())
    assert result["result"]["state"] == "COMPUTED"
    assert result["computation"]["limits_applied"] is True
    enclosure = result["result"]["rational_enclosures"]["F"]
    with localcontext() as context:
        context.prec = 180
        reference = 2 * Decimal(2).ln()
    _assert_contains((Fraction(enclosure["lower"]), Fraction(enclosure["upper"])), reference)


def test_input_denominator_over_active_budget_rejected():
    budget = Budget(max_bits=64)
    with pytest.raises(ResourceBound, match="EXACT_ARITHMETIC_BIT_BUDGET_EXCEEDED"):
        intervals.log_interval(Fraction(1, 2**64 + 1), budget)
    assert budget.steps == 1


def test_series_growth_rejected_before_full_series():
    class RecordingBudget(Budget):
        calls = 0

        def rational(self, value):
            self.calls += 1
            return super().rational(value)

    budget = RecordingBudget(max_bits=64)
    # The nine-bit input fits; the exact power/partial sum does not.
    with pytest.raises(ResourceBound, match="EXACT_ARITHMETIC_BIT_BUDGET_EXCEEDED"):
        intervals.log_interval(Fraction(1, 257), budget)
    assert 1 < budget.calls < 48


def test_legal_large_denominator_cannot_claim_success():
    # Only 91 input bits, admitted by rat() and mixture construction; the old
    # implementation returned 9,142-bit F.lower under the default 8,192 limit.
    with pytest.raises(ResourceBound, match="EXACT_ARITHMETIC_BIT_BUDGET_EXCEEDED"):
        execute(_request(Fraction(1, 2**90 + 1)))


def test_entropy_aggregation_is_checked(monkeypatch):
    values = iter([Fraction(-1, 2**40 - 1), Fraction(-1, 2**40 + 1)])

    def bounded_log(p, budget):
        value = next(values)
        return value, value

    monkeypatch.setattr(intervals, "log_interval", bounded_log)
    with pytest.raises(ResourceBound, match="EXACT_ARITHMETIC_BIT_BUDGET_EXCEEDED"):
        intervals.entropy_interval([Fraction(1, 2), Fraction(1, 2)], Budget(max_bits=64))


def test_interval_width_is_checked(monkeypatch):
    pair = Fraction(1, 2**40 + 1), Fraction(1, 2**40 - 1)
    monkeypatch.setattr(intervals, "entropy_interval", lambda *args: pair)
    with pytest.raises(ResourceBound, match="EXACT_ARITHMETIC_BIT_BUDGET_EXCEEDED"):
        intervals.matching_bounds_intervals([], [], 1, Budget(max_bits=64))


@pytest.mark.parametrize("budget,reason", [
    (lambda: Budget(cancelled=lambda: True), "CANCELLED"),
    (lambda: Budget(max_steps=1), "OPERATION_BUDGET_EXCEEDED"),
])
def test_existing_cooperative_limits_preserved(budget, reason):
    with pytest.raises(ResourceBound, match=reason):
        intervals.log_interval(Fraction(1, 2), budget())


def test_cli_reports_incomplete_without_partial_result(tmp_path, monkeypatch, capsys):
    from lumenis.shared.evaluation.openai_math_papers.cli import main

    request_file = tmp_path / "request.json"
    request_file.write_text(json.dumps(_request(Fraction(1, 2**90 + 1))))
    monkeypatch.setattr(sys, "argv", ["math", str(request_file)])
    assert main() == 3
    assert json.loads(capsys.readouterr().out) == {
        "state": "INCOMPLETE",
        "reason": "EXACT_ARITHMETIC_BIT_BUDGET_EXCEEDED",
        "partial_result_accepted": False,
    }


def test_task_adapter_propagates_resource_failure_before_success(monkeypatch):
    # Isolate source access only; exercise the real adapter, dispatcher and
    # interval code. This is an error-propagation regression, not permission E2E.
    from agent_runtime.openai_math_paper_handler import handle_openai_math_task

    reads, phases = [], []

    def read_source(*args, **kwargs):
        reads.append(args)
        return {"artifact_outcome": {"artifact_hash": "source-version"}}

    def authorize(**kwargs):
        phases.append(kwargs["phase"])
        return {"allowed": True, "decision_ref": "test-decision"}

    monkeypatch.setitem(sys.modules, "lumenis.shared.reporting.source_brief_job",
                        SimpleNamespace(get_source_brief_job=read_source))
    spec = _request(Fraction(1, 2**90 + 1))
    task = {"context": {
        "openai_math_problem": spec,
        "openai_math_problem_sha256": digest(spec),
        "source_brief_job_id": "test-source",
        "source_brief_artifact_hash": "source-version",
    }}
    with pytest.raises(ResourceBound, match="EXACT_ARITHMETIC_BIT_BUDGET_EXCEEDED"):
        handle_openai_math_task(task, actor=object(), actor_id="test-actor",
                               expected_scope={}, authorize_compute=authorize)
    assert phases == ["before"]
    assert len(reads) == 1
