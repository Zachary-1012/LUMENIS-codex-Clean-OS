from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

EXPECTED_CONTRACT_ID = "lumenis-ggi-cross-product"
EXPECTED_VERSION = "1.1.0"
EXPECTED_FINGERPRINT = "68caa37c3f4a8d50f0c0b77befac0e8ae0c954b63b1a7583a8f822a28eaa690f"
EXPECTED_LOCAL_REPO = "Zachary-1012/LUMENIS-codex-Clean-OS"
CONTRACT_BASENAME = "LUMENIS-GGI-CROSS-PRODUCT-CONTRACT-V1.json"
ONLINE_STATUS_PATH = "00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md"

SIX_ROUND_ASSIGNMENTS = {
    "C1": ("Local Codex", ("data", "collection")),
    "C2": ("Local Codex", ("owned ai", "agent")),
    "C3": ("Local Codex", ("cth", "bmp", "business")),
    "C4": ("Local Codex", ("original pitch", "video", "podcast")),
    "C5": (
        "Local Codex",
        ("importer", "research", "reporting", "artifact", "notification"),
    ),
    "C6": ("Local Codex", ("integration", "runtime", "release")),
}

ROUND_COVERAGE = {
    "R01": {"M", "W6"},
    "R02": {"M", "W6"},
    "R03": {"C1", "C6"},
    "R04": {"C1", "C2", "C5", "C6"},
    "R05": {"C1", "C2", "C6"},
    "R06": {"C1", "C6", "F"},
    "R07": {"C2", "C4", "C5"},
    "R08": {"C6", "F"},
    "R09": {"C1", "C2", "C3", "C5", "C6", "F"},
    "R10": {"C1", "C3"},
    "R11": {"C2", "C3", "C4", "C5"},
    "R12": {"C1", "C2", "C3"},
    "R13": {"C2", "C3", "C4", "C5"},
    "R14": {"C1", "C2", "C5", "C6", "F"},
    "R15": {"C6", "M", "PO"},
}

JOB_COVERAGE = {
    "J1": {"C1", "C6"},
    "J2": {"C3"},
    "J3": {"C3"},
    "J4": {"C4"},
    "J5": {"C4"},
    "J6": {"C4"},
    "J7": {"C2"},
    "J8": {"C6", "F"},
}

JOB_ASSERTIONS_HEADING = "### Current J/U job assertions — M clarification, 2026-10-02"
JOB_ASSERTION_COVERAGE = {
    identifier: set(owners.split())
    for identifier, owners in {
        "J1": "C1 C6", "J2": "C3 C1 C2 C5", "J3": "C3 C1 C2 C5",
        "J4": "C4 C2 C5 F", "J5": "C4 C2 C5 F", "J6": "C4 C2 C5 F",
        "J7": "C2 C5", "J8": "C6 F",
        "U01": "C1 C6 F", "U02": "C1 C3", "U03": "C1 C3 F",
        "U04": "C1 C6", "U05": "C1 C6", "U06": "C3 C1 C5 F",
        "U07": "C3 C1 C2 C5", "U08": "C3 C1 C2 C5", "U09": "C3 C2 C5",
        "U10": "C3 C1 C2 C5", "U11": "C3 C1 C2 C5", "U12": "C3 C2 C4 C5 F",
        "U13": "C4 C2 C5 F", "U14": "C4 C2 C5 F", "U15": "C4 C2 C5 F",
        "U16": "C5 C2 C1", "U17": "C5 C2 C3 C4", "U18": "C2 C3 C4 C5 C6",
        "U19": "C2 C6", "U20": "C2 C3 C4 C5", "U21": "C1 C6 F",
        "U22": "C6 C1 C2 C5 F", "U23": "C6 F", "U24": "C5 C6 F",
        "U25": "C6 M PO",
    }.items()
}


def _requires_online_progress(path: str) -> bool:
    if path == "AGENTS.md" or path.startswith(
        (
            ".github/workflows/",
            "account/",
            "agent_",
            "app/",
            "contracts/",
            "lumenis/",
            "scripts/",
            "tests/",
            "website/",
            "00-GOVERNANCE/evidence/round-",
            "00-GOVERNANCE/LUMENIS-ROUND-",
        )
    ):
        return True
    return "/" not in path and path.endswith(
        (".py", ".ps1", ".json", ".toml", ".yaml", ".yml")
    )


