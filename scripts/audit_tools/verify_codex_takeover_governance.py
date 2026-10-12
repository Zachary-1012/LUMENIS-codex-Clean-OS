from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

EXPECTED_CONTRACT_ID = "lumenis-ggi-cross-product"
EXPECTED_VERSION = "1.1.0"
EXPECTED_FINGERPRINT = "68caa37c3f4a8d50f0c0b77befac0e8ae0c954b63b1a7583a8f822a28eaa690f"
EXPECTED_LOCAL_REPO = "Zachary-1012/LUMENIS-codex-Clean-OS"
CONTRACT_BASENAME = "LUMENIS-GGI-CROSS-PRODUCT-CONTRACT-V1.json"
ENGINEERING_OWNER_IDS = {"C1", "C2", "C3", "C4", "C5", "C6"}

# Historical coverage maps below remain regression evidence; current execution semantics live in the governance machine contract.
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
                f"engineering-owner routing mismatch: {round_id} must map to W{round_id[1:]}"
            )
        if round_id in rows:
            raise AssertionError(f"engineering-owner routing duplicates {round_id}/W{window_number}")
        rows[round_id] = line
    return rows



def _assert_engineering_owner_routing(agents: str) -> None:
    """Human-doc mirror only: keep C1/W1..C6/W6 rows present exactly once.

    Current role responsibilities, environments, dispatch semantics and model routing
    are validated by verify_governance_machine_contract.py from structured sources.
    """
    rows = _routing_rows(agents)
    missing = sorted(ENGINEERING_OWNER_IDS - set(rows))
    extra = sorted(set(rows) - ENGINEERING_OWNER_IDS)
    if missing or extra:
        raise AssertionError(
            f"AGENTS.md human routing mirror mismatch: missing={missing}, extra={extra}"
        )

def _assert_current_round_statuses(current: str) -> None:
    rows = _routing_rows(current)
    missing = sorted(ENGINEERING_OWNER_IDS - set(rows))
    extra = sorted(set(rows) - ENGINEERING_OWNER_IDS)
    if missing or extra:
        raise AssertionError(
            f"CURRENT status table must report C1–C6 exactly once: missing={missing}, extra={extra}"
        )
    _require(
        current,
        "AGENTS.md",
        "LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md",
        label="CURRENT engineering-owner snapshot",
    )


CURRENT_PUBLICATION_STATES = {
    "LOCAL_CANDIDATE_NOT_PUBLISHED",
    "PUBLISHED_SOURCE_VERIFIED",
    "RULES_ONLY_PUBLICATION",
}
CURRENT_RUNTIME_STATES = {"NOT_LOADED_OR_NOT_VERIFIED", "LOADED_AND_VERIFIED"}


def _publication_changed_paths(*, staged: bool = False) -> set[str]:
    command = (["git", "diff", "--cached", "--name-only", "HEAD"] if staged else
               ["git", "diff-tree", "--root", "--first-parent", "--diff-merges=first-parent", "--no-commit-id", "--name-only", "-r", "HEAD"])
    proc = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise AssertionError(f"cannot inspect publication changed paths: {proc.stderr.strip()}")
    return {line.strip() for line in proc.stdout.splitlines() if line.strip()}


def _is_product_behavior_source(path: str) -> bool:
    # Engineering-policy entrypoints, not LUMENIS user/runtime behavior.
    if path in {
        ".codex/hooks/lumenis_hooks.py", ".codex/engineering.py",
        ".codex/local_workflow.py", ".codex/mcp/server.mjs",
        ".codex/tests/test_engineering.py",  # Same engineering owner regression.
        "scripts/production_baseline_check.py", "scripts/lean_footprint.py",
    }:
        return False
    if path.startswith(("00-GOVERNANCE/", "docs/", "tests/", "scripts/audit_tools/", ".github/")):
        return False
    return (
        path.endswith((".py", ".dart", ".ts", ".tsx", ".js", ".mjs"))
        or path.startswith(("app/lib/", "website/src/", "lumenis/"))
    )


