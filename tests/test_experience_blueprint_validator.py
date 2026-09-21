from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import shutil
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPO_ROOT / "scripts" / "audit_tools" / "verify_experience_screen_blueprints.py"
SPEC = importlib.util.spec_from_file_location("experience_blueprint_validator", VALIDATOR_PATH)
assert SPEC is not None and SPEC.loader is not None
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


@pytest.fixture
def isolated_contracts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[dict, Path]:
    for relative_path in validator.SOURCE_FILES:
        source = REPO_ROOT / relative_path
        target = tmp_path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    return validator._load_registry(), tmp_path


def test_source_content_drift_fails_closed(isolated_contracts: tuple[dict, Path]) -> None:
    registry, temp_root = isolated_contracts
    source = temp_root / "contracts/experience/screen_meta.json"
    source.write_bytes(source.read_bytes() + b" ")

    with pytest.raises(AssertionError, match="source snapshot drift"):
        validator._validate_source_snapshot(registry)


def test_rehashed_screen_id_drift_still_fails_closed(
    isolated_contracts: tuple[dict, Path],
) -> None:
    registry, temp_root = isolated_contracts
    relative_path = "contracts/experience/screen_meta.json"
    source = temp_root / relative_path
    screen_meta = json.loads(source.read_text(encoding="utf-8"))
    old_id = next(iter(screen_meta))
    screen_meta["CTH-99"] = screen_meta.pop(old_id)
    contents = (json.dumps(screen_meta, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    source.write_bytes(contents)

    snapshot = next(entry for entry in registry["source_files"] if entry["file"] == relative_path)
    snapshot["sha256"] = hashlib.sha256(contents).hexdigest()
    sources = validator._validate_source_snapshot(registry)

    with pytest.raises(AssertionError, match="screen source drift between screen_meta and ViewModels"):
        validator._validate_source_ids(registry, sources)


def test_blueprint_first_column_rejects_screen_id_suffix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    constitution = REPO_ROOT / "00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md"
    changed = tmp_path / "constitution.md"
    contents = constitution.read_text(encoding="utf-8")
    original_cell = "| ACC-01 Authentication entry |"
    assert original_cell in contents
    changed.write_text(contents.replace(original_cell, "| ACC-01-suffix Authentication entry |", 1), encoding="utf-8")
    monkeypatch.setattr(validator, "CONSTITUTION", changed)

    with pytest.raises(AssertionError, match="invalid screen blueprint ID/title cell"):
        validator._blueprint_rows()


def test_screen_spec_without_design_decision_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    contract_dir = tmp_path / "contracts" / "experience"
    spec_dir = contract_dir / "screen-specifications"
    spec_dir.mkdir(parents=True)

    contract_readme = contract_dir / "README.md"
    spec_readme = spec_dir / "README.md"
    spec_template = spec_dir / "SCREEN_SPEC_TEMPLATE.md"
    screen_spec = spec_dir / "SYS-01.md"
    shutil.copyfile(REPO_ROOT / "contracts/experience/README.md", contract_readme)
    shutil.copyfile(REPO_ROOT / "contracts/experience/screen-specifications/README.md", spec_readme)
    shutil.copyfile(
        REPO_ROOT / "contracts/experience/screen-specifications/SCREEN_SPEC_TEMPLATE.md",
        spec_template,
    )
    source_spec = REPO_ROOT / "contracts/experience/screen-specifications/SYS-01.md"
    contents = source_spec.read_text(encoding="utf-8")
    contents = re.sub(r"(?m)^design_decision:.*\n", "", contents, count=1)
    screen_spec.write_text(contents, encoding="utf-8")

    monkeypatch.setattr(validator, "ROOT", tmp_path)
    monkeypatch.setattr(validator, "CONTRACT_README", contract_readme)
    monkeypatch.setattr(validator, "SPEC_DIR", spec_dir)
    monkeypatch.setattr(validator, "SPEC_README", spec_readme)
    monkeypatch.setattr(validator, "SPEC_TEMPLATE", spec_template)

    with pytest.raises(AssertionError, match="must declare design_decision"):
        validator._validate_design_gate_contract()
