"""The real locator must route shared API files to their composition owner."""
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
LOCATOR = ROOT / "scripts/audit_tools/locate_capability_context.py"


def test_shared_experience_api_routes_to_composition_owner():
    result = subprocess.run(
        [sys.executable, "-B", str(LOCATOR), "--path", "experience_runtime.py",
         "--query", "route-owner-check", "--limit", "1"],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30,
    )
    assert result.returncode == 0, result.stderr
    context = json.loads(result.stdout)
    assert context["capability"] == "product_api"
    assert context["source_owner_index_row"][0] == "Product Core composition/API"
    assert "experience_runtime.py" in context["owner_roots"]


def test_explicit_collector_cannot_claim_shared_api_file():
    result = subprocess.run(
        [sys.executable, "-B", str(LOCATOR), "--capability", "collector",
         "--path", "experience_runtime.py", "--limit", "1"],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30,
    )
    assert result.returncode != 0
    assert "path routes to product_api, not collector" in result.stderr
