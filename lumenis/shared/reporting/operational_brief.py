"""Read-only, exact-scope source brief projection over Canonical Data."""

from collections import Counter
import hashlib
import json
from html import escape
import re
import sqlite3
from typing import Any
from urllib.parse import urlsplit

import canonical_data
from .artifact import compute_scoped_content_hash, compute_scoped_scope_key


def _markdown_text(value: str) -> str:
    text = escape(value, quote=False).replace("\r", " ").replace("\n", " ")
    return re.sub(r"([\\`*_{}\[\]()#+\-.!|])", r"\\\1", text)


def _content_evidence_ref(con, row, scope_ref):
    """Carry an explicit original reference; a scope receipt is not source use.

    Importer originals already serve as their own scope Evidence. Collector
    originals have a separate reference in the existing Canonical raw_ref.
    The BusinessBrief owner resolves bytes, scope and use rights afresh.
    """
    raw_ref = row.get("raw_ref")
    if isinstance(raw_ref, str) and raw_ref:
        try:
            declared = json.loads(raw_ref)
        except ValueError:
            declared = None
        if isinstance(declared, dict) and "content_evidence_ref" in declared:
            ref = declared["content_evidence_ref"]
            if isinstance(ref, str) and re.fullmatch(
                r"app_evidence_records:[1-9]\d*", ref
            ):
                return ref
            return None
    # Check the source-specific original metadata rather than infer content
    # authority from a scope signature or Canonical body alone.
    original = con.execute(
        "SELECT asset_id,content_hash,collection_metadata FROM app_evidence_records WHERE id=?",
        (scope_ref,),
    ).fetchone()
    if original is None or str(original[0] or "") != row.get("source_id"):
        return None
    try:
        metadata = json.loads(original[2])
    except (ValueError, TypeError):
        return None
    body = row.get("content")
    if (
        not isinstance(metadata, dict)
        or not metadata.get("source_artifact_ref")
        or not isinstance(body, str)
        or metadata.get("parsed_text") != body
        or hashlib.sha256(body.encode()).hexdigest() != original[1]
    ):
        return None
    return "app_evidence_records:" + str(scope_ref)


def project_profile_research(con, row, scope_ref, *, actor_ref=None):
    """Project typed statements only after the caller verifies this Canonical row.

    The internal Importer marker, original file hash and parsed-body equality
    distinguish an admitted profile compilation from arbitrary JSON text.
    No excerpt occurrence or signature establishes the truth of a claim.
    """
    cursor = con.execute("SELECT * FROM app_evidence_records WHERE id=?", (scope_ref,))
    original = cursor.fetchone()
    if original is None:
        return None
    evidence = dict(zip((item[0] for item in cursor.description), original))
    try:
        metadata = json.loads(evidence["collection_metadata"])
    except (ValueError, TypeError):
        return None
    marker = metadata.get("entity_profile") if isinstance(metadata, dict) else None
    if not isinstance(marker, dict):
        return None
    if not isinstance(actor_ref, str) or not actor_ref:
        return None
    owner = metadata.get("owner")
    if not isinstance(owner, dict):
        raise ValueError("PROFILE_RESEARCH_OWNER_INVALID")
    source_actor_ref = owner.get("principal_ref") or "actor:" + str(
        owner.get("actor_id")
    )
    if source_actor_ref != actor_ref:
        return None
    from lumenis.shared.reporting.saved_work import _verified_evidence

    _verified_evidence(con, int(scope_ref), metadata["context"])
    from lumenis.importer import documents, entity_profiles

    body = row.get("content")
    if (
        marker.get("schema") != entity_profiles.SCHEMA
        or metadata.get("parsed_text") != body
        or evidence["asset_id"] != row.get("source_id")
    ):
        raise ValueError("PROFILE_RESEARCH_SOURCE_BINDING_INVALID")
    manifest = json.loads(body)
    if entity_profiles._digest(manifest) != marker.get("sha256"):
        raise ValueError("PROFILE_RESEARCH_HASH_INVALID")
    evidence["provenance"] = metadata
    raw, _artifact = documents._source_bytes(con, evidence)
    if raw.decode("utf-8") != body:
        raise ValueError("PROFILE_RESEARCH_ORIGINAL_MISMATCH")
    references = []
    for source in manifest["sources"]:
        url, state = _source_url(source["source_url"])
        references.append(
            {
                "source_id": source["id"],
                "url": url,
                "url_state": state,
                "capture_method": source["capture_method"],
                "reviewed_on": source["reviewed_on"],
                "source_as_of": source.get("source_as_of"),
                "temporal_scope_note": source.get("temporal_scope_note"),
                "rights": source["rights"],
            }
        )
    return {
        "kind": "ENTITY_PROFILE_RESEARCH_COMPILATION",
        "version": manifest["version"],
        "references": references,
        "assertions": manifest["assertions"],
        "review": manifest["review"],
        "fact_verification": "NOT_ESTABLISHED",
        "current_validity": "NOT_ESTABLISHED",
        "commercial_reuse": "UNKNOWN",
        "capture_basis": "ASSISTED_WEB_TOOL_TEXT_EXTRACT_NOT_ORIGIN_HTTP_BYTES",
    }


