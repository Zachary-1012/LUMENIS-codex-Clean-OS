"""Authority is paper identity + exact implemented part, never a generic brand label."""

UPSTREAM_REPO = "openai/math"
UPSTREAM_COMMIT = "fd4aeeb2ee4fc729c18d98444fed42fd0529eeeb"
REGISTRY = {
    "102": {
        "relation": "DIRECT_DEFINITION_PORT",
        "path": "lean/ComparatorChallenges/UniqueGamesTheorem.lean",
        "blob": "5e0e18daac92b039a30dc500decc576b91fddb91",
        "symbols": [
            "Foundations.Target.PermutationTable",
            "Constraint.satisfied",
            "countSatisfied",
        ],
        "implemented": "finite permutation-constraint labeling evaluation preserving multiplicities",
        "not_implemented": "hardness reductions, Unique Games theorem proof or approximation algorithm",
    },
    "103": {
        "relation": "DIRECT_FINITE_SEMANTICS_PORT",
        "path": "lean/ComparatorChallenges/LogspaceEquality.lean",
        "blob": "692a4bdc0de7de093d83abdcb7a2bb1ccb7d476b",
        "symbols": [
            "Machine.step",
            "Machine.run",
            "spaceThrough",
            "acceptanceProbability",
        ],
        "implemented": "full finite transition-table semantics within a bounded clock; exact rational coin-law",
        "not_implemented": "asymptotic log-space derandomization machine or L=RL=BPL proof",
    },
    "104": {
        "relation": "DIRECT_POSITIONAL_SPECIALIZATION",
        "path": "lean/ComparatorChallenges/RandomizedMeanPayoff.lean",
        "blob": "cc70577163b98c4489466ec919a6985ee03397f1",
        "symbols": ["Game", "play", "meanPayoff"],
        "implemented": "exact eventual-cycle liminf payoff for specified positional strategy pair",
        "not_implemented": "history-dependent universal winning set, randomized quasipolynomial algorithm",
    },
    "107": {
        "relation": "DIRECT_ARITHMETIC_MODEL_PORT",
        "path": "lean/ComparatorChallenges/MatrixMultiplication.lean",
        "blob": "877d7ee3901c51382cf5bcb059a50d8dbb3cde77",
        "symbols": [
            "Arithmetic.Gate.eval",
            "Gate.cost",
            "Program.eval",
            "MatrixAlgorithm.Correct",
        ],
        "implemented": "division-free program semantics with newest-first registers; rational symbolic identity replay",
        "not_implemented": "the 9/4 exponent construction, fast-GEMM replacement or bit-complexity claim",
    },
    "113": {
        "relation": "DIRECT_PAPER_EQUATION_PORT",
        "path": "preprints/Entropy-and-Face-Dimension-of-the-Perfect-Matching-Polytope-September-23-2026/build/sections/03-entropy.tex",
        "blob": "bf0bc368e2243f9628a8ed7ff175bd5c18f50978",
        "symbols": ["ent:gibbs", "ent:tilt-entropy", "covariance K"],
        "additional_path": "preprints/Entropy-and-Face-Dimension-of-the-Perfect-Matching-Polytope-September-23-2026/build/sections/01-introduction.tex",
        "additional_blob": "14f70966c1e972cfd314f1c610ebc6ed8d6c3f7e",
        "additional_symbols": ["intro:H", "intro:FB", "intro:main-bound"],
        "implemented": "matching Gibbs law/marginals/covariance/entropy and stated pointwise bound; exact finite support, numerical exp/log",
        "not_implemented": "general matching FPRAS, complete face geometry proof; original rational expression enclosures are implemented but do not prove the general theorem or numerical Gibbs equivalence",
    },
    "114": {
        "relation": "DIRECT_PARTITION_MATROID_SPECIALIZATION",
        "path": "lean/ComparatorChallenges/CommonBasesFPRAS.lean",
        "blob": "b03428bbdc26dbe79be12218920c3313a5df5695",
        "symbols": ["ExactOracles", "commonBaseCount"],
        "implemented": "exact common-base count for two structurally valid partition matroids of equal rank",
        "not_implemented": "general independence-oracle FPRAS or polynomial resource guarantee",
    },
    "115": {
        "relation": "DIRECT_PAPER_EQUATION_PORT_WITH_EXPLICIT_FINITE_WRAPPER",
        "path": "preprints/Exact-Uniform-Sampling-of-Contingency-Tables-with-Arbitrary-Margins-September-24-2026/build/sections/algorithms.tex",
        "blob": "878d6bf097d032795e18c38b5c8755b981b9dd13",
        "symbols": [
            "D_XY",
            "eq:offset-count",
            "eq:outer-geometric-law",
            "eq:residual-integers",
            "eq:outer-parameters",
        ],
        "implemented": "exact-rational residual correction + first-success law, translation, finite table support wrapper",
        "not_implemented": "complete dense and small-state sampler, arbitrary-margin polynomial expected-time theorem or cell-bounded FPRAS",
    },
    "139": {
        "relation": "DIRECT_QUADRATIC_SUBFAMILY",
        "path": "lean/ComparatorChallenges/LogConcaveQuery.lean",
        "blob": "bb5e705b7f6a62aee93a071473d7a06d9dc735d3",
        "symbols": ["Admissible", "gibbsDensity", "firstOrderReply"],
        "implemented": "exact admissibility and value/gradient for rational quadratic Hessians I<=A<=2I; numerical density",
        "not_implemented": "general subpolynomial-query sampler or arithmetic/bit bound",
    },
    "140": {
        "relation": "DIRECT_PROJECTION_AND_FIBER_PORT",
        "path": "lean/ComparatorChallenges/PosteriorReplicas.lean",
        "blob": "be840922beb1feff22f51fa3d0c5b1d21f2f2211",
        "symbols": ["rowGram", "liftLabel", "kernelComponent", "baseFiber"],
        "implemented": "exact rational row projections and conditional Gaussian/spherical fiber map; finite-precision random draws",
        "not_implemented": "memory/sample lower-bound proof, Gaussian equal-label integral theorem or LLM-memory theorem",
    },
}


