from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NAMING = ROOT / "00-GOVERNANCE" / "CANONICAL-NAMING-AND-TWIN-SYNC.md"
CANONICAL_LAUNCHER = ROOT / "scripts" / "start-lumenis-autostart.cmd"
LEGACY_LAUNCHER = ROOT / "scripts" / "start-zbrand-autostart.cmd"
HISTORICAL_DOCUMENTS = (
    ROOT / "docs" / "ZBRAND_INTELLIGENCE_REPORTING_SPEC.md",
    ROOT / "docs" / "Z-Brand双产品线最终基线_V1.0.docx",
    ROOT
    / "intelligence_library"
    / "09_Research-Hub"
    / "engineering研究"
    / "Z-BRAND-INTEGRATION.md",
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def assert_real_exit_code_is_returned(text: str) -> None:
    assert re.search(r'set\s+"exitCode=%ERRORLEVEL%"', text, re.IGNORECASE)
    assert re.search(
        r"endlocal\s*&\s*exit\s+/b\s+%exitCode%",
        text,
        re.IGNORECASE,
    )


def test_canonical_autostart_is_repository_relative_and_preserves_process_contract() -> None:
    text = read(CANONICAL_LAUNCHER)

    assert "chcp 65001 >nul" in text
    assert "-WindowStyle Hidden" in text
    assert re.search(
        r'-File\s+"%~dp0start_production\.ps1"',
        text,
        re.IGNORECASE,
    )
    assert_real_exit_code_is_returned(text)


def test_legacy_autostart_only_forwards_to_canonical_entry() -> None:
    text = read(LEGACY_LAUNCHER)

    assert "LEGACY compatibility wrapper" in text
    assert re.search(
        r'call\s+"%~dp0start-lumenis-autostart\.cmd"',
        text,
        re.IGNORECASE,
    )
    assert "start_production.ps1" not in text
    assert_real_exit_code_is_returned(text)


def test_autostart_launchers_do_not_contain_retired_machine_path() -> None:
    retired_path = r"D:\Taikoo-monitor-new".casefold()

    for path in (CANONICAL_LAUNCHER, LEGACY_LAUNCHER):
        assert retired_path not in read(path).casefold(), path


def test_legacy_named_documents_are_explicitly_provenance_only() -> None:
    marker = "HISTORICAL / PROVENANCE ONLY / NOT CURRENT AUTHORITY"
    required_authorities = (
        "LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md",
        "LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md",
    )

    for path in HISTORICAL_DOCUMENTS:
        text = read(path)
        assert marker in text, path
        for authority in required_authorities:
            assert authority in text, (path, authority)
        assert text.index(marker) < 500, path


def test_compatibility_ledger_retains_stable_identifiers_with_migration_gates() -> None:
    text = read(NAMING)
    retained_identifiers = (
        "Z-Brand-Core",
        "product_id=ZBMP",
        "domain_id=zbmp",
        "ZBC_*",
        "zbc_*",
        r"Global\ZBrandCoreLauncher8201",
        "scripts/start-zbrand-autostart.cmd",
    )

    assert "序境 / LUMENIS" in text
    assert "CTH / LUMENIS Commerce Operations" in text
    assert "BMP / LUMENIS Brand & Market" in text
    assert "COMPATIBILITY-KEEP" in text
    assert "| Owner | Why it is retained | Migration gate | Rollback gate |" in text
    for identifier in retained_identifiers:
        assert identifier in text, identifier


def test_ledger_does_not_claim_external_autostart_migration_is_live_verified() -> None:
    text = read(NAMING)

    assert "LIVE_UNVERIFIED" in text
    assert "Task Scheduler" in text
    assert "live Task Scheduler migration" in text