def _assert_online_progress_for_paths(changed_paths: set[str]) -> None:
    delivered_paths = sorted(
        path for path in changed_paths if _requires_online_progress(path)
    )
    if delivered_paths and ONLINE_STATUS_PATH not in changed_paths:
        raise AssertionError(
            "source/round evidence changed without CURRENT online progress in "
            f"the same commit: {delivered_paths[:12]}"
        )


def _assert_head_online_progress() -> None:
    result = subprocess.run(
        [
            "git",
            "diff-tree",
            "--root",
            "--first-parent",
            "--no-commit-id",
            "--name-only",
            "-r",
            "HEAD",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(
            "cannot verify CURRENT online progress against HEAD: "
            f"{result.stderr.strip()}"
        )
    _assert_online_progress_for_paths(set(result.stdout.splitlines()))

PATHS = {
    "agents": ROOT / "AGENTS.md",
    "readme": ROOT / "README.md",
    "takeover": ROOT / "00-GOVERNANCE" / "LUMENIS-CODEX-TAKEOVER-CURRENT.md",
    "architecture": ROOT / "00-GOVERNANCE" / "LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md",
    "experience": ROOT / "00-GOVERNANCE" / "LUMENIS-EXPERIENCE-CONSTITUTION.md",
    "surface_decision": ROOT / "00-GOVERNANCE" / "LUMENIS-MULTI-SURFACE-DECISION-CURRENT.md",
    "source_index": ROOT / "00-GOVERNANCE" / "LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md",
    "real_delivery_overlay": ROOT / "00-GOVERNANCE" / "LUMENIS-REAL-DELIVERY-OVERLAY-CURRENT.md",
    "global_universe_contract": ROOT / "00-GOVERNANCE" / "LUMENIS-GLOBAL-UNIVERSE-CONTEXT-DATA-MATURITY-CURRENT.md",
    "round02_charter": ROOT / "00-GOVERNANCE" / "LUMENIS-ROUND-02-CHARTER-CURRENT.md",
    "round02_frontier_research": ROOT / "00-GOVERNANCE" / "evidence" / "round-02" / "ROUND-02-CONTINUOUS-FRONTIER-RESEARCH.md",
    "launch_plan": ROOT / "00-GOVERNANCE" / "LAUNCH-CONVERGENCE-MASTER-PLAN-V1.md",
    "experience_contracts": ROOT / "contracts" / "experience" / "README.md",
    "skill_current_truth": ROOT / ".agents" / "skills" / "lumenis-current-truth" / "SKILL.md",
    "skill_task_router": ROOT / ".agents" / "skills" / "lumenis-task-router" / "SKILL.md",
    "skill_release_completion": ROOT / ".agents" / "skills" / "lumenis-release-completion" / "SKILL.md",
    "skill_progressive_context": ROOT / ".agents" / "skills" / "lumenis-progressive-context" / "SKILL.md",
    "skill_ai_agent": ROOT / ".agents" / "skills" / "lumenis-ai-agent" / "SKILL.md",
    "registry": ROOT / "00-GOVERNANCE" / "CROSS-REPO-CANONICAL-REGISTRY-V1.md",
    "contract": ROOT / "00-GOVERNANCE" / CONTRACT_BASENAME,
    "platform_workflow": ROOT / ".github" / "workflows" / "platform-verify.yml",
}


def _read(name: str) -> str:
    path = PATHS[name]
    if not path.is_file():
        raise AssertionError(f"missing required takeover/governance file: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def _require(text: str, *needles: str, label: str) -> None:
    normalized = re.sub(r"\s+", " ", text)
    missing = [needle for needle in needles if re.sub(r"\s+", " ", needle) not in normalized]
    if missing:
        raise AssertionError(f"{label} missing required current markers: {missing}")


def _require_collapsed(text: str, *needles: str, label: str) -> None:
    _require(re.sub(r"\s+", " ", text), *needles, label=label)


def _routing_rows(text: str) -> dict[str, str]:
    rows: dict[str, str] = {}
    for line in text.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        match = re.search(r"\b(C[1-6])\s*/\s*W([1-6])\b", line)
        if not match:
            continue
        round_id, window_number = match.groups()
        if round_id != f"C{window_number}":
            raise AssertionError(
                f"six-round routing mismatch: {round_id} must map to W{round_id[1:]}"
            )
        if round_id in rows:
            raise AssertionError(f"six-round routing duplicates {round_id}/W{window_number}")
        rows[round_id] = line
    return rows


def _assert_six_round_routing(agents: str) -> None:
    rows = _routing_rows(agents)
    missing = sorted(set(SIX_ROUND_ASSIGNMENTS) - set(rows))
    extra = sorted(set(rows) - set(SIX_ROUND_ASSIGNMENTS))
    if missing or extra:
        raise AssertionError(
            f"AGENTS.md six-round execution matrix mismatch: missing={missing}, extra={extra}"
        )

    for round_id, (environment, terms) in SIX_ROUND_ASSIGNMENTS.items():
        line = rows[round_id].casefold()
        if environment.casefold() not in line:
            raise AssertionError(
                f"{round_id} must use {environment} in its canonical AGENTS.md row"
            )
        missing_terms = [term for term in terms if term not in line]
        if missing_terms:
            raise AssertionError(
                f"{round_id} row is missing its approved responsibilities: {missing_terms}"
            )

    lowered = re.sub(r"\s+", " ", agents).casefold()
    frontend_route = (
        "front-end window f" in lowered
        and ("all six deliveries" in lowered or "all six rounds" in lowered)
    )
    if not frontend_route:
        raise AssertionError("AGENTS.md must route front-end window F through all six deliveries")
    if not re.search(r"root (?:sol )?controller m", lowered) or "review" not in lowered or "acceptance" not in lowered:
        raise AssertionError("AGENTS.md must identify root M as Sol/Astra's review and acceptance role")
    if "only repository execution router" not in lowered:
        raise AssertionError("AGENTS.md must remain the only repository execution router")


def _assert_current_round_statuses(current: str) -> None:
    rows = _routing_rows(current)
    missing = sorted(set(SIX_ROUND_ASSIGNMENTS) - set(rows))
    extra = sorted(set(rows) - set(SIX_ROUND_ASSIGNMENTS))
    if missing or extra:
        raise AssertionError(
            f"CURRENT status table must report C1–C6 exactly once: missing={missing}, extra={extra}"
        )
    _require(
        current,
        "AGENTS.md",
        "LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md",
        label="CURRENT six-round snapshot",
    )


def _mapping_tokens(text: str) -> set[str]:
    tokens = {f"C{value}" for value in re.findall(r"\bC([1-6])\b", text)}
    tokens.update(f"W{value}" for value in re.findall(r"\bW([1-6])\b", text))
    tokens.update(re.findall(r"\b[FM]\b", text))
    if re.search(r"\bProduct Owner\b", text, flags=re.IGNORECASE):
        tokens.add("PO")
    return tokens


def _split_job_assertions(source_index: str, *, required: bool) -> tuple[str, str | None]:
    lines = source_index.splitlines()
    starts = [i for i, line in enumerate(lines) if line.strip() == JOB_ASSERTIONS_HEADING]
    if not starts and not required:
        return source_index, None
    if len(starts) != 1:
        raise AssertionError("Source Owner Index requires exactly one current J/U assertion section")
    start = starts[0]
    end = next(
        (i for i in range(start + 1, len(lines)) if re.match(r"^#{1,3}\s", lines[i])),
        len(lines),
    )
    return "\n".join(lines[:start] + lines[end:]), "\n".join(lines[start + 1:end])


def _assert_job_assertions(section: str, primary_mapping: dict[str, set[str]]) -> None:
    observed: set[str] = set()
    for line in section.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        identifier = cells[0].strip("`* ")
        if identifier == "ID" or all(re.fullmatch(r":?-+:?", cell) for cell in cells):
            continue
        if identifier not in JOB_ASSERTION_COVERAGE:
            raise AssertionError(f"Unexpected current job assertion ID {identifier!r}")
        if identifier in observed:
            raise AssertionError(f"Duplicate current job assertion {identifier}")
        observed.add(identifier)
        if len(cells) != 4:
            raise AssertionError(f"Current job assertion {identifier} requires four fields")
        for field in (cells[1], cells[3]):
            if field.strip("`* ").upper() in {"", "UNKNOWN", "NA", "N/A", "PENDING", "TBD", "-"}:
                raise AssertionError(f"Current job assertion {identifier} has an empty/placeholder label or outcome")
        owners = _mapping_tokens(cells[2])
        if re.search(r"\bPO\b", cells[2]):
            owners.add("PO")
        invalid = set(re.findall(r"\b[CW]\d+\b", cells[2])) - {
            f"{prefix}{number}" for prefix in ("C", "W") for number in range(1, 7)
        }
        if invalid:
            raise AssertionError(f"Current job assertion {identifier} has invalid owners {sorted(invalid)}")
        required_owners = JOB_ASSERTION_COVERAGE[identifier] | primary_mapping.get(identifier, set())
        missing = required_owners - owners
        if missing:
            raise AssertionError(f"Current job assertion {identifier} omits owners {sorted(missing)}")
    missing = set(JOB_ASSERTION_COVERAGE) - observed
    if missing:
        raise AssertionError(f"Missing current job assertions: {sorted(missing)}")


def _assert_legacy_coverage_mapping(source_index: str, *, require_assertions: bool = False) -> None:
    legacy, assertions = _split_job_assertions(source_index, required=require_assertions)
    observed: dict[str, set[str]] = {}
    for line in legacy.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        first_cell = cells[0].strip("`* ")
        identifiers = re.findall(r"\bR(?:0[1-9]|1[0-5])\b|\bJ[1-8]\b", first_cell)
        if not identifiers:
            continue
        mapping = _mapping_tokens(" ".join(cells[1:]))
        for identifier in identifiers:
            if identifier in observed:
                raise AssertionError(f"Source Owner Index duplicates coverage mapping {identifier}")
            observed[identifier] = mapping

    expected = {**ROUND_COVERAGE, **JOB_COVERAGE}
    missing = sorted(set(expected) - set(observed))
    extra = sorted(set(observed) - set(expected))
    if missing or extra:
        raise AssertionError(
            f"Source Owner Index legacy coverage map mismatch: missing={missing}, extra={extra}"
        )
    for identifier, required_tokens in expected.items():
        missing_tokens = sorted(required_tokens - observed[identifier])
        if missing_tokens:
            raise AssertionError(
                f"Source Owner Index {identifier} coverage omits {missing_tokens}"
            )
    if assertions is not None:
        _assert_job_assertions(assertions, observed)


def _assert_execution_boundaries(agents: str) -> None:
    required = (
        "fixed base SHA",
        "approved minimal/public sample inputs",
        "never upload secrets",
        "Cookies",
        "private sessions",
        "complete production database",
        "must not create a branch",
        "open a PR",
        "directly push main",
        "or deploy",
        "W6 applies that exact patch",
        "local runtime/E2E validation",
        "do not call, auto-discover, probe, fall back to, or reactivate them",
        "legacy Ollama/local-model-provider, Zhipu",
        "Jev",
        "interfaces and historical artifacts",
        "The Product Owner performs the repeated core-job acceptance only after engineering is fully operable",
        "development window E2E does not mark USER_VERIFIED, RELEASED or OPERATING",
    )
    normalized = re.sub(r"\s+", " ", agents)
    missing = [term for term in required if term.casefold() not in normalized.casefold()]
    if missing:
        raise AssertionError(f"AGENTS.md six-round execution boundaries missing: {missing}")

    obsolete_active_routes = (
        "Product Owner's parallelism target is ten",
        "ten is also the approved operating ceiling",
        "Use OpenCode with the configured Zhipu provider first",
        "Use Ollama first",
    )
    present = [phrase for phrase in obsolete_active_routes if phrase in normalized]
    if present:
        raise AssertionError(f"AGENTS.md contains obsolete active execution routes: {present}")


def _assert_readme_routing_consistent(readme: str) -> None:
    obsolete_routes = (
        "15 个顺序 Codex 任务",
        "Ollama 与获批候选 Jev 均位于单一 SYSTEM AI Gateway 边界内",
    )
    present = [phrase for phrase in obsolete_routes if phrase in readme]
    if present:
        raise AssertionError(f"README.md contains obsolete execution/provider routes: {present}")


def _assert_single_machine_contract() -> None:
    canonical = PATHS["contract"].resolve()
    copies = sorted(
        path.resolve()
        for path in ROOT.rglob(CONTRACT_BASENAME)
        if path.resolve() != canonical
    )
    if copies:
        relative = [str(path.relative_to(ROOT.resolve())) for path in copies]
        raise AssertionError(
            "duplicate live machine contract copies are forbidden; "
            f"canonical={canonical.relative_to(ROOT.resolve())}; duplicates={relative}"
        )


def validate() -> None:
    agents = _read("agents")
    readme = _read("readme")
    takeover = _read("takeover")
    architecture = _read("architecture")
    experience = _read("experience")
    surface_decision = _read("surface_decision")
    source_index = _read("source_index")
    real_delivery_overlay = _read("real_delivery_overlay")
    global_universe_contract = _read("global_universe_contract")
    round02_charter = _read("round02_charter")
    round02_frontier_research = _read("round02_frontier_research")
    launch_plan = _read("launch_plan")
    experience_contracts = _read("experience_contracts")
    skill_current_truth = _read("skill_current_truth")
    skill_task_router = _read("skill_task_router")
    skill_release_completion = _read("skill_release_completion")
    skill_progressive_context = _read("skill_progressive_context")
    skill_ai_agent = _read("skill_ai_agent")
    registry = _read("registry")
    platform_workflow = _read("platform_workflow")
    contract = json.loads(_read("contract"))

    _assert_single_machine_contract()
    _assert_six_round_routing(agents)
    _assert_current_round_statuses(takeover)
    _assert_legacy_coverage_mapping(source_index, require_assertions=True)
    _assert_execution_boundaries(agents)
    _assert_readme_routing_consistent(readme)

    assert contract["contract_id"] == EXPECTED_CONTRACT_ID
    assert contract["contract_version"] == EXPECTED_VERSION
    assert contract["protocol_fingerprint_sha256"] == EXPECTED_FINGERPRINT
    assert contract["status"] == "ACTIVE"
    assert contract["canonical_registry"][EXPECTED_LOCAL_REPO]["truth_owner"] == "Production Truth"

    _require(
        registry,
        "Effective protocol: **lumenis-ggi-cross-product v1.1.0**",
        "version     = 1.1.0",
        f"fingerprint = {EXPECTED_FINGERPRINT}",
        "序境 / LUMENIS · Production Core",
        "序蕴 / LUMENIS Intelligence",
        "序衍 / LUMENIS Growth",
        "序枢 / LUMENIS Command",
        "00-GOVERNANCE/LUMENIS-GGI-CROSS-PRODUCT-CONTRACT-V1.json",
        label="cross-repo registry",
    )
    if "version     = 1.0.0" in registry:
        raise AssertionError("cross-repo registry regressed the CURRENT machine contract to v1.0.0")

    _require(
        takeover,
        "Status: **CURRENT EXECUTION ENTRYPOINT / NO-REDISCOVERY**",
        "AGENTS.md",
        "00-GOVERNANCE/CROSS-REPO-CANONICAL-REGISTRY-V1.md",
        "00-GOVERNANCE/LUMENIS-GGI-CROSS-PRODUCT-CONTRACT-V1.json",
        "00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md",
        "00-GOVERNANCE/LUMENIS-REAL-DELIVERY-OVERLAY-CURRENT.md",
        "00-GOVERNANCE/LUMENIS-GLOBAL-UNIVERSE-CONTEXT-DATA-MATURITY-CURRENT.md",
        "git rev-parse origin/main",
        "version     = 1.1.0",
        EXPECTED_FINGERPRINT,
        "verify_codex_takeover_governance.py",
        "only repository execution router",
        "Online reader's current-state snapshot",
        "The local working tree is not visible to a reader",
        "same delivery cycle",
        "DESIGN_READY",
        label="CURRENT takeover",
    )
    for stale_claim in (
        "ROUND 02 starts only in a new Sol-controlled task",
        "Public Website, Flutter Web Workspace and Jev implementation are absent until their scheduled rounds",
    ):
        if stale_claim in takeover:
            raise AssertionError(f"CURRENT takeover contains stale status claim: {stale_claim}")

    _require(
        architecture,
        "CANONICAL / SOLE PRODUCT ARCHITECTURE AUTHORITY",
        "DESIGN_EXPLORATION",
        "DESIGN_READY",
        "implementation from a PDF, screenshot, fixture, Figma frame",
        label="CURRENT product architecture",
    )

    _require(
        experience,
        "CANONICAL / SOLE EXPERIENCE DESIGN AUTHORITY",
        "Internal version: **3.2**",
        "DESIGN_EXPLORATION",
        "DESIGN_READY",
        "copied directly into production UI",
        "Sol acceptance decision is `REWORK`",
        "three user-visible language versions",
        label="CURRENT Experience Constitution",
    )

    _require(
        surface_decision,
        "PRODUCT OWNER APPROVED / ARCHITECTURE DECISION",
        "Public Website",
        "Web Workspace",
        "Desktop App",
        "Mobile Companion",
        "Jev product decision",
        "ROUND 07",
        "DESIGN_EXPLORATION",
        "DESIGN_READY",
        label="CURRENT multi-surface decision",
    )

    _require(
        source_index,
        "LUMENIS Source Owner Index",
        "Authority, Only-One and multi-surface decision",
        "Cross-Surface Experience Foundation",
        "Closed-loop internal beta",
        "Product Owner requirement routing check",
        ".opencode/opencode.json",
        "lumenis/system/ai_gateway/",
        "lumenis/system/collector/",
        "Product account and password design remains deferred until product closure reaches 100%",
        "Do not repeat a full-repository audit for normal work",
        "Product Skill Store is a named P0 capability",
        "Product Owner requirement routing check",
        "Chinese, English and Korean",
        "Direct PDF/sketch implementation is `REWORK`",
        "LUMENIS-REAL-DELIVERY-OVERLAY-CURRENT.md",
        "LUMENIS-GLOBAL-UNIVERSE-CONTEXT-DATA-MATURITY-CURRENT.md",
        "LUMENIS_INTERNAL_FULL_UNIVERSE_READY",
        "Cross-round capability gap register",
        label="CURRENT source owner index",
    )

    _require(
        global_universe_contract,
        "CURRENT SUBORDINATE CONTEXT AND DATA-MATURITY CONTRACT",
        "ONE Product",
        "ONE Repository",
        "ONE Product Core",
        "ONE Global Product Universe",
        "ONE Canonical Data",
        "ONE Evidence",
        "ONE Permission",
        "ONE Context Model",
        "ONE Experience Ecosystem",
        "GLOBAL / ALL",
        "ONE INTERNAL EDITION ACCEPTANCE MATRIX",
        "Global Commercial Coverage",
        "Global Brand Coverage",
        "Guangzhou Taikoo Hui Reference Coverage",
        "PRE-LAUNCH GLOBAL FOUNDATION",
        "Measurable maturity matrix",
        "coverage",
        "freshness",
        "completeness",
        "provenance/Evidence",
        "deduplication/entity resolution",
        "source authorization/compliance",
        "failed/stale/blocked ratios",
        "CTH/BMP workflow usability",
        "LUMENIS_INTERNAL_FULL_UNIVERSE_READY = YES",
        "one non-Guangzhou-Taikoo-Hui commercial Subject",
        "one non-Guangzhou-Taikoo-Hui brand Subject",
        "RANDOM ENTITY DATA ACCEPTANCE",
        "sample seed / sample count / sample IDs",
        "non-empty valid result rate",
        "Evidence trace rate",
        "maturity delta since prior round",
        label="CURRENT global universe/context/data-maturity contract",
    )

    _require(
        real_delivery_overlay,
        "CURRENT SUBORDINATE REAL-DELIVERY OVERLAY / NOT A SECOND PRODUCT OR EXPERIENCE AUTHORITY",
        "REAL USER WORK E2E ACCEPTANCE",
        "REAL DELIVERY CARD",
        "ONLINE DELIVERY / LOCAL-TO-MAIN CLOSURE",
        "THREE-LANGUAGE SURFACE ACCEPTANCE",
        "OWNER → CALLER → USER CAPABILITY MATRIX",
        "CURRENT CAPABILITY TRUTH MATRIX",
        "RUNTIME FAILURE MATRIX",
        "PLATFORM LIVE CAPABILITY MATRIX",
        "SURFACE CAPABILITY MATRIX",
        "SCREEN DELIVERY MATRIX",
        "ENGINEERING_READY =",
        "REAL_DATA_READY =",
        "USER_WORKFLOW_READY =",
        "SECURITY_READY =",
        "RELEASE_READY =",
        "OPERATING =",
        "COMMERCIAL_READY =",
        "二十三、全局商业交付补充红线",
        "DATA GOVERNANCE / COMPLIANCE",
        "SECRET / CREDENTIAL GOVERNANCE",
        "CONTRACT / VERSION COMPATIBILITY",
        "DATA RETENTION / BACKUP / DISASTER RECOVERY",
        "TENANT / WORKSPACE LIFECYCLE",
        "COMMERCIAL OPERATIONS",
        "COMMERCIAL READINESS GAP / BLOCKED FOR COMMERCIAL_READY",
        "COMMERCIAL_READY=NO",
        "Global Commercial Coverage",
        "Global Brand Coverage",
        "Guangzhou Taikoo Hui Reference Coverage",
        "LUMENIS_INTERNAL_FULL_UNIVERSE_READY",
        "RANDOM ENTITY DATA ACCEPTANCE",
        "sample seed / sample count / sample IDs",
        "CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION",
        "ADOPT / ADAPT / DEFER / REJECT",
        "RESEARCH COMPLETE / NO JUSTIFIED UPGRADE",
        label="CURRENT real-delivery overlay",
    )
    # Preserve every historical acceptance section; these are coverage, not dispatch.
    for round_number in range(1, 16):
        marker = f"ROUND {round_number:02d}"
        if marker not in real_delivery_overlay:
            raise AssertionError(f"CURRENT real-delivery overlay missing {marker}")

    _require(
        round02_charter,
        "PASS / CLOSED FOR ROUND 02 SCOPE",
        "7781403e2fedcfa8290922f5469dd8d6a365533b",
        "ROUND-02-2026-09-23-CLEAN-MAIN-SYS01-ACCEPTANCE.md",
        "REAL USER WORK E2E ACCEPTANCE",
        "REAL USER JOB",
        "Windows Desktop App",
        "REAL INPUT",
        "END-TO-END PATH",
        "USER-VISIBLE RESULT",
        "FAILURE / RECOVERY",
        "EVIDENCE",
        "ACCEPTANCE ASSERTION",
        "ONE INTERNAL EDITION / context decision",
        "GLOBAL UNIVERSE / DATA MATURITY IMPACT",
        "Global Commercial Coverage",
        "Global Brand Coverage",
        "Guangzhou Taikoo Hui Reference Coverage",
        "LUMENIS_INTERNAL_FULL_UNIVERSE_READY = NO",
        "RANDOM ENTITY DATA ACCEPTANCE",
        "Sample count / IDs",
        "0 / []",
        "CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION",
        "RESEARCH COMPLETE / NO JUSTIFIED UPGRADE",
        "ROUND-02-CONTINUOUS-FRONTIER-RESEARCH.md",
        "REAL DELIVERY CARD",
        "COMMERCIAL OVERLAY IMPACT",
        "COMMERCIAL_READY=NO",
        "Sol final",
        label="ROUND 02 Charter",
    )

    _require(
        round02_frontier_research,
        "ROUND 02 CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION",
        "Flutter adaptive and responsive design",
        "Flutter accessibility testing",
        "W3C Trace Context",
        "OpenTelemetry context propagation",
        "Microsoft Fluent 2",
        "Grafana",
        "ADOPT",
        "ADAPT",
        "DEFER",
        "REJECT",
        "RESEARCH COMPLETE / NO JUSTIFIED UPGRADE",
        label="ROUND 02 continuous frontier research",
    )

    _require(
        launch_plan,
        "SUBORDINATE ROUND 15 LAUNCH GATE / NOT THE TASK-SEQUENCE AUTHORITY",
        "D:\\LUMENIS_REBUILD\\序\\序境",
        "six-round dispatch and complete legacy acceptance coverage",
        label="launch convergence plan",
    )

    _require(
        experience_contracts,
        "DESIGN_EXPLORATION",
        "DESIGN_READY",
        "direct code target",
        "REWORK",
        label="Experience contract router",
    )

    _require_collapsed(
        skill_current_truth,
        "root `AGENTS.md` first",
        "only execution router",
        "C1–C6 local/Codex Cloud assignments",
        "must not depend on workstation-only instructions or skills",
        label="repository current-truth skill",
    )
    _require_collapsed(
        skill_task_router,
        "only repository execution router",
        "six fixed C1–C6 execution rows",
        "without workstation-only skills",
        label="repository task-router skill",
    )
    _require_collapsed(
        skill_release_completion,
        "C1–C6",
        "R01–R15",
        "J1–J8",
        "only after engineering is fully operable",
        "does not mark `USER_VERIFIED`, `RELEASED` or `OPERATING`",
        label="repository release-completion skill",
    )
    _require_collapsed(
        skill_progressive_context,
        "only execution router",
        "C1–C6 rows",
        "Source Owner Index maps",
        "base-SHA",
        "W6 patch-return rules",
        label="repository progressive-context skill",
    )
    _require_collapsed(
        skill_ai_agent,
        "Do not",
        "auto-discover, probe, fall back to, or reactivate local-model or Zhipu",
        "Owned model training and inference belong to C2",
        label="repository AI/Agent skill",
    )

    for required_path in (
        ROOT / ".opencode" / "opencode.json",
        ROOT / "app" / "lib",
        ROOT / "contracts" / "experience",
        ROOT / "lumenis" / "system" / "ai_gateway",
        ROOT / "lumenis" / "system" / "collector",
        ROOT / "lumenis" / "system" / "browser" / "runtime",
        ROOT / "lumenis" / "shared" / "evidence",
        ROOT / "lumenis" / "shared" / "database",
    ):
        if not required_path.exists():
            raise AssertionError(
                "CURRENT source owner path is missing: "
                f"{required_path.relative_to(ROOT)}"
            )

    _require(
        agents,
        "### Mandatory Codex bootstrap",
        "00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md",
        "00-GOVERNANCE/CROSS-REPO-CANONICAL-REGISTRY-V1.md",
        "00-GOVERNANCE/LUMENIS-GGI-CROSS-PRODUCT-CONTRACT-V1.json",
        "00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md",
        "00-GOVERNANCE/LUMENIS-MULTI-SURFACE-DECISION-CURRENT.md",
        "### Six-round execution windows and retained acceptance coverage",
        "### Accepted Batch online-publication gate",
        "Industry Business",
        "only repository execution router",
        "**C1 / W1 — Data and Collection**",
        "**C2 / W2 — Owned AI and Agent**",
        "**C3 / W3 — CTH and BMP Business Workflows**",
        "**C4 / W4 — Original Pitch, Video and Podcast**",
        "**C5 / W5 — Importer, Research and Shared Deliverables**",
        "**C6 / W6 — Integration, Runtime and Release**",
        "The separate front-end window F remains independent across all six deliveries",
        "01a10117-03c7-7503-8a9b-670e80a474a7",
        "Current C3/C5 local continuation and historical Cloud handoff",
        "The root controller M (Sol or Astra",
        "R01–R15 remain the complete acceptance and technical-dependency coverage",
        "J1–J8 remain the mapped source of user-job requirements",
        "Do not add a ten-worker target, hidden helper window, per-leaf stop rule",
        "#### Codex Cloud window constraints",
        "REAL USER WORK E2E ACCEPTANCE — C1 through C6 and mapped R checkpoints",
        "Missing E2E evidence forces REWORK or BLOCKED",
        "REAL USER JOB",
        "USER-VISIBLE RESULT",
        "FAILURE/RECOVERY",
        "ACCEPTANCE ASSERTION",
        "真实用户工作闭环验收",
        "REAL DELIVERY CARD",
        "COMMERCIAL OVERLAY IMPACT",
        "00-GOVERNANCE/LUMENIS-REAL-DELIVERY-OVERLAY-CURRENT.md",
        "00-GOVERNANCE/LUMENIS-GLOBAL-UNIVERSE-CONTEXT-DATA-MATURITY-CURRENT.md",
        "one Product/Core/Data/Evidence/Permission/API/Context/Experience stack",
        "Global Commercial Coverage",
        "Global Brand Coverage",
        "Guangzhou Taikoo Hui Reference Coverage",
        "LUMENIS_INTERNAL_FULL_UNIVERSE_READY=YES",
        "RANDOM ENTITY DATA ACCEPTANCE",
        "sample count zero",
        "CONTINUOUS FRONTIER RESEARCH / CAPABILITY EVOLUTION",
        "ADOPT / ADAPT / DEFER / REJECT",
        "RESEARCH COMPLETE / NO JUSTIFIED UPGRADE",
        "COMMERCIAL_READY=NO",
        "fixtures, mocks, hard-coded examples",
        "DESIGN_EXPLORATION",
        "DESIGN_READY",
        "Sol returns `REWORK`",
        "git rev-parse origin/main",
        "v1.1.0",
        EXPECTED_FINGERPRINT,
        label="root AGENTS.md",
    )

    _require(
        readme,
        "Coding Agent 必须首先读取 [`AGENTS.md`](AGENTS.md)。",
        "Zachary-1012/LUMENIS-codex-Clean-OS",
        label="root README.md",
    )

    # The single Product Gate owns both the cross-product machine contract and
    # Codex takeover consistency. A duplicate standalone workflow is retired.
    _require(
        platform_workflow,
        "verify_lumenis_ggi_contract.py",
        "verify_codex_takeover_governance.py",
        label="platform verify workflow",
    )

    # Dated source-audit SHAs may remain as provenance. What must never regress is
    # the CURRENT takeover path pretending a fixed SHA is the live HEAD.
    if "current HEAD = READ WITH git fetch + git rev-parse origin/main" not in takeover:
        raise AssertionError("CURRENT takeover must resolve origin/main dynamically")

    _assert_head_online_progress()


if __name__ == "__main__":
    validate()
    print(
        "CODEX TAKEOVER GOVERNANCE OK "
        f"{EXPECTED_CONTRACT_ID} v{EXPECTED_VERSION} {EXPECTED_FINGERPRINT} "
        "single-machine-contract=PASS six-round-routing=PASS legacy-coverage=PASS "
        "cloud-boundaries=PASS workflow-guards=PASS online-progress=PASS"
    )