def _is_rules_only_publication_path(path: str) -> bool:
    path = path.replace("\\", "/")
    if path in {
        "AGENTS.md",
        "README.md",
        "app/README.md",
        "website/README.md",
        "contracts/experience/README.md",
        ".agents/skills/lumenis-flutter-experience/SKILL.md",
        ".agents/skills/lumenis-progressive-context/SKILL.md",
        "scripts/audit_tools/verify_codex_takeover_governance.py",
        "scripts/audit_tools/verify_lumenis_single_product.py",  # Existing positioning/Only-One governance validator.
        'scripts/production_baseline_check.py',
        'scripts/lean_footprint.py',
        '.codex/hooks/lumenis_hooks.py',
        '.codex/engineering.py',
        '.codex/local_workflow.py',
        '.codex/mcp/server.mjs',
        'scripts/local_development.ps1',
        '.vscode/settings.json',
        '.vscode/tasks.json',
        '.vscode/extensions.json',
        '.codex/README.md',
        # These exact existing files belong to this rule/engineering owner.
        # Arbitrary model configuration, tests or Website behavior remain denied.
        '.codex/model-routing.toml',
        '.codex/tests/test_engineering.py',
        'website/DEVELOPMENT-BRIEF.md',
        '.agents/skills/lumenis-local-engineering-tools/SKILL.md',

        '.github/workflows/platform-verify.yml',
        '.github/workflows/app-verify.yml',
        'tests/CI_TEST_TIERS.md',
        '00-GOVERNANCE/LUMENIS-GOVERNANCE-MACHINE-CONTRACT-V1.json',
        'scripts/audit_tools/verify_governance_machine_contract.py',
        'scripts/audit_tools/verify_ai_native_constitution.py',
        '.agents/skills/lumenis-testing/SKILL.md',
        '.agents/skills/lumenis-release-completion/SKILL.md',

        "tests/test_online_progress_governance.py",
        "tests/test_governance_machine_contract.py",  # This policy owner's regression, not product behavior.
        # These exact JSON files are material/approved-target documentation,
        # not runtime configuration. Keep arbitrary JSON outside this allowlist.
        "00-GOVERNANCE/evidence/round-15/full-product-audit-20261003/MATERIAL-OWNER-MANIFEST.json",
        "contracts/experience/source-target-contract-v1.json",
    }:
        return True
    if path.startswith("00-GOVERNANCE/") and path.endswith(".md"):
        return True
    if path.startswith("00-GOVERNANCE/evidence/approvals/") and path.endswith(".json"):
        return True
    return (
        path.startswith("contracts/experience/screen-specifications/")
        and path.endswith(".md")
    )


