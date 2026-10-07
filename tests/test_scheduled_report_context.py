"""Legacy scheduled reference jobs select their subject without leaking it."""
import ast
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from domain_isolation import get_domain_context
from subject_context import brand_scope
from lumenis.shared.reporting.engine import _resolve_legacy_report_scope


@pytest.mark.parametrize("name", [
    "_generate_all_reports", "_generate_daily_report", "_generate_weekly_report",
])
@pytest.mark.parametrize("fails", [False, True])
def test_scheduled_reference_job_preserves_callers_context(name, fails):
    # Execute the actual scheduling functions without importing app.py's startup
    # and scheduler effects. Reporting's actual context validator remains active.
    tree = ast.parse(Path("app.py").read_text(encoding="utf-8-sig"))
    function = next(node for node in tree.body
                    if isinstance(node, ast.FunctionDef) and node.name == name)
    calls = []

    def generate(*args, domain_id=None):
        calls.append(_resolve_legacy_report_scope(domain_id))
        if fails:
            raise RuntimeError("isolated report failure")
        return {"_artifact_verified": True, "_db_row_id": 1}, "digest"

    namespace = {
        "report_engine": SimpleNamespace(generate_all=generate, generate_report=generate),
        "datetime": datetime, "timedelta": timedelta,
    }
    exec(compile(ast.Module(body=[function], type_ignores=[]), "app.py", "exec"), namespace)
    with brand_scope("non-reference-brand", "ZBMP"):
        before = get_domain_context()
        if fails and name == "_generate_all_reports":
            with pytest.raises(RuntimeError, match="isolated report failure"):
                namespace[name]()
        else:
            result = namespace[name]()
            if name != "_generate_all_reports":
                assert result is (not fails)
        assert get_domain_context() == before
    assert calls == [("cth", "CTH")]