def source_card(family):
    c = dict(REGISTRY[family])
    c["family"] = family
    c["commit"] = UPSTREAM_COMMIT
    c["url"] = f"https://github.com/{UPSTREAM_REPO}/blob/{UPSTREAM_COMMIT}/{c['path']}"
    c["upstream_authorship"] = (
        "OpenAI paper/formal specification; code implementation independently written for this package"
    )
    c["formal_replay"] = (
        "NOT_PERFORMED; ComparatorChallenges contain target statements, not automatic proof evidence"
    )
    c["production_acceptance"] = "NOT_VERIFIED"
    return c

# Exact identities, not keyword or brand matching. These three titles are the
# complete withdrawn set in the reviewed immutable official history. They have
# no mapped operation in the bounded registry above.
HISTORY_COMMIT = "1581d4cbdd69a0faf34b2089614fe2a814316a6a"
HISTORY_URL = f"https://github.com/{UPSTREAM_REPO}/blob/{HISTORY_COMMIT}/history.md"
WITHDRAWN_TITLES = (
    "Algebraicity of Weil classes on split abelian eightfolds",
    "Algebraicity of Kuga–Satake Correspondences for K3 Surfaces",
    "The rational Hodge conjecture for products of K3 surfaces",
)
REVIEW_SOURCE = "openai_math_papers:source_review"
REVIEW_SCHEMA = "lumenis.math-source-review/v1"


def source_identity(path, blob):
    return f"{UPSTREAM_REPO}:{path}@{blob}"


for _family, _entry in REGISTRY.items():
    _entry["manuscript_identity"] = source_identity(_entry["path"], _entry["blob"])
    _entry["dependency_identities"] = (
        [source_identity(_entry["additional_path"], _entry["additional_blob"])]
        if "additional_path" in _entry else []
    )
    _entry["dependency_scope"] = "implemented bounded source fragments; not full-paper theorem dependencies"


def review_snapshot(family, *, connection=None):
    """Read local immutable review evidence only; never fetch on dispatch.

    Missing Evidence storage is a blocker, not permission to forget a persisted
    withdrawal. Empty initialized storage uses the explicit source-code review.
    """
    import json
    from .core import digest, MathInputError
    from lumenis.shared.database import get_repository

    if connection is None:
        import sqlite3
        try:
            with get_repository().connection(read_only=True, wal=False) as con:
                return review_snapshot(family, connection=con)
        except sqlite3.Error as exc:
            raise MathInputError("PAPER_REVIEW_UNAVAILABLE") from exc
    entry = REGISTRY[family]
    identities = [entry["manuscript_identity"], *entry["dependency_identities"]]
    material = {"family": family, "identities": identities, "pin": UPSTREAM_COMMIT,
                "reviewed_history": HISTORY_COMMIT, "status": "REVIEWED_PINNED",
                "freshness": "LOCAL_REVIEW_ONLY_NO_LIVE_FETCH", "reviews": []}
    # The built-in exact title list also applies if a future reviewed mapping
    # explicitly declares a title dependency; no inferred family IDs.
    if any(identity in WITHDRAWN_TITLES for identity in identities):
        material["status"] = "REVOKED"
    rows = connection.execute(
        "SELECT * FROM app_evidence_records WHERE source=? ORDER BY id", (REVIEW_SOURCE,)
    ).fetchall()
    states = {}
    if rows:
        from lumenis.shared.evidence.store import verify_evidence_record_integrity
    for row in rows:
        row = dict(row)
        if not verify_evidence_record_integrity(row):
            raise MathInputError("PAPER_REVIEW_EVIDENCE_INTEGRITY")
        review = json.loads(row["outputs_json"])
        if review.get("schema") != REVIEW_SCHEMA:
            raise MathInputError("PAPER_REVIEW_EVIDENCE_SCHEMA")
        identity = review["identity"]
        if identity not in identities:
            continue
        material["reviews"].append({"id": row["id"], "revision": digest(review)})
        # A failed fetch/new workflow cannot rehabilitate a withdrawn source.
        if states.get(identity) not in {"REVOKED", "REVIEW_REQUIRED"} or review["state"] == "REVOKED":
            states[identity] = review["state"]
    for state in ("UNKNOWN", "REVIEW_REQUIRED", "REVOKED"):
        if state in states.values() and material["status"] != "REVOKED":
            material["status"] = state
    material["review_revision"] = digest(material)
    return material