def _assert_current_publication_truth(
    current: str, *, changed_paths: set[str] | None = None
) -> None:
    heading = "## 1. Online reader's current-state snapshot"
    if heading not in current:
        raise AssertionError("CURRENT missing current-state snapshot heading")
    section = current.split(heading, 1)[1].split("### Approved D1", 1)[0]
    publication = re.search(
        r"Implementation publication state:\s*`([A-Z_]+)`", section
    )
    runtime = re.search(r"Runtime load state:\s*`([A-Z_]+)`", section)
    if publication is None or publication.group(1) not in CURRENT_PUBLICATION_STATES:
        raise AssertionError("CURRENT requires a valid implementation publication state")
    if runtime is None or runtime.group(1) not in CURRENT_RUNTIME_STATES:
        raise AssertionError("CURRENT requires a valid runtime load state")

    state = publication.group(1)
    if state == "LOCAL_CANDIDATE_NOT_PUBLISHED":
        _require(
            section,
            "not yet part of GitHub main",
            "current protected local candidate only",
            "not published Product Source",
            "Promotion requires one coherent delivery",
            label="CURRENT local-candidate publication truth",
        )
        return

    paths = _publication_changed_paths() if changed_paths is None else set(changed_paths)
    current_path = str(PATHS["takeover"].relative_to(ROOT)).replace("\\", "/")

    if state == "RULES_ONLY_PUBLICATION":
        if runtime.group(1) != "NOT_LOADED_OR_NOT_VERIFIED":
            raise AssertionError(
                "RULES_ONLY_PUBLICATION requires runtime state NOT_LOADED_OR_NOT_VERIFIED"
            )
        if current_path not in paths:
            raise AssertionError(
                "RULES_ONLY_PUBLICATION requires CURRENT co-publication in the same commit"
            )
        if not paths:
            raise AssertionError("RULES_ONLY_PUBLICATION requires changed governance paths")
        disallowed_paths = sorted(
            path for path in paths if not _is_rules_only_publication_path(path)
        )
        if disallowed_paths:
            raise AssertionError(
                "RULES_ONLY_PUBLICATION permits governance/documentation paths only; "
                f"found {disallowed_paths}"
            )
        product_paths = sorted(path for path in paths if _is_product_behavior_source(path))
        if product_paths:
            raise AssertionError(
                "RULES_ONLY_PUBLICATION cannot include product behavior source"
            )
        return

    if current_path not in paths:
        raise AssertionError(
            "PUBLISHED_SOURCE_VERIFIED requires CURRENT co-publication in the same commit"
        )
    product_paths = sorted(path for path in paths if _is_product_behavior_source(path))
    if not product_paths:
        raise AssertionError(
            "PUBLISHED_SOURCE_VERIFIED requires same-commit product behavior source"
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
    """Regression-only: obsolete execution/provider routes must never reappear."""
    obsolete_routes = (
        "Product Owner's parallelism target is ten",
        "ten is also the approved operating ceiling",
        "Use OpenCode with the configured Zhipu provider first",
        "Use Ollama first",
        "ROUND 02 starts only in a new Sol-controlled task",
    )
    normalized = " ".join(agents.split())
    present = [phrase for phrase in obsolete_routes if phrase in normalized]
    if present:
        raise AssertionError(f"AGENTS.md reintroduced obsolete execution routes: {present}")


def _assert_readme_routing_consistent(readme: str) -> None:
    """Regression-only: README cannot revive obsolete routing or freeze a live SHA."""
    obsolete_routes = (
        "15 个顺序 Codex 任务",
        "Ollama 与获批候选 Jev 均位于单一 SYSTEM AI Gateway 边界内",
    )
    present = [phrase for phrase in obsolete_routes if phrase in readme]
    if present:
        raise AssertionError(f"README.md contains obsolete execution/provider routes: {present}")
    if re.search(r"local HEAD\s*==\s*origin/main\s*==\s*[0-9a-f]{8,40}", readme):
        raise AssertionError("README.md must not freeze a current Git SHA; CURRENT/fresh git is authoritative")


def _assert_current_authority_consistency(source_index: str, agents: str) -> None:
    """Regression-only: block stale route text that can resurrect retired execution."""
    normalized = " ".join(source_index.split())
    stale_current = (
        "current AGENTS instruction authorizes M-only product-source repairs",
        "The current task authorizes M-only source repair",
        "no other window is active in this task",
        "without active work in this task",
        "When an owner is later authorized",
        "C3+C5 owns cross-material intake/transfer",
    )
    present = [phrase for phrase in stale_current if phrase.casefold() in normalized.casefold()]
    if present:
        raise AssertionError(
            "Source Owner Index contains stale current execution guidance: "
            f"{present}"
        )
    if "Choose the shortest evidence-supported feasible implementation" in agents:
        raise AssertionError(
            "AGENTS.md reintroduced the retired minimum-subset execution wording"
        )

RETIRED_RULE_PATHS = ('AI_POLICY.md', 'AI_PROVIDER_RUNTIME_POLICY_V1.md', 'ARCHITECTURE.md', 'CAPABILITY_REGISTRY.md', 'COMPLIANCE_BY_DESIGN_RELEASE_GATE_V1.md', 'CURRENT_BASELINE.md', 'DEPLOYMENT.md', 'DOUBAO_GITHUB_UPGRADE_PROTOCOL.md', 'LOCAL_AI_CONTINUOUS_RUNTIME_P0.md', 'LUMENIS_AI_MASTER_UPGRADE_INCREMENT_V1.md', 'LUMENIS_FUNCTION_MAP.md', 'LUMENIS_PRODUCT_ARCHITECTURE_FINAL.md', 'PLATFORM_README.md', 'PROJECT_STATUS.md', 'REBUILD_ROADMAP.md', 'UPGRADE.md', 'USER_GUIDE.md', 'VIDEO_INTELLIGENCE_CONTRACT_V1.md', 'docs/DOUBAO_2200_EXECUTION.md', 'docs/REPOSITORY-FACT-BASELINE.md', 'docs/MASTER_DEVELOPMENT_BASELINE.md', 'docs/UNIFIED_PRODUCTION_ARCHITECTURE_v1.0.md', 'intelligence_library/09_Research-Hub/shared-intelligence/docs/protocols/CHATGPT-INTERVENTION-PROTOCOL.md', 'intelligence_library/09_Research-Hub/shared-intelligence/docs/operations/AI-AUDIT-SCHEDULE.md', 'intelligence_library/09_Research-Hub/shared-intelligence/docs/operations/DOUBAO-HANDOFF-R-2026-0002.md', 'intelligence_library/09_Research-Hub/shared-intelligence/protocols/CONTINUOUS-RESEARCH-AND-DEVELOPMENT-POLICY.md', 'intelligence_library/09_Research-Hub/shared-intelligence/docs/protocols/AI-WORK-LOG-AND-REALTIME-PUSH-PROTOCOL.md', 'intelligence_library/09_Research-Hub/shared-intelligence/docs/operations/TASK-QUEUE-INTEGRATION-PROTOCOL.md', 'output/final-audit-2026-09-21/LUMENIS_AGENTS_EXECUTION_RULES_2026-09-21.txt', 'intelligence_library/05_Runtime/LOCAL_AI_CONTINUOUS_RUNTIME_P0.md')


def _assert_unique_current_rule_sources() -> None:
    """Reject removed instruction files and copies at root and nested entry paths."""
    present = [rel for rel in RETIRED_RULE_PATHS if (ROOT / rel).exists()]
    copies = [str(copy.relative_to(ROOT)) for rel in RETIRED_RULE_PATHS
              for copy in (ROOT / rel).parent.glob((ROOT / rel).name + ".*")
              if copy.is_file() or copy.is_symlink()]
    if present or copies:
        raise AssertionError(f"retired instruction files remain: {sorted(set(present + copies))}")
    catalog = (ROOT / "lumenis_shared_skills.py").read_text(encoding="utf-8-sig")
    import ast
    tree = ast.parse(catalog)
    values = [ast.literal_eval(node.value) for node in tree.body
              if isinstance(node, ast.Assign) and any(
                  isinstance(t, ast.Name) and t.id == "_LOCAL_RESEARCH" for t in node.targets)]
    if len(values) != 1 or len(values[0]) != len(set(values[0])):
        raise AssertionError("Shared research authority must be unique")
    if any(ref in RETIRED_RULE_PATHS for ref in values[0]):
        raise AssertionError("Shared catalog loads a retired rule source")
    if "00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md" not in values[0]:
        raise AssertionError("Shared catalog omits the current product architecture")



    release_policy = ROOT / "RELEASE_POLICY.md"
    if release_policy.is_file():
        text = release_policy.read_text("utf-8-sig")
        _require_collapsed(
            text,
            "SUPPORTING RELEASE SAFETY POLICY",
            "NO_SCOPE_REDUCTION_ON_RELEASE",
            "SINGLE_PRODUCT_FOUR_SURFACES",
            "C6_W6_RELEASE_OWNER",
            "C6/W6 owns integration/runtime/release",
            label="supporting release safety policy",
        )


def _assert_repository_model_neutrality() -> None:
    """Regression/hygiene only; structured model semantics live in machine governance."""
    required_project_codex = (
        ".codex/config.toml",
        ".codex/model-routing.toml",
        ".codex/README.md",
        ".codex/engineering.py",
        ".codex/mcp/server.mjs",
        ".codex/hooks/lumenis_hooks.py",
        ".codex/hooks.example.json",
        ".codex/rules/lumenis.rules",
        ".codex/tests/test_engineering.py",
    )
    redundant_rule = ROOT / ".codex" / "rules" / "engineering-safety.rules"
    if redundant_rule.exists():
        raise AssertionError(
            "duplicate Codex ExecPolicy is forbidden; keep only .codex/rules/lumenis.rules"
        )
    for rel in required_project_codex:
        proc = subprocess.run(
            ["git", "ls-files", "--error-unmatch", rel],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        if proc.returncode != 0:
            raise AssertionError(
                f"portable Codex project configuration must be tracked on main: {rel}"
            )

    engineering = (ROOT / ".codex" / "engineering.py").read_text("utf-8-sig")
    forbidden_local_helpers = (
        r"D:\\codex\\agent-skills",
        "C:\\Users\\",
        "settings.json",
    )
    present = [token for token in forbidden_local_helpers if token in engineering]
    if present:
        raise AssertionError(
            "portable LUMENIS engineering MCP must not depend on workstation-local "
            f"absolute helper paths: {present}"
        )
    if "def source_read(" not in engineering or "def route_task(" not in engineering:
        raise AssertionError(
            "portable LUMENIS engineering MCP must own its bounded source helpers in-repo"
        )

    dev_ai = ROOT / "scripts" / "dev_ai.py"
    if dev_ai.is_file():
        text = dev_ai.read_text("utf-8-sig")
        forbidden = ("DEFAULT_MODEL", "FALLBACK_MODEL", "glm-4.7", "glm-4.5-air")
        present = [token for token in forbidden if token in text]
        if present:
            raise AssertionError(
                f"retired engineering helper reintroduced default/fallback models: {present}"
            )
        if "RETIRED" not in text or "no default engineering model" not in text:
            raise AssertionError(
                "scripts/dev_ai.py must remain a fail-closed retired compatibility marker"
            )

    env_example = ROOT / ".env.example"
    if env_example.is_file():
        text = env_example.read_text("utf-8-sig")
        for key in ("AI_PROVIDER", "LOCAL_AI_PREFERRED"):
            if re.search(rf"(?m)^\s*{re.escape(key)}\s*=", text):
                raise AssertionError(
                    f".env.example must not define active retired provider selector {key}"
                )
        retired_model_keys = (
            "OLLAMA_MODEL",
            "LMSTUDIO_MODEL",
            "LLAMA_CPP_MODEL",
            "QWEN_MODEL",
            "OPENAI_MODEL",
            "DEEPSEEK_MODEL",
            "ZHIPU_MODEL",
            "ZHIPU_STRONG_MODEL",
            "ARK_MODEL",
        )
        for key in retired_model_keys:
            match = re.search(rf"(?m)^[ \t]*{re.escape(key)}[ \t]*=[ \t]*(.*)$", text)
            if match and match.group(1).strip():
                raise AssertionError(
                    f".env.example retired compatibility model key must stay blank: {key}"
                )

def _assert_single_machine_contract() -> None:
    canonical = PATHS["contract"].resolve()
    copies = []
    excluded_roots = {".git", ".venv", "venv", "vendor", "node_modules", ".pytest_cache", "work"}
    for directory, dirs, files in os.walk(ROOT, onerror=_scan_error):
        current = Path(directory)
        dirs[:] = [name for name in dirs if name != "__pycache__"
                   and not (current == ROOT and name in excluded_roots)]
        if CONTRACT_BASENAME in files:
            path = current / CONTRACT_BASENAME
            if path != PATHS["contract"]:
                copies.append(path)
    if copies:
        relative = [str(path.relative_to(ROOT)) for path in sorted(copies)]
        raise AssertionError(
            "duplicate live machine contract copies are forbidden; "
            f"canonical={canonical.relative_to(ROOT.resolve())}; duplicates={relative}"
        )


def _scan_error(error: OSError) -> None:
    raise error


def validate(*, staged: bool = False) -> None:
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

    _assert_current_authority_consistency(source_index, agents)
    _assert_unique_current_rule_sources()
    _assert_repository_model_neutrality()

    _assert_single_machine_contract()
    _assert_engineering_owner_routing(agents)
    _assert_current_round_statuses(takeover)
    if staged:
        current_path = str(PATHS["takeover"].relative_to(ROOT)).replace("\\", "/")
        staged_current = subprocess.run(
            ["git", "show", f":{current_path}"], cwd=ROOT,
            capture_output=True, text=True, encoding="utf-8", check=False,
        )
        if staged_current.returncode != 0:
            raise AssertionError("cannot read staged CURRENT publication state")
        _assert_current_publication_truth(
            staged_current.stdout, changed_paths=_publication_changed_paths(staged=True)
        )
    else:
        _assert_current_publication_truth(takeover)
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
        "LUMENIS-GOVERNANCE-MACHINE-CONTRACT-V1.json",
        "00-GOVERNANCE/CROSS-REPO-CANONICAL-REGISTRY-V1.md",
        "00-GOVERNANCE/LUMENIS-GGI-CROSS-PRODUCT-CONTRACT-V1.json",
        "00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md",
        "00-GOVERNANCE/LUMENIS-REAL-DELIVERY-OVERLAY-CURRENT.md",
        "00-GOVERNANCE/LUMENIS-GLOBAL-UNIVERSE-CONTEXT-DATA-MATURITY-CURRENT.md",
        "git rev-parse origin/main",
        EXPECTED_FINGERPRINT,
        "Current owner continuation",
        "source-target-contract-v1.json",
        label="CURRENT takeover provenance/mirror",
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
        "Platform-native Source → Source/Evidence/Canonical → LUMENIS presentation → Open Original → Return",
        label="CURRENT product architecture",
    )

    _require(
        experience,
        "CANONICAL / SOLE EXPERIENCE DESIGN AUTHORITY",
        "Internal version: **3.2**",
        "DESIGN_EXPLORATION",
        "DESIGN_READY",
        "copied directly into production UI",
        "M returns `REWORK`",
        "three user-visible language versions",
        "Platform-native SourceTarget / Open Original",
        "LUMENIS SourceTarget v1",
        "SYS-06",
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
        "APPROVED D1–D5 historical-package convergence",
        "EIGHT OWNER RESULT PACKAGES",
        "Production admission = 0",
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
        "OPEN ORIGINAL / SOURCE TARGET ACCEPTANCE",
        "source-target-contract-v1.json",
        "Production admission = 0",
        label="CURRENT real-delivery overlay",
    )
    # Preserve all 15 historical coverage groups without routing them as
    # current execution rounds. C1-C6 are the only current delivery units.
    for group_number in range(1, 16):
        marker = f"HISTORICAL COVERAGE {group_number:02d} ACCEPTANCE"
        if marker not in real_delivery_overlay:
            raise AssertionError(f"CURRENT real-delivery overlay missing {marker}")

    # "Sol final" below is a preservation marker for the dated, closed R02
    # acceptance record. It must not route the current model or controller.
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
        "engineering source responsibility and complete retained acceptance coverage",
        label="launch convergence plan",
    )

    _require(
        experience_contracts,
        "DESIGN_EXPLORATION",
        "DESIGN_READY",
        "direct code target",
        "REWORK",
        "source-target-contract-v1.json",
        "lumenis.source-target/v1",
        label="Experience contract router",
    )

    _require_collapsed(
        skill_current_truth,
        "root `AGENTS.md` first",
        "only execution router",
        "C1–C6 engineering source responsibilities",
        "Actual window, host and model assignment follow the latest direct Product Owner instruction",
        "Cloud restrictions apply only to an explicitly authorized Cloud task",
        "must not depend on workstation-only instructions or skills",
        label="repository current-truth skill",
    )
    _require_collapsed(
        skill_task_router,
        "only repository execution router",
        "C1–C6 are not six product rounds or a fixed local/Cloud assignment",
        "current Product Owner dispatch",
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
        "00-GOVERNANCE/LUMENIS-GOVERNANCE-MACHINE-CONTRACT-V1.json",
        "00-GOVERNANCE/LUMENIS-CODEX-TAKEOVER-CURRENT.md",
        "00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md",
        "00-GOVERNANCE/LUMENIS-MULTI-SURFACE-DECISION-CURRENT.md",
        "00-GOVERNANCE/LUMENIS-REAL-DELIVERY-OVERLAY-CURRENT.md",
        "00-GOVERNANCE/LUMENIS-GLOBAL-UNIVERSE-CONTEXT-DATA-MATURITY-CURRENT.md",
        "00-GOVERNANCE/LUMENIS-GGI-CROSS-PRODUCT-CONTRACT-V1.json",
        "### Engineering source responsibilities and retained acceptance coverage",
        "**C1 / W1 — Data and Collection**",
        "**C2 / W2 — Owned AI and Agent**",
        "**C3 / W3 — CTH and BMP Business Workflows**",
        "**C4 / W4 — Original Pitch, Video and Podcast**",
        "**C5 / W5 — Importer, Research and Shared Deliverables**",
        "**C6 / W6 — Integration, Runtime and Release**",
        "### Accepted Batch online-publication gate",
        label="root AGENTS human governance mirror",
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
        "verify_governance_machine_contract.py",
        "verify_codex_takeover_governance.py",
        label="platform verify workflow regression",
    )

    # Dated source-audit SHAs may remain as provenance. What must never regress is
    # the CURRENT takeover path pretending a fixed SHA is the live HEAD.
    if not all(item in takeover for item in ("git rev-parse HEAD", "git rev-parse origin/main", "HEAD...origin/main", "GitHub main")):
        raise AssertionError("CURRENT takeover must resolve origin/main dynamically")



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--staged", action="store_true",
                        help="Check proposed index co-publication before commit; default checks HEAD")
    validate(staged=parser.parse_args().staged)
    print(
        "CODEX TAKEOVER GOVERNANCE OK "
        f"{EXPECTED_CONTRACT_ID} v{EXPECTED_VERSION} {EXPECTED_FINGERPRINT} "
        "cross-product-contract=PASS human-routing-mirror=PASS legacy-coverage=PASS "
        "historical-authority=PASS retired-route-regressions=PASS workflow-guards=PASS"
    )
