"""LUMENIS Shared Content & Creation skill catalog and local adapters.

The six user-specified tools are registered as one Shared Capability surface.
They are not a third product line and they never own CTH/BMP truth.  The
catalog deliberately separates:

* the requested tool identity (``tool_name``),
* the canonical local implementation that can be verified in this repository,
* the current implementation state, and
* the evidence/permission boundary used by the execution chain.

Adapters are local-first and read/plan oriented.  They do not open external
websites, download platform media, operate social accounts, publish content,
or bypass the existing permission/evidence chain.
"""
from __future__ import annotations

import datetime as _dt
import html
import re
from typing import Any, Dict, Iterable, List, Mapping, Optional


_PROHIBITIONS = [
    "bypass_permission_gate",
    "write_production_data",
    "execute_high_risk_shell",
    "bypass_audit_trail",
    "escalate_privilege",
    "access_credentials_plaintext",
    "access_external_platform_without_user_boundary",
    "publish_or_send_without_human_approval",
]


def _metadata(
    skill_id: str,
    *,
    version: str,
    owner: str,
    permission_level: str,
    input_schema: Dict[str, Any],
    output_schema: Dict[str, Any],
    risk_level: str,
    execution_policy: str,
    evidence_contract: str,
    evaluation_status: str,
    description: str,
    tags: List[str],
    category: str,
    implementation: str,
    implementation_state: str,
    consumers: List[str],
    tool_name: str,
    input_hint: str,
    output_hint: str,
    research_basis: List[str],
    bindings: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Build one catalog record and its SkillRegistry-compatible metadata."""
    metadata = {
        "skill_id": skill_id,
        "version": version,
        "owner": owner,
        "permission_level": permission_level,
        "input_schema": input_schema,
        "output_schema": output_schema,
        "risk_level": risk_level,
        "execution_policy": execution_policy,
        "evidence_contract": evidence_contract,
        "evaluation_status": evaluation_status,
        "description": description,
        "tags": tags,
        "prohibited_actions": list(_PROHIBITIONS),
        "product": "SHARED",
        "domain": "content",
        "cross_domain_allowed": ["CTH", "BMP"],
        "category": category,
    }
    return {
        "metadata": metadata,
        "tool_name": tool_name,
        "name": description.split("：", 1)[0],
        "description": description,
        "implementation": implementation,
        "implementation_state": implementation_state,
        "consumers": consumers,
        "input_hint": input_hint,
        "output_hint": output_hint,
        "research_basis": research_basis,
        "bindings": bindings,
    }


_LOCAL_RESEARCH = [
    "LUMENIS_PRODUCT_ARCHITECTURE_FINAL.md",
    "experience_v2/03_ia_and_flows/IA_AND_FLOWS.md",
    "experience_v2/04_design_system/v2.5/DESIGN_ECOSYSTEM_V2.5.md",
    "00-GOVERNANCE/LUMENIS-CONTENT-CREATION-LEARNING-SOURCE-CONTRACT-V1-20260911.md",
    "intelligence_library/02_ZBMP研究/品牌营销知识/brand-marketing-knowledge-08-meta-framework-seed-to-world-20260903.md",
]


SHARED_SKILL_CATALOG: List[Dict[str, Any]] = [
    _metadata(
        "shared.union_search",
        version="1.0.0",
        owner="Shared Capability / Content Studio",
        permission_level="RESEARCH",
        input_schema={"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["query"]},
        output_schema={"type": "object", "properties": {"resources": {"type": "array"}, "research_assets": {"type": "array"}}},
        risk_level="LOW",
        execution_policy="READ_ONLY",
        evidence_contract="只返回本地 Resource/Intelligence Library 候选及其来源标识；不直接把参考资料升级为生产事实。",
        evaluation_status="PARTIAL",
        description="跨平台选题搜索：在本地研究资料与已入库 Evidence 中做受限检索，不访问站外平台。",
        tags=["research", "evidence", "local-first", "cth", "bmp"],
        category="研究与证据",
        implementation="resource_library.search_resources + content_generation.search_research_library",
        implementation_state="BOUND_LOCAL_READ",
        consumers=["CTH", "BMP"],
        tool_name="union-search-skill",
        input_hint="query（主体/品牌/平台/目标的受限检索词）",
        output_hint="本地 resources、intelligence_assets、source/evidence 元数据",
        research_basis=_LOCAL_RESEARCH + ["用户提供：union-search-skill 规格"],
        bindings=[
            {"module": "resource_library.py", "functions": ["search_resources"]},
            {"module": "content_generation.py", "functions": ["search_research_library"]},
        ],
    ),
    _metadata(
        "shared.video_shotcraft",
        version="1.0.0",
        owner="Shared Capability / Content Studio",
        permission_level="ANALYZE",
        input_schema={"type": "object", "properties": {"brief": {"type": "string"}, "evidence_id": {"type": "string"}, "note_id": {"type": "string"}, "ocr_text": {"type": "string"}, "asr_text": {"type": "string"}}, "required": ["brief"]},
        output_schema={"type": "object", "properties": {"shot_plan": {"type": "array"}, "video_analysis": {"type": "object"}}},
        risk_level="MEDIUM",
        execution_policy="APPROVAL_REQUIRED",
        evidence_contract="只接受已由授权运行时提供的 browser_rendered Evidence；规划/分析结果标为派生草稿，不生成或发布媒体。",
        evaluation_status="PARTIAL",
        description="专业级片头与转场：依据 Brief 生成可审阅镜头草案，并在提供 Evidence 时复用本地视频分析规范。",
        tags=["content", "video", "storyboard", "evidence-first"],
        category="内容制作",
        implementation="video_intelligence.VideoIntelligenceEngine + deterministic shot planner",
        implementation_state="BOUND_LOCAL_DRAFT",
        consumers=["CTH", "BMP"],
        tool_name="video-shotcraft",
        input_hint="brief；可选 browser_rendered Evidence 的 evidence_id/note_id/OCR/ASR",
        output_hint="镜头规划草案、输入 Evidence 的被动分析结果",
        research_basis=_LOCAL_RESEARCH + ["video_intelligence.py", "用户提供：video-shotcraft 规格"],
        bindings=[
            {"module": "video_intelligence.py", "functions": ["VideoIntelligenceEngine.analyze"]},
            {"module": "content_generation.py", "functions": ["api_video_analyze"]},
        ],
    ),
    _metadata(
        "shared.cangjie",
        version="1.0.0",
        owner="Shared Capability / Content Studio",
        permission_level="RESEARCH",
        input_schema={"type": "object", "properties": {"text": {"type": "string"}, "query": {"type": "string"}}, "required": []},
        output_schema={"type": "object", "properties": {"structure": {"type": "object"}, "research_candidates": {"type": "array"}}},
        risk_level="LOW",
        execution_policy="READ_ONLY",
        evidence_contract="结构化提炼只作用于用户/本地资料输入；不覆盖原始资料，不把提炼结果写成 Canonical Data。",
        evaluation_status="PARTIAL",
        description="内容结构化提炼：把本地研究或用户 Brief 组织为可复用结构，不替代原文与事实链。",
        tags=["research", "structure", "learning-asset", "content"],
        category="研究与证据",
        implementation="content_generation.search_research_library + local deterministic structure parser",
        implementation_state="BOUND_LOCAL_PARTIAL",
        consumers=["CTH", "BMP"],
        tool_name="cangjie-skill",
        input_hint="text 或 query；只读取本地研究资料",
        output_hint="标题/段落/主题结构、研究候选及其知识状态",
        research_basis=_LOCAL_RESEARCH + ["用户提供：cangjie-skill 规格"],
        bindings=[
            {"module": "content_generation.py", "functions": ["search_research_library", "search_research_filesystem"]},
            {"module": "intelligence_library_api.py", "functions": ["search_assets"]},
        ],
    ),
    _metadata(
        "shared.huashu",
        version="1.0.0",
        owner="Shared Capability / Content Studio",
        permission_level="SUGGEST",
        input_schema={"type": "object", "properties": {"brief": {"type": "string"}, "platform": {"type": "string"}, "asset_type": {"type": "string"}, "audience": {"type": "string"}, "goal": {"type": "string"}}, "required": ["brief"]},
        output_schema={"type": "object", "properties": {"workflow": {"type": "object"}, "content_types": {"type": "array"}, "modules": {"type": "array"}}},
        risk_level="MEDIUM",
        execution_policy="APPROVAL_REQUIRED",
        evidence_contract="只生成有明确 Context/Brief/Evidence/Approval 边界的创作工作流草案；真正内容生成复用既有 Content API。",
        evaluation_status="PARTIAL",
        description="全流程创作工具集：把 Brief 映射到选题、文案、视频、封面、评估和学习资产的共享工作流。",
        tags=["content", "workflow", "copy", "video", "evaluation"],
        category="内容制作",
        implementation="content_generation.CONTENT_TYPES + content_generation.get_module_status",
        implementation_state="BOUND_LOCAL_WORKFLOW",
        consumers=["CTH", "BMP"],
        tool_name="huashu-skills",
        input_hint="Brief + 平台/形式/受众/目标；不自动发布",
        output_hint="可用内容类型、已登记模块、下一步审批边界",
        research_basis=_LOCAL_RESEARCH + ["content_generation.py", "用户提供：huashu-skills 规格"],
        bindings=[
            {"module": "content_generation.py", "functions": ["get_module_status", "generate_content"]},
            {"module": "content_generation.py", "functions": ["evaluate_content"]},
        ],
    ),
    _metadata(
        "shared.social_card",
        version="1.0.0",
        owner="Shared Capability / Content Studio",
        permission_level="SUGGEST",
        input_schema={"type": "object", "properties": {"title": {"type": "string"}, "subtitle": {"type": "string"}, "accent": {"type": "string"}, "width": {"type": "integer"}, "height": {"type": "integer"}}, "required": ["title"]},
        output_schema={"type": "object", "properties": {"artifact_type": {"type": "string"}, "svg": {"type": "string"}, "approval_required": {"type": "boolean"}}},
        risk_level="MEDIUM",
        execution_policy="APPROVAL_REQUIRED",
        evidence_contract="输出本地 SVG 草稿并记录为派生 Artifact；不宣称 PNG/平台发布已完成，不包含未经 Evidence 支撑的事实。",
        evaluation_status="PARTIAL",
        description="多平台封面生成：按 Brief 生成可审阅的本地 SVG 社交卡草稿，保留平台尺寸与人工审批边界。",
        tags=["content", "visual", "social", "draft", "approval"],
        category="内容制作",
        implementation="local deterministic SVG draft renderer (no external asset fetch)",
        implementation_state="BOUND_LOCAL_DRAFT",
        consumers=["CTH", "BMP"],
        tool_name="quizang-social-card-skill",
        input_hint="title；可选 subtitle/accent/width/height",
        output_hint="SVG 草稿 Artifact + approval_required=true",
        research_basis=_LOCAL_RESEARCH + ["用户提供：quizang-social-card-skill 规格"],
        bindings=[
            {"module": "lumenis_shared_skills.py", "functions": ["_render_social_card"]},
            {"module": "experience_v2/04_design_system/v2.5/DESIGN_ECOSYSTEM_V2.5.md", "functions": ["material / point / trace language"]},
        ],
    ),
    _metadata(
        "shared.last30days",
        version="1.0.0",
        owner="Shared Capability / Content Studio",
        permission_level="RESEARCH",
        input_schema={"type": "object", "properties": {"days": {"type": "integer"}, "query": {"type": "string"}}, "required": []},
        output_schema={"type": "object", "properties": {"period": {"type": "object"}, "stats": {"type": "object"}, "notes": {"type": "array"}}},
        risk_level="LOW",
        execution_policy="READ_ONLY",
        evidence_contract="只读 Canonical notes 近 N 日数据与既有统计函数；无新采集、无外部平台访问、无指标重算。",
        evaluation_status="PARTIAL",
        description="话题简报扫描：从当前本地 Canonical 数据读取近 30 日话题/内容变化，按真实时间范围输出简报素材。",
        tags=["cth", "bmp", "trend", "evidence", "local-data"],
        category="研究与证据",
        implementation="database.get_notes_by_date_range + database.get_stats_by_date_range",
        implementation_state="BOUND_LOCAL_READ",
        consumers=["CTH", "BMP"],
        tool_name="last30days-skill",
        input_hint="可选 days/query；默认近 30 日",
        output_hint="真实时间窗、Canonical 统计、按互动排序的内容摘要",
        research_basis=_LOCAL_RESEARCH + ["database.py", "用户提供：last30days-skill 规格"],
        bindings=[
            {"module": "database.py", "functions": ["get_notes_by_date_range", "get_stats_by_date_range"]},
            {"module": "experience_v2/03_ia_and_flows/IA_AND_FLOWS.md", "functions": ["Observe -> Understand -> Evidence"]},
        ],
    ),
]

_BY_ID = {item["metadata"]["skill_id"]: item for item in SHARED_SKILL_CATALOG}
_SENSITIVE_KEYS = {"password", "token", "api_key", "secret", "cookie", "session", "credential", "private_key"}


def _binding_state(spec: Mapping[str, Any]) -> Dict[str, Any]:
    """Probe only module/function presence; never expose filesystem paths."""
    import importlib

    results = []
    available = True
    for binding in spec.get("bindings", []):
        missing: List[str] = []
        exc_name = ""
        module_name = str(binding.get("module", ""))
        if module_name.endswith(".py"):
            module_name = module_name[:-3].replace("/", ".")
        if "/" in module_name:
            module_name = module_name.replace("/", ".")
        if module_name.startswith("experience_v2."):
            # Documentation binding: presence is checked by the catalog's own source.
            results.append({"module": str(binding.get("module")), "available": True, "functions": binding.get("functions", [])})
            continue
        try:
            module = importlib.import_module(module_name)
            missing = [fn for fn in binding.get("functions", []) if not _has_dotted_attr(module, fn)]
            ok = not missing
        except Exception as exc:  # pragma: no cover - environment-dependent optional module
            ok = False
            missing = list(binding.get("functions", []))
            exc_name = type(exc).__name__
        row = {"module": str(binding.get("module")), "available": ok, "functions": binding.get("functions", [])}
        if missing:
            row["missing"] = missing
        if not ok and exc_name:
            row["error_type"] = exc_name
        results.append(row)
        available = available and ok
    state = str(spec.get("implementation_state", "UNKNOWN"))
    return {"available": available, "state": state, "bindings": results}


def _has_dotted_attr(obj: Any, dotted: str) -> bool:
    current = obj
    for part in str(dotted).split("."):
        if not hasattr(current, part):
            return False
        current = getattr(current, part)
    return True


def list_shared_skills() -> List[Dict[str, Any]]:
    """Return a safe, UI/API-ready catalog snapshot."""
    result = []
    for spec in SHARED_SKILL_CATALOG:
        meta = spec["metadata"]
        binding = _binding_state(spec)
        result.append({
            "skill_id": meta["skill_id"],
            "tool_name": spec["tool_name"],
            "name": spec["name"],
            "description": spec["description"],
            "owner": meta["owner"],
            "product": "SHARED",
            "domain": "content",
            "consumers": list(spec["consumers"]),
            "category": meta["category"],
            "version": meta["version"],
            "permission_level": meta["permission_level"],
            "risk_level": meta["risk_level"],
            "execution_policy": meta["execution_policy"],
            "evaluation_status": meta["evaluation_status"],
            "implementation": spec["implementation"],
            "implementation_state": spec["implementation_state"],
            "binding": binding,
            "input_hint": spec["input_hint"],
            "output_hint": spec["output_hint"],
            "research_basis": list(spec["research_basis"]),
        })
    return result


def get_shared_skill(skill_id: str) -> Optional[Dict[str, Any]]:
    return _BY_ID.get(str(skill_id or ""))


def skill_metadata(skill_id: str) -> Optional[Dict[str, Any]]:
    spec = get_shared_skill(skill_id)
    return dict(spec["metadata"]) if spec else None


def validate_input(payload: Mapping[str, Any]) -> Optional[Dict[str, str]]:
    """Reject credential-shaped input before it reaches the execution trace."""
    for key in payload.keys():
        if str(key).lower() in _SENSITIVE_KEYS:
            return {"code": "SENSITIVE_INPUT", "reason": f"input field '{key}' is not accepted by Shared Skill"}
    return None


def run_shared_skill(skill_id: str, task: str = "", input_payload: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """Run one local, bounded adapter.  The caller supplies the permission chain."""
    spec = get_shared_skill(skill_id)
    if not spec:
        raise ValueError(f"shared skill '{skill_id}' is not registered")
    payload = dict(input_payload or {})
    invalid = validate_input(payload)
    if invalid:
        return {"status": "rejected", **invalid, "implementation_state": spec["implementation_state"]}
    task = str(task or "").strip()[:4000]
    if skill_id == "shared.union_search":
        return _run_union_search(task, payload)
    if skill_id == "shared.video_shotcraft":
        return _run_video_shotcraft(task, payload)
    if skill_id == "shared.cangjie":
        return _run_cangjie(task, payload)
    if skill_id == "shared.huashu":
        return _run_huashu(task, payload)
    if skill_id == "shared.social_card":
        return _run_social_card(task, payload)
    if skill_id == "shared.last30days":
        return _run_last30days(task, payload)
    raise ValueError(f"no local adapter for shared skill '{skill_id}'")


def _run_union_search(task: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    query = str(payload.get("query") or task).strip()[:240]
    if not query:
        return {"status": "input_required", "code": "QUERY_REQUIRED", "implementation_state": "BOUND_LOCAL_READ"}
    limit = _bounded_int(payload.get("limit", 5), 1, 20)
    resources: List[Dict[str, Any]] = []
    research: List[Dict[str, Any]] = []
    errors: List[str] = []
    try:
        from resource_library import search_resources
        pc = str(payload.get("domain") or payload.get("product") or "")
        if pc.upper() == "BMP":
            pc = "ZBMP"
        result = search_resources(query=query, product_context=pc, reference_only=True, limit=limit) if pc else search_resources(query=query, reference_only=True, limit=limit)
        resources = list(result.get("resources", []))
    except Exception as exc:
        errors.append(f"resource_library:{type(exc).__name__}")
    try:
        from content_generation import search_research_library
        research = search_research_library(query, limit=limit)
    except Exception as exc:
        errors.append(f"intelligence_assets:{type(exc).__name__}")
    return {
        "status": "completed" if not errors else "partial",
        "query": query,
        "resources": resources,
        "research_assets": research,
        "external_fetch": False,
        "errors": errors,
        "implementation_state": "BOUND_LOCAL_READ",
    }


def _run_video_shotcraft(task: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    brief = str(payload.get("brief") or task).strip()[:2000]
    if not brief:
        return {"status": "input_required", "code": "BRIEF_REQUIRED", "implementation_state": "BOUND_LOCAL_DRAFT"}
    shot_plan = _shot_plan(brief)
    result: Dict[str, Any] = {
        "status": "completed",
        "brief": brief,
        "shot_plan": shot_plan,
        "implementation_state": "BOUND_LOCAL_DRAFT",
        "external_media_fetch": False,
        "approval_required": True,
        "unimplemented": ["自动生成成片", "平台发布"],
    }
    evidence_id = str(payload.get("evidence_id") or "").strip()
    note_id = str(payload.get("note_id") or "").strip()
    if evidence_id or note_id:
        if not evidence_id or not note_id or payload.get("source", "browser_rendered") != "browser_rendered":
            return {"status": "rejected", "code": "BROWSER_RENDERED_EVIDENCE_REQUIRED", "implementation_state": "BOUND_LOCAL_DRAFT"}
        try:
            from video_intelligence import VideoEvidence, VideoIntelligenceEngine
            evidence = VideoEvidence(
                evidence_id=evidence_id,
                note_id=note_id,
                ocr_text=str(payload.get("ocr_text") or "")[:4000],
                asr_text=str(payload.get("asr_text") or "")[:4000],
                source="browser_rendered",
            )
            analysis = VideoIntelligenceEngine(provider=None, provider_name="none", model_version="none").analyze(evidence)
            result["video_analysis"] = analysis.as_dict()
            result["evidence_id"] = evidence_id
        except Exception as exc:
            result["status"] = "partial"
            result["analysis_error_type"] = type(exc).__name__
    return result


def _run_cangjie(task: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    text = str(payload.get("text") or "").strip()[:12000]
    query = str(payload.get("query") or task).strip()[:240]
    structure = _structure_text(text) if text else {"status": "input_required", "sections": []}
    candidates: List[Dict[str, Any]] = []
    if query:
        try:
            from content_generation import search_research_library
            candidates = search_research_library(query, limit=5)
        except Exception:
            candidates = []
    return {
        "status": "completed" if text or candidates else "input_required",
        "structure": structure,
        "research_candidates": candidates,
        "source_scope": "local research library + supplied text",
        "implementation_state": "BOUND_LOCAL_PARTIAL",
        "unimplemented": ["把结构结果自动发布为永久 Skill 版本"],
    }


def _run_huashu(task: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    brief = str(payload.get("brief") or task).strip()[:2000]
    if not brief:
        return {"status": "input_required", "code": "BRIEF_REQUIRED", "implementation_state": "BOUND_LOCAL_WORKFLOW"}
    try:
        from content_generation import CONTENT_TYPES, get_module_status
        types = [{"id": key, "label": value.get("label"), "level": value.get("level")} for key, value in CONTENT_TYPES.items()]
        modules = get_module_status()
    except Exception as exc:
        return {"status": "partial", "brief": brief, "error_type": type(exc).__name__, "implementation_state": "BOUND_LOCAL_WORKFLOW"}
    return {
        "status": "completed",
        "brief": brief,
        "workflow": {
            "context": {k: payload.get(k) for k in ("domain", "product", "platform", "asset_type", "audience", "goal") if payload.get(k)},
            "stages": ["Brief", "Context", "Evidence", "Strategy", "Create", "Review", "Approval", "Export/Publish", "Evaluation", "Learning"],
            "next_api": "/api/content/generate",
            "publish": "human_approval_required",
        },
        "content_types": types,
        "modules": [{"id": m.get("id"), "name": m.get("name"), "status": m.get("status"), "api": m.get("api")} for m in modules],
        "implementation_state": "BOUND_LOCAL_WORKFLOW",
        "provider_call": False,
    }


def _run_social_card(task: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    title = str(payload.get("title") or task).strip()[:160]
    if not title:
        return {"status": "input_required", "code": "TITLE_REQUIRED", "implementation_state": "BOUND_LOCAL_DRAFT"}
    width = _bounded_int(payload.get("width", 1080), 320, 2048)
    height = _bounded_int(payload.get("height", 1440), 320, 2048)
    subtitle = str(payload.get("subtitle") or "").strip()[:240]
    accent = str(payload.get("accent") or "#9fe7f5")
    if not re.match(r"^#[0-9a-fA-F]{6}$", accent):
        accent = "#9fe7f5"
    return {
        "status": "completed",
        "artifact_type": "svg_draft",
        "svg": _render_social_card(title, subtitle, accent, width, height),
        "dimensions": {"width": width, "height": height},
        "approval_required": True,
        "publishing": "not_performed",
        "implementation_state": "BOUND_LOCAL_DRAFT",
    }


def _run_last30days(task: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    days = _bounded_int(payload.get("days", 30), 1, 90)
    end = _dt.date.today()
    start = end - _dt.timedelta(days=days - 1)
    start_s, end_s = start.isoformat(), end.isoformat()
    query = str(payload.get("query") or task).strip()[:160]
    try:
        import database
        stats = database.get_stats_by_date_range(start_s, end_s)
        notes = database.get_notes_by_date_range(start_s, end_s)
        if query:
            needle = query.lower()
            notes = [n for n in notes if needle in str(n.get("title", "")).lower() or needle in str(n.get("content", "")).lower()]
        notes = sorted(notes, key=lambda n: sum(int(n.get(k) or 0) for k in ("likes", "comments", "collects", "shares")), reverse=True)[:20]
        view = [{"note_id": n.get("note_id"), "title": (n.get("title") or "")[:120], "publish_date": n.get("publish_date"), "platform": n.get("platform") or n.get("source_platform"), "engagement": sum(int(n.get(k) or 0) for k in ("likes", "comments", "collects", "shares")), "risk_level": n.get("risk_level"), "evidence_id": n.get("note_id")} for n in notes]
        return {"status": "completed", "period": {"start": start_s, "end": end_s, "days": days}, "stats": stats, "notes": view, "query": query, "implementation_state": "BOUND_LOCAL_READ", "external_fetch": False}
    except Exception as exc:
        return {"status": "offline", "period": {"start": start_s, "end": end_s, "days": days}, "error_type": type(exc).__name__, "implementation_state": "BOUND_LOCAL_READ"}


def _shot_plan(brief: str) -> List[Dict[str, Any]]:
    parts = [p.strip() for p in re.split(r"[。！？!?；;\n]+", brief) if p.strip()]
    if not parts:
        parts = [brief]
    roles = ["hook", "context", "proof", "action"]
    return [{"shot_no": idx + 1, "role": roles[min(idx, len(roles) - 1)], "duration_sec": 3 if idx == 0 else 4, "brief": part[:180], "transition": "cut" if idx == 0 else "match-cut"} for idx, part in enumerate(parts[:8])]


def _structure_text(text: str) -> Dict[str, Any]:
    headings = list(re.finditer(r"(?m)^#{1,6}\s+(.+?)\s*$", text))
    sections = []
    if headings:
        for idx, match in enumerate(headings):
            end = headings[idx + 1].start() if idx + 1 < len(headings) else len(text)
            body = text[match.end():end].strip()
            sections.append({"title": match.group(1).strip()[:160], "level": len(match.group(0)) - len(match.group(0).lstrip("#")), "summary": body[:420], "paragraph_count": len([p for p in re.split(r"\n\s*\n", body) if p.strip()])})
    else:
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        sections = [{"title": f"Section {idx + 1}", "level": 1, "summary": paragraph[:420], "paragraph_count": 1} for idx, paragraph in enumerate(paragraphs[:12])]
    return {"title_count": len(headings), "section_count": len(sections), "characters": len(text), "sections": sections}


def _render_social_card(title: str, subtitle: str, accent: str, width: int, height: int) -> str:
    safe_title = html.escape(title, quote=True)
    safe_subtitle = html.escape(subtitle, quote=True)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{safe_title}">'
        f'<rect width="{width}" height="{height}" fill="#151719"/><path d="M72 {height - 132}H{width - 72}" stroke="#596167" stroke-width="2"/>'
        f'<circle cx="{width - 104}" cy="104" r="28" fill="none" stroke="{accent}" stroke-width="4"/>'
        f'<text x="72" y="{int(height * 0.46)}" fill="#f5f7f8" font-family="Arial, sans-serif" font-size="{max(34, int(width * 0.07))}" font-weight="700">{safe_title}</text>'
        f'<text x="72" y="{int(height * 0.54)}" fill="#b8c0c5" font-family="Arial, sans-serif" font-size="{max(20, int(width * 0.032))}">{safe_subtitle}</text>'
        f'<text x="72" y="{height - 72}" fill="{accent}" font-family="monospace" font-size="18" letter-spacing="3">LUMENIS · DRAFT</text></svg>'
    )


def _bounded_int(value: Any, default: int, maximum: int) -> int:
    try:
        return max(1, min(int(value), maximum))
    except (TypeError, ValueError):
        return default