def assert_review(family, expected=None, *, connection=None):
    from .core import MathInputError
    current = review_snapshot(family, connection=connection)
    if current["status"] != "REVIEWED_PINNED":
        raise MathInputError("PAPER_" + current["status"])
    if expected is not None and expected.get("status") != "REVIEWED_PINNED":
        raise MathInputError("PAPER_OFFLINE_REVIEW_NOT_PUBLISHABLE")
    if expected is not None and current["review_revision"] != expected["review_revision"]:
        raise MathInputError("PAPER_REVIEW_CHANGED")
    return current


def record_source_review(*, identity, state, evidence_url, evidence_sha256,
                         upstream_commit, change_kind, actor, scope, evidence_content):
    """Existing authorized review owner appends signed Evidence, no new store/job.

    The caller supplies already acquired/reviewed upstream evidence. This is not
    a collector and does not interpret an unsuccessful fetch as withdrawal.
    Changes never replace the implementation pin or rewrite historical artifacts.
    """
    import re
    from .core import MathInputError, digest
    import hashlib
    from lumenis.shared.reporting.saved_work import authorize
    from lumenis.shared.database import get_repository
    from lumenis.shared.evidence.store import record_evidence
    from lumenis.system.security import OperationType, get_permission_gate

    known = set(WITHDRAWN_TITLES)
    for entry in REGISTRY.values():
        known.update([entry["manuscript_identity"], *entry["dependency_identities"]])
    if identity not in known or state not in {"REVIEWED_PINNED", "REVIEW_REQUIRED", "UNKNOWN", "REVOKED"}:
        raise MathInputError("PAPER_REVIEW_IDENTITY_OR_STATE")
    if (not re.fullmatch(r"[0-9a-f]{40}", upstream_commit or "")
            or not re.fullmatch(r"[0-9a-f]{64}", evidence_sha256 or "")
            or not evidence_url.startswith(f"https://github.com/{UPSTREAM_REPO}/blob/{upstream_commit}/")
            or change_kind not in {"withdrawal", "source_change", "workflow_only", "fetch_unknown"}):
        raise MathInputError("PAPER_REVIEW_EVIDENCE_REQUIRED")
    if ((change_kind == "withdrawal" and state != "REVOKED")
            or (change_kind == "source_change" and state != "REVIEW_REQUIRED")
            or (change_kind == "fetch_unknown" and state != "UNKNOWN")
            or (change_kind == "workflow_only" and state != "REVIEWED_PINNED")):
        raise MathInputError("PAPER_REVIEW_STATE_MISMATCH")
    if (not isinstance(evidence_content, str) or not 1 <= len(evidence_content.encode()) <= 500_000
            or hashlib.sha256(evidence_content.encode()).hexdigest() != evidence_sha256):
        raise MathInputError("PAPER_REVIEW_CONTENT_HASH")
    evidence = {"schema": REVIEW_SCHEMA, "identity": identity, "state": state,
                "evidence_url": evidence_url, "evidence_sha256": evidence_sha256,
                "upstream_commit": upstream_commit, "change_kind": change_kind,
                "implementation_pin": UPSTREAM_COMMIT}
    with get_repository().connection() as con:
        con.execute("BEGIN IMMEDIATE")
        principal = authorize(actor, scope, action="write", connection=con)
        reviewer = principal.get("principal_ref") or f"actor:{principal['actor_id']}"
        # Bind approval to the existing authenticated identity and normalized
        # scope; another valid actor cannot reuse this review approval.
        evidence.update(reviewer=reviewer, review_scope=principal)
        resource = "math-source-review:" + digest(evidence)
        gate = get_permission_gate()
        if gate.get_valid_approval_token(OperationType.CONFIG_MODIFY.value, resource, exact=True) is None:
            raise PermissionError("PAPER_REVIEW_EXACT_APPROVAL_REQUIRED")
        decision = get_permission_gate().check(
            OperationType.CONFIG_MODIFY, resource=resource,
            caller=reviewer, exact_approval_required=True, domain_id="bmp" if principal["domain_id"] == "zbmp" else "cth")
        if not decision.allowed:
            raise PermissionError("PAPER_REVIEW_PERMISSION_DENIED")
        evidence_id = record_evidence(
            connection=con, source=REVIEW_SOURCE, project="LUMENIS", product="Shared",
            feature_id="G165", outputs=evidence, inputs={"permission": decision.to_dict(), "reviewer": reviewer},
            raw_content=evidence_content, actual=evidence_content,
            result="FAIL" if state == "REVOKED" else "GAP" if state != "REVIEWED_PINNED" else "PASS",
            status="verified" if state != "UNKNOWN" else "pending",
            metric_name="paper_source_review", metric_value=state,
        )
        con.commit()
    return evidence_id