def _source_url(value: Any) -> tuple[str | None, str]:
    if not isinstance(value, str) or not value.strip():
        return None, "UNKNOWN"
    raw = value.strip()
    if len(raw) > 2048 or any(ord(char) < 33 for char in raw):
        return None, "WITHHELD"
    try:
        parsed = urlsplit(raw)
        _ = parsed.port
    except ValueError:
        return None, "WITHHELD"
    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        # Preserve the exact public pagination URL; unknown query material
        # stays withheld rather than being stripped into a different source.
        or ("?" in raw and not re.fullmatch(r"(?:page|p)=[0-9]{1,6}", parsed.query))
        or parsed.fragment
        or "#" in raw
        or any(char in raw for char in '<>"\\`')
        or re.search(r"/[A-Za-z0-9_-]{32,}(?:/|$)", parsed.path)
        or re.search(
            r"(?i)(token|secret|api[-_]?key|auth|session|signature)", parsed.path
        )
    ):
        return None, "WITHHELD"
    return raw, "AVAILABLE"


def _counter(records: list[dict], field: str) -> dict[str, int]:
    values = []
    for record in records:
        value = record.get(field)
        values.append(
            value.strip() if isinstance(value, str) and value.strip() else "UNKNOWN"
        )
    return dict(sorted(Counter(values).items()))


def _analysis_window(body: str, question: str | None) -> tuple[str, dict]:
    """Select a bounded verbatim window, never a generated summary or relevance verdict."""

    def terms(text):
        words = set(re.findall(r"[a-z0-9]{3,}", text.casefold()))
        for run in re.findall(r"[\u3400-\u9fff]+", text):
            words.update(run[index : index + 2] for index in range(len(run) - 1))
        return words - {
            "the",
            "and",
            "for",
            "from",
            "with",
            "this",
            "that",
            "what",
            "should",
        }

    query = terms(question or "")
    start, overlap = 0, set()
    # Keep context contiguous: quotes can be checked against the original body.
    for index in range(0, max(1, len(body) - 1200 + 400), 400):
        candidate = min(index, max(0, len(body) - 1200))
        matched = query & terms(body[candidate : candidate + 1200])
        if len(matched) > len(overlap):
            start, overlap = candidate, matched
    text = body[start : start + 1200]
    return text, {
        "method": "lexical_window/v1",
        "start": start,
        "end": start + len(text),
        "matched_query_terms": len(overlap),
        "semantic_relevance": "NOT_EVALUATED",
    }


