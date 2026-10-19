"""Deterministic, source-linked drafting within Shared Content & Creation.

No storage, network, model, permission authority or publishing lives here.
All user-authored facts and translations remain subject to human review.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re

SCHEMA = "content-multiplatform:v1"
GENRES = {
    "press_release": ("lead", "detail", "context", "quote", "condition", "action"),
    "media_pitch": ("context", "lead", "detail", "condition", "quote", "action"),
    "editorial_article": ("context", "lead", "detail", "quote", "condition", "action"),
    "social_post": ("lead", "context", "detail", "condition", "quote", "action"),
}
PLATFORMS = ("website", "wechat", "xhs", "weibo", "linkedin", "x", "youtube")
TARGET_LANGUAGES = ("zh-CN", "en", "ko", "ja", "fr", "de", "es", "pt", "it", "ar", "hi", "id")
ROLES = set(GENRES["press_release"])
LABELS = {
    "zh-CN": {"lead": "核心信息", "detail": "详情", "context": "背景", "quote": "引语", "condition": "适用条件", "action": "下一步"},
    "en": {"lead": "Key information", "detail": "Details", "context": "Context", "quote": "Quotation", "condition": "Conditions", "action": "Next step"},
    "ko": {"lead": "핵심 정보", "detail": "세부 내용", "context": "배경", "quote": "인용", "condition": "적용 조건", "action": "다음 단계"},
}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def text_hash(value):
    return hashlib.sha256(value.encode()).hexdigest()


def _text(value, limit=6000):
    if not isinstance(value, str) or not value.strip() or len(value) > limit or "\x00" in value:
        raise ValueError("MULTIPLATFORM_TEXT_INVALID")
    return value


def _identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", value):
        raise ValueError("MULTIPLATFORM_ID_INVALID")
    return value


def capabilities():
    return {"schema": SCHEMA, "genres": list(GENRES), "platforms": list(PLATFORMS),
            "target_languages": list(TARGET_LANGUAGES), "ui_locales": ["zh-CN", "en", "ko"],
            "language_quality": "NOT_VERIFIED", "translation": "USER_SUPPLIED_ONLY",
            "model_used": False, "publication": "NOT_PERFORMED",
            "platform_compliance": "HUMAN_REVIEW_REQUIRED", "template_kind": "composable_fact_structure",
            "capability_scope": "routine_source_linked_templates",
            "creative_workflows": "Existing original ideation, expression and multimodal workflows remain separate; this routine drafting path does not prove creative acceptance."}


def validate_request(value):
    if not isinstance(value, dict) or set(value) != {"title", "brief", "facts", "variants"}:
        raise ValueError("MULTIPLATFORM_REQUEST_INVALID")
    _text(value["title"], 300)
    brief = value["brief"]
    if not isinstance(brief, dict) or set(brief) != {"objective", "audience", "tone"}:
        raise ValueError("MULTIPLATFORM_BRIEF_INVALID")
    for key in ("objective", "audience"):
        _text(brief[key], 2000)
    if brief["tone"] not in {"neutral", "informative", "concise"}:
        raise ValueError("MULTIPLATFORM_TONE_UNSUPPORTED")
    facts, variants = value["facts"], value["variants"]
    if not isinstance(facts, list) or not 1 <= len(facts) <= 20:
        raise ValueError("MULTIPLATFORM_FACTS_REQUIRED")
    ids = set()
    for fact in facts:
        if not isinstance(fact, dict) or set(fact) != {"id", "role", "texts", "citation"}:
            raise ValueError("MULTIPLATFORM_FACT_INVALID")
        fid = _identifier(fact["id"])
        if fid in ids or fact["role"] not in ROLES:
            raise ValueError("MULTIPLATFORM_FACT_INVALID")
        ids.add(fid)
        if not isinstance(fact["texts"], dict) or not fact["texts"] or len(fact["texts"]) > 12:
            raise ValueError("MULTIPLATFORM_FACT_TEXTS_INVALID")
        for locale, text in fact["texts"].items():
            if locale not in TARGET_LANGUAGES:
                raise ValueError("MULTIPLATFORM_LOCALE_UNSUPPORTED")
            _text(text, 4000)
        c = fact["citation"]
        if c is not None:
            if (not isinstance(c, dict) or set(c) != {"evidence_id", "start", "end", "quote"}
                    or type(c["evidence_id"]) is not int or c["evidence_id"] <= 0
                    or type(c["start"]) is not int or type(c["end"]) is not int
                    or not 0 <= c["start"] < c["end"]):
                raise ValueError("MULTIPLATFORM_CITATION_INVALID")
            _text(c["quote"], 4000)
    if not any(f["role"] == "lead" for f in facts):
        raise ValueError("MULTIPLATFORM_LEAD_REQUIRED")
    if not isinstance(variants, list) or not 1 <= len(variants) <= 4:
        raise ValueError("MULTIPLATFORM_VARIANTS_INVALID")
    ids = set()
    for variant in variants:
        if not isinstance(variant, dict) or set(variant) != {"id", "genre", "platform", "locale", "title"}:
            raise ValueError("MULTIPLATFORM_VARIANT_INVALID")
        vid = _identifier(variant["id"])
        if vid in ids or variant["genre"] not in GENRES or variant["platform"] not in PLATFORMS:
            raise ValueError("MULTIPLATFORM_VARIANT_INVALID")
        ids.add(vid)
        if variant["locale"] not in TARGET_LANGUAGES:
            raise ValueError("MULTIPLATFORM_LOCALE_UNSUPPORTED")
        _text(variant["title"], 300)
    return copy.deepcopy(value)


def compose(value, sources):
    """Sources are resolved by the server; linked text is not semantic proof."""
    value = validate_request(value)
    expected = {f["citation"]["evidence_id"] for f in value["facts"] if f["citation"]}
    if set(sources) != expected:
        raise ValueError("MULTIPLATFORM_SOURCE_SET_MISMATCH")
    citations, bindings = [], []
    for fact in value["facts"]:
        c = fact["citation"]
        if c is not None:
            source = sources[c["evidence_id"]]
            if source["text"][c["start"]:c["end"]] != c["quote"] or c["end"] > len(source["text"]):
                raise ValueError("MULTIPLATFORM_SOURCE_LOCATOR_INVALID")
            if c not in citations:
                citations.append(copy.deepcopy(c))
    for eid in sorted(sources):
        bindings.append({k: v for k, v in sources[eid].items() if k != "text"})
    variants = []
    for spec in value["variants"]:
        missing = [f["id"] for f in value["facts"] if spec["locale"] not in f["texts"]]
        item = {**spec, "state": "TRANSLATION_UNAVAILABLE" if missing else "DRAFT",
                "language_quality": "NOT_VERIFIED", "translation_state": "UNAVAILABLE" if missing else "USER_SUPPLIED_TEXT",
                "rendered_locale": None if missing else spec["locale"], "missing_translation_fact_ids": missing,
                "review_status": "HUMAN_PENDING", "body": "", "claims": [], "format_checks": {}}
        if not missing:
            order = GENRES[spec["genre"]]
            facts = sorted(value["facts"], key=lambda f: order.index(f["role"]))
            if value["brief"]["tone"] == "concise":
                separator = "\n"
            else:
                separator = "\n\n"
            chunks = [spec["title"]]
            local_claims = [{"claim_id": spec["id"] + "-title", "text": spec["title"], "start": 0,
                             "end": len(spec["title"]), "fact_id": None, "citation": None,
                             "source_status": "USER_PROVIDED_UNVERIFIED"}]
            length = len(spec["title"])
            for fact in facts:
                label = ""
                if spec["genre"] == "editorial_article" and value["brief"]["tone"] != "concise":
                    label = LABELS.get(spec["locale"], {}).get(fact["role"], "")
                    label = label + "\n" if label else ""
                # No truncation, invented bridge, experience, quote, number or CTA.
                text = fact["texts"][spec["locale"]]
                start = length + len(separator) + len(label)
                chunks.append(label + text)
                length = start + len(text)
                local_claims.append({"claim_id": spec["id"] + "-" + fact["id"], "text": text,
                    "start": start, "end": length, "fact_id": fact["id"], "citation": fact["citation"],
                    "source_status": "SOURCE_LINKED_UNVERIFIED" if fact["citation"] else "USER_PROVIDED_UNVERIFIED"})
            item["body"] = separator.join(chunks)
            item["claims"] = local_claims
            count = len(item["body"])
            item["format_checks"] = {"unicode_code_points": count, "platform_limit_verified": False,
                "reason": "Official platform/account/weighted counting requires review", "truncated": False}
            if spec["platform"] == "x" and count > 280 or spec["platform"] == "youtube" and count > 5000:
                item["state"] = "NEEDS_EDIT"
                item["format_checks"]["reason"] = "Conservative size warning; no content was truncated"
        item["body_sha256"] = text_hash(item["body"])
        variants.append(item)
    package = {"schema": SCHEMA, "request": value, "source_bindings": bindings, "variants": variants,
               "generation": {"recipe": "deterministic-fact-order:v1", "model_used": False,
                              "language_quality": "NOT_VERIFIED", "semantic_support": "HUMAN_REVIEW_REQUIRED"},
               "publication": "NOT_PERFORMED", "review_status": "HUMAN_PENDING"}
    return assemble(package), citations


def assemble(package):
    """Recompute exact combined offsets and all hashes after owner edits."""
    package = copy.deepcopy(package)
    markdown, claims = "", []
    for variant in package["variants"]:
        if not variant["body"]:
            continue
        header = f"## {variant['id']} / {variant['genre']} / {variant['platform']} / {variant['locale']}\n\n"
        prefix = ("\n\n" if markdown else "") + header
        offset = len(markdown) + len(prefix)
        markdown += prefix + variant["body"]
        for claim in variant["claims"]:
            if variant["body"][claim["start"]:claim["end"]] != claim["text"]:
                raise ValueError("MULTIPLATFORM_CLAIM_LOCATOR_INVALID")
            claims.append({"claim_id": claim["claim_id"], "text": claim["text"],
                           "start": claim["start"] + offset, "end": claim["end"] + offset})
        variant["body_sha256"] = text_hash(variant["body"])
    if not markdown:
        raise ValueError("MULTIPLATFORM_TRANSLATION_UNAVAILABLE")
    if len(markdown) > 100000 or len(claims) > 100:
        raise ValueError("MULTIPLATFORM_OUTPUT_TOO_LARGE")
    return {"package": package, "markdown": markdown, "claims": claims}


def validate_saved(document):
    payload = document["payload"]
    package = payload.get("multiplatform")
    if not isinstance(package, dict) or package.get("schema") != SCHEMA:
        raise ValueError("MULTIPLATFORM_OWNER_REQUIRED")
    validate_request(package["request"])
    assembled = assemble(package)
    expected = [{k: c[k] for k in ("claim_id", "text", "start", "end")} for c in payload["claims"]]
    if (assembled["markdown"] != document["markdown"] or assembled["claims"] != expected
            or assembled["package"] != package):
        raise ValueError("MULTIPLATFORM_DOCUMENT_INTEGRITY_INVALID")
    return package


def revise(package, edits):
    """User replaces selected versions explicitly. Entire edited body is unverified.

    This deliberately does not guess which new prose is factual. Review must
    account for the whole changed body and enumerate its factual coverage.
    """
    package = copy.deepcopy(package)
    if not isinstance(edits, list) or not 1 <= len(edits) <= 4:
        raise ValueError("MULTIPLATFORM_EDITS_REQUIRED")
    variants = {v["id"]: v for v in package["variants"]}
    seen = set()
    for edit in edits:
        if not isinstance(edit, dict) or set(edit) != {"variant_id", "expected_body_sha256", "body"}:
            raise ValueError("MULTIPLATFORM_EDIT_INVALID")
        vid = edit["variant_id"]
        if vid not in variants or vid in seen:
            raise ValueError("MULTIPLATFORM_EDIT_INVALID")
        seen.add(vid)
        v = variants[vid]
        if v["state"] == "TRANSLATION_UNAVAILABLE":
            raise ValueError("MULTIPLATFORM_TRANSLATION_INPUT_REQUIRED")
        if edit["expected_body_sha256"] != v["body_sha256"]:
            raise ValueError("MULTIPLATFORM_EDIT_CONFLICT")
        body = _text(edit["body"], 20000)
        v["body"] = body
        v["claims"] = [{"claim_id": vid + "-edited", "text": body, "start": 0, "end": len(body),
                        "fact_id": None, "citation": None, "source_status": "USER_EDITED_UNVERIFIED"}]
        v["state"] = "DRAFT"
        v["authorship"] = "USER_EDITED; all claims require fresh review"
        v["format_checks"] = {"unicode_code_points": len(body), "platform_limit_verified": False,
                              "truncated": False, "reason": "Edited content requires format review"}
        if v["platform"] == "x" and len(body) > 280 or v["platform"] == "youtube" and len(body) > 5000:
            v["state"] = "NEEDS_EDIT"
    return assemble(package)


def differences(old, new):
    before, after = {v["id"]: v for v in old["variants"]}, {v["id"]: v for v in new["variants"]}
    return [{"variant_id": vid, "before_sha256": before.get(vid, {}).get("body_sha256"),
             "after_sha256": after.get(vid, {}).get("body_sha256"),
             "before_body": before.get(vid, {}).get("body", ""), "after_body": after.get(vid, {}).get("body", ""),
             "semantic_change_assessed": False}
            for vid in sorted(set(before) | set(after)) if before.get(vid) != after.get(vid)]


def read_variant(binding, *, actor, scope, connection):
    """Typed consumer for the existing Analysis owner, without a Flask context.

    Read both Content and SavedWork authorization, the exact signed producer
    receipt and currently authorized source versions. Never trust copied JSON.
    """
    from lumenis.shared.reporting import saved_work
    from shared_artifacts import _authorize_content_project, _content_artifact_context
    import content_generation as content
    aid = binding["artifact_id"]
    work = saved_work.read_committed_work(aid, actor=actor, scope=scope, connection=connection)
    if work["artifact"]["sha256"] != binding["sha256"] or work["document"]["version"] != binding["version"]:
        raise ValueError("ARTIFACT_EXPERIMENT_VARIANT_VERSION_MISMATCH")
    options = {"shared_workspace_scope": scope} if saved_work._shared_scope_requested(scope) else scope
    actor_id, owner_scope = _authorize_content_project(actor, action="read", **options)
    context = _content_artifact_context(actor, actor_id, owner_scope)
    rows = connection.execute("SELECT * FROM content_generation_evidence WHERE content_type='content_multiplatform' "
                              "AND json_extract(input_json,'$.artifact_id')=?", (aid,)).fetchall()
    if len(rows) != 1:
        raise PermissionError("MULTIPLATFORM_OWNER_RECEIPT_REQUIRED")
    row = dict(rows[0])
    content._verify_content_receipt(row, connection=connection, expected_context=context)
    if (json.loads(row["input_json"]).get("_content_context") != context
            or json.loads(row["output_json"]) != content._content_work_binding(work["artifact"], work["document"])):
        raise PermissionError("MULTIPLATFORM_OWNER_RECEIPT_INVALID")
    package = validate_saved(work["document"])
    source_context = saved_work.authorize_saved_work(actor, scope, action="read", connection=connection)
    for source in package["source_bindings"]:
        current = saved_work._verified_evidence(connection, source["evidence_id"], source_context, actor)
        rights = current["provenance"]["provenance"]
        if (current["content_hash"] != source["content_hash"] or current["version"] != source["version"]
                or current["integrity_digest"] != source["integrity_digest"]
                or rights["rights"] != source["rights"]
                or rights.get("intended_use", "research_reference") not in {"research_reference", "report_quote"}):
            raise PermissionError("MULTIPLATFORM_SOURCE_STALE")
    found = [v for v in package["variants"] if v["id"] == binding["variant_id"]]
    if len(found) != 1 or not found[0]["body"] or found[0]["body_sha256"] != binding["body_sha256"]:
        raise ValueError("ARTIFACT_EXPERIMENT_VARIANT_VERSION_MISMATCH")
    variant = found[0]
    return {**binding, "content_sha256": variant["body_sha256"], "work_id": work["document"]["work_id"],
            "platform": variant["platform"], "locale": variant["locale"], "genre": variant["genre"],
            "source_bindings": package["source_bindings"], "language_quality": "NOT_VERIFIED",
            "meaning": "Exact source-linked Content draft version; not proof of publication, exposure, linguistic quality or human approval."}