def _group_source_records(rows: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        source_id = row.get("source_id")
        if isinstance(source_id, str) and source_id:
            grouped.setdefault(source_id, []).append(row)
    return grouped


def _source_level_record(rows: list[dict]) -> dict | None:
    """Resolve Canonical projections to one exact logical-source record.

    Document imports retain a parent ``document`` row and zero or more signed
    ``document_row`` projections under the same source ID and Evidence. The
    Source Brief remains source-level, so it pins the parent. Other duplicate
    Canonical identities stay ambiguous and fail closed.
    """
    if len(rows) == 1:
        return rows[0]
    if not rows:
        return None
    identity = {
        (
            row.get("scope_evidence_ref"),
            row.get("product_id"),
            row.get("domain_id"),
            row.get("subject_id") or "",
            row.get("brand_focus_id") or "",
        )
        for row in rows
    }
    if len(identity) != 1:
        return None
    parents = [row for row in rows if row.get("source_type") == "document"]
    projections = [row for row in rows if row.get("source_type") == "document_row"]
    if len(parents) == 1 and len(parents) + len(projections) == len(rows):
        return parents[0]
    return None


def build_scoped_source_brief(
    con: sqlite3.Connection,
    *,
    product_id: str,
    global_scope: bool,
    entity_label: str,
    subject_id: str | None = None,
    brand_focus_id: str | None = None,
    limit: int = 30,
    include_analysis_text: bool = False,
    source_ids: list[str] | None = None,
    analysis_question: str | None = None,
    actor_ref: str | None = None,
) -> dict[str, Any]:
    """Build a deterministic source-only brief; label comes from server registry/context."""
    if type(product_id) is not str or product_id not in {"CTH", "ZBMP"}:
        raise ValueError("product_id must be exactly CTH or ZBMP")
    if type(global_scope) is not bool:
        raise TypeError("global_scope must be an explicit boolean")
    if (
        type(entity_label) is not str
        or not entity_label
        or entity_label != entity_label.strip()
    ):
        raise ValueError("entity_label from the server registry/context is required")
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("limit must be an integer between 1 and 100")
    source_ids = canonical_data.validate_source_ids(
        source_ids, limit=min(limit, 8) if include_analysis_text else limit
    )
    if global_scope and (subject_id is not None or brand_focus_id is not None):
        raise ValueError("GLOBAL scope cannot include a focused entity")
    if (
        not global_scope
        and product_id == "CTH"
        and (
            type(subject_id) is not str
            or not subject_id
            or subject_id != subject_id.strip()
            or brand_focus_id is not None
        )
    ):
        raise ValueError("CTH focus requires one exact subject_id only")
    if (
        not global_scope
        and product_id == "ZBMP"
        and (
            type(brand_focus_id) is not str
            or not brand_focus_id
            or brand_focus_id != brand_focus_id.strip()
            or subject_id is not None
        )
    ):
        raise ValueError("ZBMP focus requires one exact brand_focus_id only")

    domain_id = "cth" if product_id == "CTH" else "zbmp"
    focus_key = "subject_id" if product_id == "CTH" else "brand_focus_id"
    focus_id = subject_id if product_id == "CTH" else brand_focus_id
    scope_key = compute_scoped_scope_key(
        domain_id,
        subject_id,
        brand_focus_id,
        global_scope,
        None,
        None,
        "zh-CN",
        "markdown",
    )
    result = canonical_data.list_scoped_canonical(
        con,
        product_id=product_id,
        subject_id=subject_id,
        brand_focus_id=brand_focus_id,
        limit=limit,
        source_ids=source_ids,
        source_level=True,
    )
    source_groups = _group_source_records(result.get("records", []))
    ambiguous_source_count = 0
    if source_ids is not None:
        selected = {}
        for source_id in source_ids:
            rows = source_groups.get(source_id, [])
            primary = _source_level_record(rows)
            if primary is None:
                raise PermissionError("SOURCE_BRIEF_SELECTED_SOURCE_UNAVAILABLE")
            selected[source_id] = primary
        if (
            result.get("candidate_count") != len(source_ids)
            or result.get("rejected_count") != 0
            or result.get("truncated") is True
            or set(source_groups) != set(source_ids)
            or len(selected) != len(source_ids)
        ):
            raise PermissionError("SOURCE_BRIEF_SELECTED_SOURCE_UNAVAILABLE")
        result["records"] = [selected[source_id] for source_id in source_ids]
    else:
        source_records = []
        for rows in source_groups.values():
            primary = _source_level_record(rows)
            if primary is None:
                ambiguous_source_count += 1
                continue
            source_records.append(primary)
        result["records"] = source_records
    counts = {}
    for key in ("candidate_count", "scanned_count", "rejected_count", "returned_count"):
        value = result.get(key)
        if type(value) is not int or value < 0:
            raise RuntimeError(f"scoped Canonical returned invalid {key}")
        counts[key] = value
    if type(result.get("truncated")) is not bool or not isinstance(
        result.get("records"), list
    ):
        raise RuntimeError("scoped Canonical returned an invalid read envelope")

    records = []
    analysis_sources = []
    unsafe_links = 0
    for row in result["records"]:
        proof = row.get("scope_evidence")
        integrity = proof.get("integrity") if isinstance(proof, dict) else None
        stored = proof.get("stored_scope") if isinstance(proof, dict) else None
        scope_ref = row.get("scope_evidence_ref")
        source_id = row.get("source_id")
        if (
            not isinstance(scope_ref, str)
            or not scope_ref.strip()
            or row.get("scope_status") != "VERIFIED"
            or row.get("product_id") != product_id
            or row.get("domain_id") != domain_id
            or not isinstance(integrity, dict)
            or integrity.get("verified") is not True
            or integrity.get("lineage_verified") is not True
            or integrity.get("assurance") != "writer-authenticated"
            or not isinstance(stored, dict)
            or str(proof.get("id")) != str(scope_ref)
            or proof.get("source_id") != source_id
            or not isinstance(source_id, str)
            or not source_id
            or stored.get("product_id") != product_id
            or stored.get("domain_id") != domain_id
            or stored.get("scope_status") != "VERIFIED"
            or stored.get("subject_id", "") != (row.get("subject_id") or "")
            or stored.get("brand_focus_id", "") != (row.get("brand_focus_id") or "")
        ):
            raise RuntimeError(
                "scoped Canonical returned a source without verified scope Evidence"
            )
        if not global_scope and row.get(focus_key) != focus_id:
            raise RuntimeError(
                "scoped Canonical returned a source outside the requested focus"
            )
        title = row.get("title") if isinstance(row.get("title"), str) else ""
        title = "".join(char for char in title if ord(char) >= 32 and ord(char) != 127)
        title_truncated = len(title) > 240
        title = title[:240]
        url, url_status = _source_url(row.get("canonical_url") or row.get("url"))
        unsafe_links += url_status == "WITHHELD"
        publish = row.get("publish_datetime")
        publish = (
            publish.strip() if isinstance(publish, str) and publish.strip() else None
        )
        captured = row.get("captured_at")
        captured = (
            captured.strip() if isinstance(captured, str) and captured.strip() else None
        )
        records.append(
            {
                "source_id": source_id,
                "title": title or None,
                "title_truncated": title_truncated,
                "canonical_id": row.get("canonical_id"),
                "source_url": url,
                "source_link_status": url_status,
                "source_type": row.get("source_type") or "UNKNOWN",
                "source_platform": row.get("source_platform") or "UNKNOWN",
                "publish_datetime": publish,
                "publish_status": "KNOWN" if publish else "UNKNOWN",
                "captured_at": captured,
                "subject_id": row.get("subject_id") or None,
                "brand_focus_id": row.get("brand_focus_id") or None,
                "scope_evidence_ref": scope_ref,
                "evidence_id": str(proof["id"]),
            }
        )
        research = project_profile_research(con, row, scope_ref, actor_ref=actor_ref)
        if research is not None:
            records[-1]["profile_research"] = research
        body = row.get("content")
        if (
            include_analysis_text
            and isinstance(body, str)
            and body.strip()
            and len(analysis_sources) < 8
        ):
            selected_text, selection = _analysis_window(body, analysis_question)
            analysis_sources.append(
                {
                    "source_id": source_id,
                    "evidence_ref": scope_ref,
                    "content_evidence_ref": _content_evidence_ref(con, row, scope_ref),
                    "title": title,
                    "text": selected_text,
                    "truncated": len(body) > len(selected_text),
                    "text_selection": selection,
                    "body_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
                    "publish_datetime": publish,
                    "captured_at": captured,
                    "source_platform": row.get("source_platform") or "UNKNOWN",
                }
            )

    withheld_count = counts["rejected_count"] + unsafe_links + ambiguous_source_count
    truncated = result["truncated"]
    status = (
        "PARTIAL"
        if withheld_count or truncated
        else "AVAILABLE" if records else "EMPTY"
    )
    source_counts, platform_counts = _counter(records, "source_type"), _counter(
        records, "source_platform"
    )
    lines = [
        "# 来源简报",
        f"- 范围：{_markdown_text(entity_label)}",
        f"- 模式：{'GLOBAL / ALL' if global_scope else 'FOCUS'}",
        f"- 结果：{status}",
        "- 覆盖：UNKNOWN",
        "- 新鲜度：UNKNOWN",
        "- 采集状态：UNKNOWN（Canonical 样本不证明是否已采集）",
        f"- 已验证返回样本：{len(records)} 条；来源类型样本计数："
        f"{_markdown_text(str(source_counts))}；平台样本计数：{_markdown_text(str(platform_counts))}",
        f"- 候选 {counts['candidate_count']}；扫描 {counts['scanned_count']}；被拒绝 {counts['rejected_count']}；截断：{truncated}",
        "",
        "## 来源样本",
    ]
    if not records:
        lines.append("- 本次查询未返回可展示的已验证来源；这不表示已采集或覆盖为零。")
    for record in records:
        title = _markdown_text(record["title"] or "UNKNOWN title")
        label = (
            f"[{title}](<{record['source_url']}>)" if record["source_url"] else title
        )
        publish = record["publish_datetime"] or "UNKNOWN"
        captured = record["captured_at"] or "UNKNOWN"
        identity = record["subject_id"] or record["brand_focus_id"] or "UNKNOWN"
        lines.append(
            f"- {label} — platform: {_markdown_text(str(record['source_platform']))}; "
            f"published: {_markdown_text(publish)}; captured: {_markdown_text(captured)}; "
            f"scope: {_markdown_text(identity)}; Evidence: {_markdown_text(str(record['scope_evidence_ref']))}"
        )
        research = record.get("profile_research")
        if research:
            lines.append(
                "  - Profile source statements: "
                + str(len(research["assertions"]))
                + "; independently verified facts: NOT_ESTABLISHED"
            )
            for reference in research["references"]:
                lines.append(
                    "  - Research source: "
                    + _markdown_text(reference["url"] or reference["url_state"])
                    + "; source as of: "
                    + _markdown_text(reference["source_as_of"] or "UNKNOWN")
                )
    markdown = "\n".join(lines)
    result = {
        "status": status,
        "withheld": withheld_count > 0,
        "truncated": truncated,
        "scope": {
            "product_id": product_id,
            "domain_id": domain_id,
            "global": global_scope,
            "subject_id": subject_id,
            "brand_focus_id": brand_focus_id,
            "entity_label": entity_label,
            "scope_key": scope_key,
        },
        "coverage": "UNKNOWN",
        "freshness": "UNKNOWN",
        "collection_state": "UNKNOWN",
        "sample": {
            **counts,
            "returned_verified_count": len(records),
            "truncated": truncated,
            "withheld": withheld_count > 0,
            "withheld_count": withheld_count,
            "source_type_counts_sample": source_counts,
            "platform_counts_sample": platform_counts,
            "counts_basis": "returned verified Canonical records only; not coverage or business metrics",
        },
        "records": records,
        "markdown": markdown,
        "content_hash": compute_scoped_content_hash(markdown),
    }
    if include_analysis_text:
        result["_analysis_sources"] = analysis_sources
    return result


def build_shared_source_brief(*, actor, source_ids=None, limit=30, question=None):
    """Independent private research through existing verified SavedWork custody."""
    from lumenis.shared.reporting.saved_work import authorize_saved_work
    from lumenis.importer.documents import read_private_document_source
    scope = {"scope_kind": "shared_workspace", "version": 1}
    authorize_saved_work(actor, scope, action="read")
    selected = canonical_data.validate_source_ids(source_ids, limit=limit)
    records = [read_private_document_source(ref, actor=actor, scope=scope)
               for ref in selected or []]
    lines = ["# " + _markdown_text(question or "Source review"), ""]
    if not records:
        lines.append("Add permitted source materials to continue. No findings established.")
    markdown = "\n".join(lines)
    return {"status": "source_review_ready" if records else "needs_sources", "scope": scope,
            "coverage": "PARTIAL" if records else "UNKNOWN", "freshness": "UNKNOWN",
            "collection_state": "private_custody", "records": records,
            "sample": {"returned_verified_count": len(records),
                       "verification_basis": "custody_and_bytes_only", "population_count": None},
            "markdown": markdown, "content_hash": hashlib.sha256(markdown.encode()).hexdigest()}
