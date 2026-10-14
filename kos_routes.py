# -*- coding: utf-8 -*-





"""LUMENIS BMP KOS API compatibility blueprint











复用 kos_engine.py 与 Shared Reporting KOS owner，不重复建设。





API 统一前缀 /api/kos/。





"""





from flask import Blueprint, jsonify, request

# KOS采集专用香港账号（rednote_hk）
try:
    from dual_account_rotation import select_account_for_collection
    KOS_DUAL_ACCOUNT = True
except ImportError:
    KOS_DUAL_ACCOUNT = False

import os
import sys
from pathlib import Path

kos_bp = Blueprint("kos", __name__, url_prefix="/api/kos")











# 延迟导入，避免循环依赖





def _engine():





    if "kos_engine" not in sys.modules:





        import kos_engine





    return sys.modules["kos_engine"]











def _resolve_kos_brand_scope(action):
    """Resolve one registered BMP BrandFocus and its current Permission receipt."""
    from lumenis.auth.service import get_current_user
    from lumenis.system.security.permission import (
        check_actor_scope_permission,
        check_local_workspace_scope_permission,
        resolve_local_workspace_principal,
    )
    from subject_registry import get_subject_by_id, list_subjects, normalize_domain

    try:
        domain_name = normalize_domain(request.headers.get("X-Domain-Id", ""))
    except (TypeError, ValueError) as exc:
        raise ValueError("DOMAIN_REQUIRED") from exc
    if domain_name != "BMP":
        raise ValueError("BMP_DOMAIN_REQUIRED")
    product = request.headers.get("X-Product-Id")
    if product is not None and product.strip().upper() not in {"BMP", "ZBMP"}:
        raise ValueError("CONTEXT_SCOPE_MISMATCH")
    if request.headers.get("X-Lumenis-Context-Mode", "GLOBAL_ALL") != "FOCUS":
        raise ValueError("BRAND_FOCUS_REQUIRED")

    subject_id = request.headers.get("X-Subject-ID")
    brand_focus_id = request.headers.get("X-Brand-Focus-ID")
    if any(value is not None and (not value.strip() or value != value.strip())
           for value in (subject_id, brand_focus_id)):
        raise ValueError("CONTEXT_SCOPE_MISMATCH")
    if subject_id:
        selected = get_subject_by_id(domain_name, subject_id)
        if (not isinstance(selected, dict) or selected.get("subject_type") != "brand"
                or not selected.get("brand_focus_id")
                or (brand_focus_id and selected.get("brand_focus_id") != brand_focus_id)):
            raise ValueError("BRAND_FOCUS_NOT_REGISTERED")
    elif brand_focus_id:
        matches = [entry for entry in list_subjects(domain_name)
                   if entry.get("brand_focus_id") == brand_focus_id
                   and entry.get("status") in {"active", "configured"}]
        if len(matches) != 1 or matches[0].get("subject_type") != "brand":
            raise ValueError("BRAND_FOCUS_NOT_UNIQUELY_REGISTERED")
        selected = matches[0]
    else:
        raise ValueError("BRAND_FOCUS_REQUIRED")
    if selected.get("status") not in {"active", "configured"}:
        raise ValueError("BRAND_FOCUS_NOT_ACTIVE")

    scope = {"domain_id": "zbmp", "subject_id": None,
             "brand_focus_id": selected["brand_focus_id"], "global_scope": False}
    principal = resolve_local_workspace_principal(module="reports", action=action)
    actor = principal if principal is not None else get_current_user(read_only=action == "read")
    if principal is None and (not isinstance(actor, dict)
                              or type(actor.get("id")) is not int or actor["id"] <= 0):
        raise PermissionError("AUTH_REQUIRED")
    checker = check_local_workspace_scope_permission if principal is not None else check_actor_scope_permission
    decision = checker(actor, module="reports", action=action, **scope)
    if (decision.allowed is not True or decision.verification_state != "verified"
            or not decision.scope_audit_id):
        raise PermissionError("SCOPE_PERMISSION_DENIED")
    actor_id = decision.actor_id or (actor.get("id") if isinstance(actor, dict) else getattr(actor, "id", None))
    if type(actor_id) is not int or actor_id <= 0:
        raise PermissionError("ACTOR_ID_UNAVAILABLE")
    return actor, str(actor_id), scope, selected, decision


def _kos_scope_error(exc):
    code = str(exc) or type(exc).__name__
    status = 403 if isinstance(exc, PermissionError) else (
        503 if "UNAVAILABLE" in code else 400
    )
    return jsonify({"ok": False, "status": "denied" if status == 403 else "blocked" if status == 503 else "invalid_request",
                    "code": code}), status


def _kos_scoped_author_profile(author_id, scope):
    import database as db
    import reprocess

    if not isinstance(author_id, str) or not author_id.strip():
        return None
    author_id = author_id.strip()
    ids = reprocess._canonical_source_ids(scope, limit=5000)
    if not ids:
        return None
    rows = db.get_notes_for_canonical_source_ids(
        ids, filters={"author_id": author_id}, limit=min(len(ids), 1000))
    matched = []
    for row in rows:
        note = reprocess._scoped_note(row, scope)
        if note.get("author_id") == author_id:
            matched.append(note)
    if not matched:
        return None
    return {
        "author_id": author_id,
        "author_nickname": matched[0].get("author_nickname"),
        "kos_tier": None,
        "notes": matched,
    }


def _kos_selected_brand_name(selected):
    value = selected.get("name_zh") or selected.get("name_en")
    if not isinstance(value, str) or not value.strip():
        raise ValueError("BRAND_DISPLAY_NAME_UNAVAILABLE")
    return value.strip()


@kos_bp.route("/overview", methods=["GET"])





def api_overview():





    """KOS 总览统计。"""





    try:





        ke = _engine()





        return jsonify({"ok": True, "data": ke.get_stats()})





    except Exception as e:





        return jsonify({"ok": False, "error": str(e)}), 500

















@kos_bp.route("/list", methods=["GET"])





def api_list():





    """KOS 列表（支持 tier/lifecycle/potential/risk/search/limit/offset/sort_by）。"""





    try:





        ke = _engine()





        tier = request.args.get("tier", "")





        lifecycle = request.args.get("lifecycle", "")





        potential = request.args.get("potential", "0") == "1"





        risk = request.args.get("risk", "0") == "1"





        search = request.args.get("search", "")





        limit = min(int(request.args.get("limit", 50)), 200)





        offset = int(request.args.get("offset", 0))





        sort_by = request.args.get("sort_by", "kos_score")





        result = ke.list_profiles(tier=tier, lifecycle=lifecycle, potential_only=potential,





                                   risk_only=risk, search=search, limit=limit, offset=offset, sort_by=sort_by)





        return jsonify({"ok": True, **result})





    except Exception as e:





        return jsonify({"ok": False, "error": str(e)}), 500

















@kos_bp.route("/detail", methods=["GET"])





def api_detail():





    """KOS 详情（含笔记列表）。"""





    try:





        ke = _engine()





        author_id = request.args.get("author_id", "")





        if not author_id:





            return jsonify({"ok": False, "error": "author_id required"}), 400





        profile = ke.get_profile(author_id)





        if not profile:





            return jsonify({"ok": False, "error": "KOS not found"}), 404





        return jsonify({"ok": True, "data": profile})





    except Exception as e:





        return jsonify({"ok": False, "error": str(e)}), 500

















@kos_bp.route("/refresh", methods=["POST"])





def api_refresh():





    """从 notes 重新聚合刷新 KOS 数据。"""





    try:





        ke = _engine()





        stats = ke.refresh_profiles()





        return jsonify({"ok": True, "data": stats})





    except Exception as e:





        return jsonify({"ok": False, "error": str(e)}), 500

















@kos_bp.route("/comments", methods=["GET"])





def api_comments():





    """评论分析（支持 author_id/note_id）。"""





    try:





        ke = _engine()





        author_id = request.args.get("author_id", "")





        note_id = request.args.get("note_id", "")





        limit = min(int(request.args.get("limit", 50)), 200)





        result = ke.analyze_comments(author_id=author_id, note_id=note_id, limit=limit)





        return jsonify({"ok": True, **result})





    except Exception as e:





        return jsonify({"ok": False, "error": str(e)}), 500

















@kos_bp.route("/outreach", methods=["POST"])
def api_outreach():
    """Create a scoped, deterministic outreach draft for human review."""
    try:
        _actor, actor_id, scope, selected, decision = _resolve_kos_brand_scope("write")
        data = request.get_json(silent=True) or {}
        author_id = data.get("author_id")
        campaign_name = data.get("campaign_name", "")
        if not isinstance(author_id, str) or not author_id.strip():
            return jsonify({"ok": False, "status": "invalid_request", "code": "AUTHOR_ID_REQUIRED"}), 400
        if not isinstance(campaign_name, str) or len(campaign_name) > 200:
            return jsonify({"ok": False, "status": "invalid_request", "code": "CAMPAIGN_NAME_INVALID"}), 400
        profile = _kos_scoped_author_profile(author_id, scope)
        if profile is None:
            return jsonify({"ok": False, "status": "not_found", "code": "AUTHOR_NOT_IN_BRAND_SCOPE"}), 404
        brand_name = _kos_selected_brand_name(selected)
        result = _engine().generate_outreach(
            author_id, brand_name=brand_name, campaign_name=campaign_name,
            profile=profile, ai_enhance=False,
        )
        if result.get("ok") is not True:
            return jsonify(result), 409
        try:
            import kos_execution as execution
            receipt = execution.create_execution(
                action_type="outreach_send", target_author_id=author_id,
                target_brand=brand_name,
                payload={"campaign_name": campaign_name,
                         "generated_draft": result.get("content", ""),
                         "content_source": "deterministic_rule",
                         "brand_focus_id": scope["brand_focus_id"],
                         "scope_audit_id": decision.scope_audit_id},
                actor=f"actor:{actor_id}",
            )
        except Exception as exc:  # noqa: BLE001 - convert unknown persistence failures to an explicit partial result.
            return jsonify({"ok": False, "status": "partial", "code": "DRAFT_REVIEW_RECORD_FAILED",
                            "draft": result, "error_type": type(exc).__name__}), 503
        result["hcg"] = {"status": receipt.get("status"),
                         "execution_id": receipt.get("execution_id"),
                         "note": "规则生成草稿已登记；未发送，需人工审核。"}
        result["scope"] = {"domain_id": scope["domain_id"],
                           "brand_focus_id": scope["brand_focus_id"],
                           "scope_audit_id": decision.scope_audit_id}
        return jsonify(result)
    except (ValueError, PermissionError) as exc:
        return _kos_scope_error(exc)
    except Exception as exc:  # noqa: BLE001 - request boundary returns a sanitized failure, never success.
        return jsonify({"ok": False, "status": "error", "code": "OUTREACH_FAILED",
                        "error_type": type(exc).__name__}), 503



@kos_bp.route("/ad-candidates", methods=["GET"])





def api_ad_candidates():





    """投流候选评分。"""





    try:





        ke = _engine()





        note_id = request.args.get("note_id", "")





        author_id = request.args.get("author_id", "")





        result = ke.ad_candidate_score(note_id=note_id, author_id=author_id)





        return jsonify({"ok": True, **result})





    except Exception as e:





        return jsonify({"ok": False, "error": str(e)}), 500

















@kos_bp.route("/reward", methods=["GET"])





def api_reward():





    """奖励积分计算。"""





    try:





        ke = _engine()





        author_id = request.args.get("author_id", "")





        period = request.args.get("period", "month")





        if not author_id:





            return jsonify({"ok": False, "error": "author_id required"}), 400





        result = ke.reward_calculate(author_id, period=period)





        return jsonify(result)





    except Exception as e:





        return jsonify({"ok": False, "error": str(e)}), 500

















@kos_bp.route("/report/generate", methods=["POST"])
def api_report_generate():
    """Fail honestly until the existing KOS report reader supports exact BrandFocus."""
    try:
        _actor, _actor_id, scope, selected, decision = _resolve_kos_brand_scope("write")
        return jsonify({
            "ok": False,
            "status": "blocked",
            "code": "KOS_REPORT_SCOPE_UNAVAILABLE",
            "brand_focus_id": scope["brand_focus_id"],
            "brand_name": _kos_selected_brand_name(selected),
            "scope_audit_id": decision.scope_audit_id,
            "reason": "现有 KOS 报告读取器仍聚合未按 BrandFocus 隔离的数据；本次不生成跨品牌报告。",
        }), 409
    except (ValueError, PermissionError) as exc:
        return _kos_scope_error(exc)
    except Exception as exc:  # noqa: BLE001 - request boundary returns a sanitized failure, never success.
        return jsonify({"ok": False, "status": "error", "code": "KOS_REPORT_SCOPE_RESOLUTION_FAILED",
                        "error_type": type(exc).__name__}), 503



@kos_bp.route("/report/view", methods=["GET"])
def api_report_view():
    """Fail closed for historical reports without a persisted BrandFocus binding."""
    try:
        _actor, _actor_id, scope, selected, decision = _resolve_kos_brand_scope("read")
        return jsonify({
            "ok": False,
            "status": "blocked",
            "code": "KOS_REPORT_SCOPE_UNAVAILABLE",
            "brand_focus_id": scope["brand_focus_id"],
            "brand_name": _kos_selected_brand_name(selected),
            "scope_audit_id": decision.scope_audit_id,
            "reason": "现有报告文件没有可核验的 BrandFocus 绑定，暂不提供跨范围报告。",
        }), 409
    except (ValueError, PermissionError) as exc:
        return _kos_scope_error(exc)
    except Exception as exc:  # noqa: BLE001 - hide unexpected scope resolver details and return a sanitized failure.
        return jsonify({"ok": False, "status": "error", "code": "KOS_REPORT_SCOPE_RESOLUTION_FAILED",
                        "error_type": type(exc).__name__}), 503



@kos_bp.route("/reply/generate", methods=["POST"])
def api_reply_generate():
    """Create a scoped reply suggestion; never sends it or changes brand identity."""
    try:
        _actor, actor_id, scope, selected, decision = _resolve_kos_brand_scope("write")
        data = request.get_json(silent=True) or {}
        comment_text = data.get("comment_text")
        if not isinstance(comment_text, str) or not comment_text.strip() or len(comment_text) > 8000:
            return jsonify({"ok": False, "status": "invalid_request", "code": "COMMENT_TEXT_REQUIRED"}), 400
        author_id = data.get("author_id", "")
        if author_id and (not isinstance(author_id, str)
                          or _kos_scoped_author_profile(author_id, scope) is None):
            return jsonify({"ok": False, "status": "denied", "code": "AUTHOR_NOT_IN_BRAND_SCOPE"}), 403
        risk_level = data.get("risk_level", "low")
        if risk_level not in {"low", "medium", "high", "critical"}:
            risk_level = "unknown"
        reply_style = data.get("reply_style", "professional")
        if not isinstance(reply_style, str) or len(reply_style) > 40:
            return jsonify({"ok": False, "status": "invalid_request", "code": "REPLY_STYLE_INVALID"}), 400
        brand_name = _kos_selected_brand_name(selected)
        result = _engine().generate_reply(
            comment_text=comment_text.strip(), brand_name=brand_name,
            reply_style=reply_style, risk_level=risk_level, ai_enhance=False,
        )
        result["content_source"] = "deterministic_rule"
        result["input_provenance"] = "USER_PROVIDED_UNVERIFIED"
        result["scope"] = {"domain_id": scope["domain_id"],
                           "brand_focus_id": scope["brand_focus_id"],
                           "scope_audit_id": decision.scope_audit_id}
        if result.get("ok") is True and result.get("action") != "NO_REPLY":
            try:
                import kos_execution as execution
                receipt = execution.create_execution(
                    action_type="reply_send", target_author_id=author_id,
                    target_brand=brand_name,
                    payload={"comment_text": comment_text.strip(),
                             "comment_source": "USER_PROVIDED_UNVERIFIED",
                             "reply_style": reply_style,
                             "generated_reply": result.get("reply") or result.get("draft") or "",
                             "content_source": "deterministic_rule",
                             "brand_focus_id": scope["brand_focus_id"],
                             "scope_audit_id": decision.scope_audit_id},
                    actor=f"actor:{actor_id}",
                )
            except Exception as exc:  # noqa: BLE001 - preserve the suggestion but report failed review registration.
                return jsonify({"ok": False, "status": "partial", "code": "REPLY_REVIEW_RECORD_FAILED",
                                "suggestion": result, "error_type": type(exc).__name__}), 503
            result["hcg"] = {"status": receipt.get("status"),
                             "execution_id": receipt.get("execution_id"),
                             "note": "规则生成建议已登记；未发送，需人工审核。"}
        return jsonify(result)
    except (ValueError, PermissionError) as exc:
        return _kos_scope_error(exc)
    except Exception as exc:  # noqa: BLE001 - request boundary returns a sanitized failure, never success.
        return jsonify({"ok": False, "status": "error", "code": "REPLY_GENERATION_FAILED",
                        "error_type": type(exc).__name__}), 503



@kos_bp.route("/content-dna", methods=["GET"])





def api_content_dna():





    """提取KOS内容基因。"""





    try:





        ke = _engine()





        author_id = request.args.get("author_id", "")





        limit = min(int(request.args.get("limit", 20)), 50)





        if not author_id:





            return jsonify({"ok": False, "error": "author_id required"}), 400





        result = ke.extract_content_dna(author_id, limit=limit)





        return jsonify(result)





    except Exception as e:





        return jsonify({"ok": False, "error": str(e)}), 500

















@kos_bp.route("/attribution", methods=["GET"])
def api_attribution():
    """Return attribution from notes verified within the selected BrandFocus."""
    try:
        _actor, _actor_id, scope, selected, decision = _resolve_kos_brand_scope("read")
        author_id = request.args.get("author_id", "")
        note_ids = request.args.get("note_ids", "")
        brand_name = _kos_selected_brand_name(selected)
        if author_id:
            import kos_attribution
            outcome = kos_attribution.calculate_attribution(
                author_id, brand_name=brand_name, scope=scope,
            )
        elif note_ids:
            normalized = [part.strip() for part in note_ids.split(",") if part.strip()]
            import kos_attribution
            outcome = kos_attribution.calculate_multi_touch_attribution(
                normalized, brand_name=brand_name, scope=scope,
            )
        else:
            return jsonify({"ok": False, "status": "invalid_request",
                            "code": "AUTHOR_ID_OR_NOTE_IDS_REQUIRED"}), 400
        if outcome.get("ok") is not True:
            status = 403 if outcome.get("status") == "denied" else 409
            return jsonify({**outcome, "scope_audit_id": decision.scope_audit_id}), status
        return jsonify({**outcome, "scope_audit_id": decision.scope_audit_id})
    except (ValueError, PermissionError) as exc:
        return _kos_scope_error(exc)
    except Exception as exc:  # noqa: BLE001 - request boundary returns a sanitized failure, never success.
        return jsonify({"ok": False, "status": "error", "code": "ATTRIBUTION_FAILED",
                        "error_type": type(exc).__name__}), 503



@kos_bp.route("/intent-analysis", methods=["GET"])





def api_intent_analysis():





    """意向评论分层分析。参数：note_id / author_id / limit。"""





    try:





        ki = _intel()





        note_id = request.args.get("note_id", "")





        author_id = request.args.get("author_id", "")





        limit = min(int(request.args.get("limit", 50)), 200)





        return jsonify({"ok": True, "data": ki.analyze_comments_intent(





            note_id=note_id, author_id=author_id, limit=limit)})





    except Exception as e:





        return jsonify({"ok": False, "error": str(e)}), 500

















@kos_bp.route("/kos-identity", methods=["GET", "POST"])





def api_kos_identity():





    """KOS 号识别。GET: 单作者识别 author_id；POST: 全量刷新 limit。"""





    try:





        ki = _intel()





        if request.method == "POST":





            limit = min(int(request.args.get("limit", 500)), 2000)





            return jsonify({"ok": True, "data": ki.refresh_kos_identity(limit=limit)})





        author_id = request.args.get("author_id", "")





        if not author_id:





            return jsonify({"ok": False, "error": "author_id required"}), 400





        return jsonify({"ok": True, "data": ki.recognize_kos_identity(author_id)})





    except Exception as e:





        return jsonify({"ok": False, "error": str(e)}), 500

















@kos_bp.route("/competitor-benchmark", methods=["GET"])





def api_competitor_benchmark():





    """竞品对标（主品牌 vs 竞品实体，复用 hainan_cdf.json 消歧）。"""





    try:





        ki = _intel()





        return jsonify({"ok": True, "data": ki.competitor_benchmark()})





    except Exception as e:





        return jsonify({"ok": False, "error": str(e)}), 500

















# ---------------------------------------------------------------------------




# KOS Metrics 增量路由（CTR-KOS-METRICS-P1-01 · Phase A）




# ---------------------------------------------------------------------------




def _metrics():




    """延迟导入 KOS Metrics 模块（三阶漏斗 / 成本 / 分层 / KOC）。"""




    if "kos_metrics" not in sys.modules:




        import kos_metrics




    return sys.modules["kos_metrics"]














@kos_bp.route("/funnel", methods=["GET"])




def api_kos_funnel():




    """KOS 三阶漏斗：Viewership→WeCom→Sales。参数：entity=all|kos|brand, limit。"""




    try:




        km = _metrics()




        entity = request.args.get("entity", "all")




        limit = min(int(request.args.get("limit", 20)), 200)




        return jsonify({"ok": True, "data": km.funnel_metrics(entity=entity, limit=limit)})




    except Exception as e:




        return jsonify({"ok": False, "error": str(e)}), 500














@kos_bp.route("/cost", methods=["GET"])




def api_kos_cost():




    """KOS 成本指标：CPL/CPC/Cost-per-WeCom/Boosting 预算。参数：period。"""




    try:




        km = _metrics()




        period = request.args.get("period", "month")




        return jsonify({"ok": True, "data": km.cost_metrics(period=period)})




    except Exception as e:




        return jsonify({"ok": False, "error": str(e)}), 500














@kos_bp.route("/tier", methods=["GET"])




def api_kos_tier():




    """KOS 分层看板：Top5/Top6-10/Top11-20/Others 集中度 + 高/低产出画像。"""




    try:




        km = _metrics()




        limit = min(int(request.args.get("limit", 40)), 500)




        return jsonify({"ok": True, "data": km.tier_benchmark(limit=limit)})




    except Exception as e:




        return jsonify({"ok": False, "error": str(e)}), 500














@kos_bp.route("/koc-tier", methods=["GET"])




def api_kos_koc_tier():




    """KOC 分层判定。参数：interactions_24h, interactions_7d。"""




    try:




        km = _metrics()




        i24 = int(request.args.get("interactions_24h", 0))




        i7d = int(request.args.get("interactions_7d", 0))




        return jsonify({"ok": True, "data": km.koc_reward_tier(i24, i7d)})




    except Exception as e:




        return jsonify({"ok": False, "error": str(e)}), 500














@kos_bp.route("/manual", methods=["POST"])



def api_kos_manual():



    """手动回填单个 KOS 的 WeCom/Sales/Boosting 预算（Phase A；认证后可换官方 API 自动归因）。"""



    try:



        km = _metrics()



        body = request.get_json(silent=True) or {}



        kos_id = body.get("kos_id", "")



        if not kos_id:



            return jsonify({"ok": False, "error": "kos_id required"}), 400



        return jsonify({"ok": True, "data": km.set_manual(



            kos_id,



            wecom_add=body.get("wecom_add"),



            sales_amount=body.get("sales_amount"),



            boosting_budget=body.get("boosting_budget"),


            inquiry=body.get("inquiry"),


            clicks=body.get("clicks"),



        )})



    except Exception as e:



        return jsonify({"ok": False, "error": str(e)}), 500











@kos_bp.route("/campaign", methods=["POST"])



def api_kos_campaign():



    """KOC campaign 复盘聚合：KOC 数 / 曝光 / 互动 / High-intent comment / 分层。"""



    try:



        km = _metrics()



        body = request.get_json(silent=True) or {}



        campaign = body.get("campaign", "default")



        kocs = body.get("kocs", []) or []



        return jsonify({"ok": True, "data": km.koc_campaign_review(campaign, kocs)})



    except Exception as e:



        return jsonify({"ok": False, "error": str(e)}), 500











@kos_bp.route("/channel-roi", methods=["GET"])

def api_kos_channel_roi():

    """多渠道 ROI 对比：小红书/微信OA/私域 CPL·CPC·Cost-per-WeCom vs 基准。"""

    try:

        km = _metrics()

        return jsonify({"ok": True, "data": km.channel_roi()})

    except Exception as e:

        return jsonify({"ok": False, "error": str(e)}), 500





@kos_bp.route("/profile", methods=["GET"])
def api_kos_profile():
    """当前激活品牌 profile：品牌/主体词/排除词/采集关键词 + 聚光 Phase B 状态。"""
    try:
        import juguang_api
        from subject_rules import (
            collect_keywords_for,
            get_active_brand,
            get_brand_config,
        )
        brand = get_active_brand()
        cfg = get_brand_config(brand)
        return jsonify({"ok": True, "data": {
            "brand": brand,
            "display_name": cfg.get("display_name", brand),
            "region": cfg.get("region", ""),
            "store_type": cfg.get("store_type", ""),
            "subject_words": cfg.get("subject_words", []),
            "exclude_words": cfg.get("exclude_words", []),
            "collect_keywords": collect_keywords_for(brand),
            "juguang": juguang_api.verify_config(),
        }})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@kos_bp.route("/collect", methods=["POST"])
def api_kos_collect():
    """Compatibility entry into the canonical scoped secondary-collection flow."""
    try:
        body = request.get_json(silent=True)
        allowed = {"brand", "operator", "confirm_read_only", "max_results"}
        if not isinstance(body, dict) or set(body) - allowed:
            return jsonify({"ok": False, "status": "invalid_request",
                            "code": "INVALID_COLLECTION_REQUEST",
                            "read_only": True, "external_write": False}), 400
        operator = str(body.get("operator") or "").strip().lower()
        if operator not in {"human", "human_ui"}:
            return jsonify({"ok": False, "status": "denied", "code": "HUMAN_OPERATOR_REQUIRED",
                            "read_only": True, "external_write": False}), 403
        if body.get("confirm_read_only") is not True:
            return jsonify({"ok": False, "status": "input_required",
                            "code": "READ_ONLY_CONFIRMATION_REQUIRED"}), 400
        brand_key = body.get("brand")
        if not isinstance(brand_key, str) or not brand_key.strip():
            return jsonify({"ok": False, "status": "input_required", "code": "BRAND_REQUIRED"}), 400
        brand_key = brand_key.strip()
        raw_limit = body.get("max_results", 20)
        if type(raw_limit) is not int or not 1 <= raw_limit <= 20:
            return jsonify({"ok": False, "status": "invalid_request", "code": "MAX_RESULTS_OUT_OF_RANGE"}), 400

        from subject_rules import BRAND_PROFILES
        profile = BRAND_PROFILES.get(brand_key)
        if not isinstance(profile, dict):
            return jsonify({"ok": False, "status": "invalid_request", "code": "BRAND_PROFILE_UNKNOWN"}), 400

        from experience_runtime import _content_project_error, _content_project_scope
        from shared_artifacts import LocalArtifactError
        try:
            actor, scope = _content_project_scope("write", module="collector")
        except LocalArtifactError as exc:
            return _content_project_error(exc)
        if (scope.get("domain_id") not in {"bmp", "zbmp"}
                or not isinstance(scope.get("brand_focus_id"), str)
                or not scope["brand_focus_id"] or scope.get("global_scope") is True):
            return jsonify({"ok": False, "status": "denied", "code": "EXACT_BRAND_FOCUS_REQUIRED",
                            "read_only": True, "external_write": False}), 403

        from subject_registry import list_subjects
        entries = [entry for entry in list_subjects("BMP")
                   if entry.get("brand_focus_id") == scope["brand_focus_id"]]
        if len(entries) != 1:
            return jsonify({"ok": False, "status": "blocked", "code": "BRAND_FOCUS_NOT_UNIQUELY_REGISTERED",
                            "read_only": True, "external_write": False}), 503
        entry = entries[0]
        registered_terms = entry.get("keywords")
        if not isinstance(registered_terms, list):
            return jsonify({"ok": False, "status": "blocked", "code": "BRAND_TOPIC_TERMS_UNAVAILABLE",
                            "read_only": True, "external_write": False}), 503
        registered_names = {
            str(value).strip().casefold()
            for value in (entry.get("name_zh"), entry.get("name_en"), *registered_terms,
                          entry.get("subject_id"), entry.get("brand_focus_id"))
            if isinstance(value, str) and value.strip()
        }
        profile_names = {
            part.strip().casefold()
            for part in str(profile.get("display_name") or "").split("/")
            if part.strip()
        }
        if not profile_names.intersection(registered_names):
            return jsonify({"ok": False, "status": "denied", "code": "BRAND_PROFILE_SCOPE_MISMATCH",
                            "read_only": True, "external_write": False}), 403

        terms = []
        seen_terms = set()
        for value in (entry.get("name_zh"), entry.get("name_en"), *registered_terms):
            if isinstance(value, str) and value.strip() and value.strip().casefold() not in seen_terms:
                term = value.strip()
                seen_terms.add(term.casefold())
                terms.append(term)
        if not terms:
            return jsonify({"ok": False, "status": "blocked", "code": "BRAND_TOPIC_TERMS_UNAVAILABLE",
                            "read_only": True, "external_write": False}), 503

        from xhs_cookie_bridge import is_user_paused
        paused = is_user_paused()
        if paused and not os.environ.get("ZBC_TEST_MODE"):
            return jsonify({"ok": False, "status": "USER_PAUSED",
                            "reason": paused.get("reason", "采集已暂停"),
                            "brand_focus_id": scope["brand_focus_id"]}), 409

        from lumenis.system.collector.adapters.secondary_collection import (
            collect_search,
        )
        results = []
        stop_statuses = {
            "RISK_WARNING", "NEED_VERIFY", "SESSION_EXPIRED", "BLOCKED",
            "PROVIDER_UNAVAILABLE", "NOT_CONFIGURED", "RATE_LIMITED", "COOLING_DOWN",
            "SCOPE_UNAUTHORIZED", "APPROVAL_REQUIRED", "PERMISSION_UNAVAILABLE",
        }
        result_fields = {
            "ok", "status", "platform", "raw_count", "returned_count", "imported", "updated",
            "failed", "subject_matches", "canonical_synced", "native_fields_synced",
            "evidence_recorded", "evidence_ref", "scope_status", "refresh_verified",
            "error_type", "read_only", "external_write", "publish_authority",
        }
        for keyword in terms:
            try:
                result = collect_search(
                    "xiaohongshu", keyword, max_results=raw_limit,
                    operator=operator, actor=actor, scope=scope,
                )
            except Exception as exc:
                result = {"ok": False, "status": "ERROR", "error_type": type(exc).__name__}
            results.append({"keyword": keyword, **{
                field: result[field] for field in result_fields if field in result
            }})
            if str(result.get("status") or "").upper() in stop_statuses:
                break

        accepted_total = sum(
            int(result.get("imported", 0) or 0) + int(result.get("updated", 0) or 0)
            for result in results if result.get("ok") is True
        )
        all_terms_completed = len(results) == len(terms)
        all_succeeded = all(result.get("ok") is True for result in results) and all_terms_completed
        any_succeeded = any(result.get("ok") is True for result in results)
        status = "SUCCESS" if all_succeeded else "PARTIAL" if any_succeeded else (
            str(results[-1].get("status") or "ERROR").upper() if results else "ERROR"
        )
        try:
            collection_stats = _engine().brand_collection_stats(brand_key)
            collection_stats_status = "AVAILABLE"
        except Exception:
            collection_stats = None
            collection_stats_status = "UNAVAILABLE"
        return jsonify({
            "ok": all_succeeded, "status": status,
            "brand": entry.get("name_zh"), "brand_focus_id": scope["brand_focus_id"],
            "accepted_total": accepted_total, "collection": collection_stats,
            "collection_stats_status": collection_stats_status,
            "query_count": len(results), "query_total": len(terms), "results": results,
        }), 200 if all_succeeded or any_succeeded else 503
    except Exception as exc:
        return jsonify({"ok": False, "status": "unavailable",
                        "code": "KOS_COLLECTION_UNAVAILABLE",
                        "error_type": type(exc).__name__}), 503


@kos_bp.route("/brand", methods=["GET"])
def api_kos_brand():
    """品牌采集状态 + KOS 实时聚合（不写 kos_profiles，与广州主链隔离）+ 主体归属 Gate 视图。"""
    try:
        brand = (request.args.get("brand") or "").strip()
        if not brand:
            return jsonify({"ok": False, "error": "brand required"}), 400
        ke = _engine()
        limit = int(request.args.get("limit", 20) or 20)
        profiles = ke.brand_profiles(brand, limit=limit)
        rows = []
        for p in profiles:
            rows.append({**p, "ownership": ke.ownership_for(p, brand=brand)})
        return jsonify({"ok": True, "brand": brand,
                        "stats": ke.brand_collection_stats(brand),
                        "profiles": rows}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@kos_bp.route("/ownership", methods=["GET"])
def api_kos_ownership():
    """主体归属 Gate 视图：按品牌返回 KOS 归属判定（内容相关≠KOS；needs_manual_review 为人工复核清单）。"""
    try:
        brand = (request.args.get("brand") or "").strip()
        author_id = (request.args.get("author_id") or "").strip()
        ke = _engine()
        limit = int(request.args.get("limit", 50) or 50)
        if author_id:
            p = ke.get_profile(author_id)
            if not p:
                return jsonify({"ok": False, "error": "author not found"}), 404
            return jsonify({"ok": True, "author_id": author_id,
                            "ownership": ke.ownership_for(p, brand=brand)}), 200
        if brand:
            profiles = ke.brand_profiles(brand, limit=limit)
            rows = []
            for p in profiles:
                own = ke.ownership_for(p, brand=brand)
                # 增强：relevance + interaction（确定性视图，不写库）
                try:
                    acc = ke.brand_kos_account(brand, p["author_id"], limit=20)
                    rel = {"avg_relevance": acc["avg_relevance"], "relevance_segment": acc["relevance_segment"]} if acc else {}
                    inter = acc["interaction"] if acc and acc.get("interaction") else {}
                except Exception:
                    rel, inter = {}, {}
                rows.append({**p, "ownership": own, "relevance": rel, "interaction": inter})
            return jsonify({"ok": True, "brand": brand, "count": len(rows),
                            "needs_review": sum(1 for r in rows if r["ownership"]["needs_manual_review"]),
                            "profiles": rows}), 200
        return jsonify({"ok": False, "error": "brand or author_id required"}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@kos_bp.route("/execution", methods=["POST"])
def api_kos_execution_create():
    """HCG：创建门控执行（初始 AI_GENERATED，不执行；敏感动作必须人工审核）。"""
    try:
        import kos_execution as _kx
        body = request.get_json(silent=True) or {}
        action_type = (body.get("action_type") or "").strip()
        if action_type not in _kx.GATED_ACTIONS:
            return jsonify({"ok": False,
                            "error": f"action_type 必须在 HCG 门控动作内: {sorted(_kx.GATED_ACTIONS)}"}), 400
        rec = _kx.create_execution(action_type=action_type,
                                   target_author_id=body.get("target_author_id", ""),
                                   target_brand=body.get("target_brand", ""),
                                   payload=body.get("payload"),
                                   actor=body.get("actor", "AI"),
                                   version=body.get("version", "v1"))
        return jsonify({"ok": True, "execution": rec,
                        "message": "AI_GENERATED，等待人工审核（HUMAN_CONTROL_GATE）"}), 201
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@kos_bp.route("/execution/<execution_id>/transition", methods=["POST"])
def api_kos_execution_transition(execution_id):
    """HCG：状态机转移（approve/execute/...）。敏感动作必须带 actor。"""
    try:
        import kos_execution as _kx
        body = request.get_json(silent=True) or {}
        to_status = (body.get("status") or body.get("to_status") or "").strip().upper()
        if not to_status:
            return jsonify({"ok": False, "error": "status required"}), 400
        rec = _kx.transition(execution_id, to_status, actor=body.get("actor", ""),
                             payload=body.get("payload"), result=body.get("result", ""),
                             evidence_ref=body.get("evidence_ref", ""),
                             failure_reason=body.get("failure_reason", ""))
        return jsonify({"ok": True, "execution": rec}), 200
    except (ValueError, KeyError) as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@kos_bp.route("/executions", methods=["GET"])
def api_kos_executions():
    """HCG：执行审计列表（可按 status/action_type/author 过滤）。"""
    try:
        import kos_execution as _kx
        rows = _kx.list_executions(status=request.args.get("status", ""),
                                   action_type=request.args.get("action_type", ""),
                                   target_author_id=request.args.get("author_id", ""),
                                   limit=int(request.args.get("limit", 50) or 50))
        return jsonify({"ok": True, "count": len(rows), "executions": rows}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@kos_bp.route("/account", methods=["GET"])
def api_kos_account():
    """品牌 KOS 单账号 360° 视图（ownership + relevance + interaction，纯视图不写库）。"""
    try:
        ke = _engine()
        brand = (request.args.get("brand") or "").strip()
        author_id = (request.args.get("author_id") or "").strip()
        if not brand or not author_id:
            return jsonify({"ok": False, "error": "brand and author_id required"}), 400
        acc = ke.brand_kos_account(brand, author_id, limit=20)
        if not acc:
            return jsonify({"ok": False, "error": "account not found in brand scope"}), 404
        return jsonify({"ok": True, "account": acc}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@kos_bp.route("/ownership/confirm", methods=["POST"])
def api_kos_ownership_confirm():
    """人工确认 KOS 主体归属（AI 只建议不越权，确认后 VERIFIED；写 override 文件，不碰 DB）。"""
    try:
        ke = _engine()
        body = request.get_json(silent=True) or {}
        brand = (body.get("brand") or "").strip()
        author_id = (body.get("author_id") or "").strip()
        ownership_class = (body.get("ownership_class") or "").strip()
        confirmed_by = (body.get("confirmed_by") or "zachary").strip()
        if not author_id or not ownership_class:
            return jsonify({"ok": False, "error": "author_id and ownership_class required"}), 400
        rec = ke.ownership_confirm(brand, author_id, ownership_class, confirmed_by=confirmed_by)
        return jsonify({"ok": True, "confirmed": rec}), 200
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@kos_bp.route("/ownership/overrides", methods=["GET"])
def api_kos_ownership_overrides():
    """查看已人工确认的归属 override 列表。"""
    try:
        ke = _engine()
        data = ke._load_overrides()
        rows = list(data.values())
        return jsonify({"ok": True, "count": len(rows), "overrides": rows}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500



# ===== KOS 运营模块端点（kos_ops.py：留资/合作/邮件邀约/运营闭环） =====
@kos_bp.route("/lead", methods=["GET", "POST"])
def api_kos_lead():
    """留资管理：POST 保存/更新留资；GET 查询单条。"""
    import kos_ops as ko
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        aid = str(data.get("author_id", "")).strip()
        if not aid:
            return jsonify({"ok": False, "error": "author_id 必填"}), 400
        return jsonify(ko.save_lead(
            aid,
            contact_name=str(data.get("contact_name", "")),
            phone=str(data.get("phone", "")),
            wechat=str(data.get("wechat", "")),
            email=str(data.get("email", "")),
            mcn=str(data.get("mcn", "")),
            company=str(data.get("company", "")),
            actor=str(data.get("actor", "AI")),
        ))
    aid = str(request.args.get("author_id", "")).strip()
    if not aid:
        return jsonify({"ok": False, "error": "author_id 必填"}), 400
    return jsonify(ko.get_lead(aid))


@kos_bp.route("/cooperation", methods=["GET", "POST"])
def api_kos_cooperation():
    """合作状态：POST 更新草稿；GET 查询。"""
    import kos_ops as ko
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        aid = str(data.get("author_id", "")).strip()
        if not aid:
            return jsonify({"ok": False, "error": "author_id 必填"}), 400
        return jsonify(ko.update_cooperation(
            aid,
            cooperation_status=str(data.get("cooperation_status", "NONE")),
            quote=float(data.get("quote", 0) or 0),
            budget=float(data.get("budget", 0) or 0),
            note=str(data.get("note", "")),
            actor=str(data.get("actor", "AI")),
        ))
    aid = str(request.args.get("author_id", "")).strip()
    if not aid:
        return jsonify({"ok": False, "error": "author_id 必填"}), 400
    r = ko.get_lead(aid)
    return jsonify({**r, "cooperation_status": _kos_profile_field(aid, "cooperation_status"),
                    "quote": _kos_profile_field(aid, "quote"), "budget": _kos_profile_field(aid, "budget")})


@kos_bp.route("/cooperation/confirm", methods=["POST"])
def api_kos_cooperation_confirm():
    """商务合作确认（HCG cooperation_confirm 门控）：登记 execution，待人工审批。"""
    import kos_ops as ko
    data = request.get_json(silent=True) or {}
    aid = str(data.get("author_id", "")).strip()
    if not aid:
        return jsonify({"ok": False, "error": "author_id 必填"}), 400
    return jsonify(ko.confirm_cooperation(
        aid, confirmed_by=str(data.get("confirmed_by", "zachary")),
        quote=float(data.get("quote", 0) or 0), budget=float(data.get("budget", 0) or 0)))


@kos_bp.route("/cooperation/execute", methods=["POST"])
def api_kos_cooperation_execute():
    """人工审批后执行合作确认（HCG EXECUTING -> SUCCESS）。"""
    import kos_ops as ko
    data = request.get_json(silent=True) or {}
    eid = str(data.get("execution_id", "")).strip()
    actor = str(data.get("actor", "")).strip()
    if not eid or not actor:
        return jsonify({"ok": False, "error": "execution_id 与 actor 必填"}), 400
    return jsonify(ko.execute_cooperation(eid, actor))


@kos_bp.route("/email/invitation", methods=["POST"])
def api_kos_email_invitation():
    """创建邮件邀约（HCG email_send 门控：AI_GENERATED，不发送）。"""
    import kos_ops as ko
    data = request.get_json(silent=True) or {}
    aid = str(data.get("author_id", "")).strip()
    if not aid:
        return jsonify({"ok": False, "error": "author_id 必填"}), 400
    return jsonify(ko.create_invitation_email(
        aid, subject=str(data.get("subject", "")), body=str(data.get("body", "")),
        actor=str(data.get("actor", "AI"))))


@kos_bp.route("/email/send", methods=["POST"])
def api_kos_email_send():
    """人工审批后发送邮件（HCG EXECUTING -> SUCCESS/FAILED）。"""
    import kos_ops as ko
    data = request.get_json(silent=True) or {}
    eid = str(data.get("execution_id", "")).strip()
    actor = str(data.get("actor", "")).strip()
    if not eid or not actor:
        return jsonify({"ok": False, "error": "execution_id 与 actor 必填"}), 400
    return jsonify(ko.send_invitation_email(eid, actor))


@kos_bp.route("/operations", methods=["GET"])
def api_kos_operations():
    """运营动作台账（按 author_id 或全局）。"""
    import kos_ops as ko
    aid = str(request.args.get("author_id", "")).strip()
    limit = int(request.args.get("limit", 50))
    return jsonify({"ok": True, "operations": ko.operation_log(aid, limit=limit)})


@kos_bp.route("/operation", methods=["POST"])
def api_kos_record_operation():
    """记录运营动作并推进生命周期。"""
    import kos_ops as ko
    data = request.get_json(silent=True) or {}
    aid = str(data.get("author_id", "")).strip()
    action = str(data.get("action", "")).strip()
    if not aid or not action:
        return jsonify({"ok": False, "error": "author_id 与 action 必填"}), 400
    return jsonify(ko.record_operation(aid, action, note=str(data.get("note", "")),
                                       actor=str(data.get("actor", "AI"))))



# ===== KOS P2 投流与奖励端点（kos_paid.py） =====
@kos_bp.route("/paid/plan", methods=["POST"])
def api_kos_paid_plan():
    """创建投流计划（HCG paid_media 门控：AI_GENERATED，不实际投放）。"""
    import kos_paid as kp
    data = request.get_json(silent=True) or {}
    return jsonify(kp.create_paid_plan(
        author_id=str(data.get("author_id", "")),
        note_id=str(data.get("note_id", "")),
        budget=float(data.get("budget", 0) or 0),
        channel=str(data.get("channel", "xhs")),
        expected_reach=int(data.get("expected_reach", 0) or 0),
        actor=str(data.get("actor", "AI"))))


@kos_bp.route("/paid/execute", methods=["POST"])
def api_kos_paid_execute():
    """人工审批后执行投流计划。"""
    import kos_paid as kp
    data = request.get_json(silent=True) or {}
    eid, actor = str(data.get("execution_id", "")).strip(), str(data.get("actor", "")).strip()
    if not eid or not actor:
        return jsonify({"ok": False, "error": "execution_id 与 actor 必填"}), 400
    return jsonify(kp.execute_paid_plan(eid, actor))


@kos_bp.route("/paid/result", methods=["POST"])
def api_kos_paid_result():
    """记录投流效果反馈（真实投放数据，ROI 可测算不伪造）。"""
    import kos_paid as kp
    data = request.get_json(silent=True) or {}
    return jsonify(kp.record_paid_result(
        str(data.get("plan_id", "")), spend=float(data.get("spend", 0) or 0),
        impressions=int(data.get("impressions", 0) or 0), clicks=int(data.get("clicks", 0) or 0),
        conversions=int(data.get("conversions", 0) or 0)))


@kos_bp.route("/paid/plans", methods=["GET"])
def api_kos_paid_plans():
    import kos_paid as kp
    aid = str(request.args.get("author_id", "")).strip()
    return jsonify({"ok": True, "plans": kp.paid_plans(aid)})


@kos_bp.route("/reward/issue", methods=["POST"])
def api_kos_reward_issue():
    """创建奖励发放（HCG reward_issue 门控：AI_GENERATED，不实际发放）。"""
    import kos_paid as kp
    data = request.get_json(silent=True) or {}
    return jsonify(kp.issue_reward(
        str(data.get("author_id", "")), points=float(data.get("points", 0) or 0),
        amount=float(data.get("amount", 0) or 0), reason=str(data.get("reason", "")),
        actor=str(data.get("actor", "AI"))))


@kos_bp.route("/reward/execute", methods=["POST"])
def api_kos_reward_execute():
    """人工审批后发放奖励。"""
    import kos_paid as kp
    data = request.get_json(silent=True) or {}
    eid, actor = str(data.get("execution_id", "")).strip(), str(data.get("actor", "")).strip()
    if not eid or not actor:
        return jsonify({"ok": False, "error": "execution_id 与 actor 必填"}), 400
    return jsonify(kp.execute_reward(eid, actor))


@kos_bp.route("/rewards", methods=["GET"])
def api_kos_rewards():
    import kos_paid as kp
    aid = str(request.args.get("author_id", "")).strip()
    return jsonify({"ok": True, "rewards": kp.reward_ledger(aid)})



def _kos_profile_field(author_id: str, field: str):
    """辅助：读取 kos_profiles 单字段。"""
    from lumenis.shared.database import get_repository
    conn = get_repository().connect()
    try:
        r = conn.execute(f"SELECT {field} FROM kos_profiles WHERE author_id = ?", (author_id,)).fetchone()
        return r[0] if r else None
    finally:
        conn.close()


def _DB():
    from lumenis.shared.database import main_db_path
    return main_db_path()





# ============ 专业号接入口（每品牌可选，默认关闭，熔断保护） ============

def _professional():
    try:
        import kos_professional as kp
        return kp
    except Exception as e:
        print(f"[KOS] professional module unavailable: {e}")
        return None


@kos_bp.route("/professional/status", methods=["GET"])
def api_professional_status():
    """查询某品牌专业号接入状态。未开启返回 disabled。"""
    try:
        brand_id = request.args.get("brand_id", "default")
        platform = request.args.get("platform", "xiaohongshu")
        kp = _professional()
        if not kp:
            return jsonify({"ok": True, "enabled": False, "accounts": [], "module": "unavailable"})
        accounts = kp.list_accounts(brand_id)
        enabled = kp.is_enabled(brand_id, platform)
        return jsonify({"ok": True, "enabled": enabled, "brand_id": brand_id,
                        "platform": platform, "accounts": accounts,
                        "account_count": len(accounts), "state": "CONNECTED" if enabled else "DISABLED"})
    except Exception as e:
        return jsonify({"ok": False, "enabled": False, "error": str(e)})


@kos_bp.route("/professional/enable", methods=["POST"])
def api_professional_enable():
    """开启某品牌专业号接入（按钮触发）。"""
    try:
        data = request.get_json(silent=True) or {}
        brand_id = data.get("brand_id", "default")
        platform = data.get("platform", "xiaohongshu")
        account_id = data.get("account_id", "")
        account_name = data.get("account_name", "")
        verified_type = data.get("verified_type", "")
        if not account_id:
            return jsonify({"ok": False, "error": "account_id required"})
        kp = _professional()
        if not kp:
            return jsonify({"ok": False, "error": "module unavailable"})
        result = kp.enable(brand_id, platform, account_id, account_name, verified_type)
        return jsonify(result)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@kos_bp.route("/professional/disable", methods=["POST"])
def api_professional_disable():
    """关闭某品牌专业号接入。"""
    try:
        data = request.get_json(silent=True) or {}
        brand_id = data.get("brand_id", "default")
        platform = data.get("platform", "xiaohongshu")
        account_id = data.get("account_id", "")
        kp = _professional()
        if not kp:
            return jsonify({"ok": False, "error": "module unavailable"})
        result = kp.disable(brand_id, platform, account_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@kos_bp.route("/professional/import", methods=["POST"])
def api_professional_import():
    """导入专业号后台数据（仅开启后可用）。"""
    try:
        data = request.get_json(silent=True) or {}
        brand_id = data.get("brand_id", "default")
        account_id = data.get("account_id", "")
        metrics = data.get("metrics", [])
        source = data.get("source", "import")
        if not account_id or not metrics:
            return jsonify({"ok": False, "error": "account_id and metrics required"})
        kp = _professional()
        if not kp:
            return jsonify({"ok": False, "error": "module unavailable"})
        result = kp.import_metrics(brand_id, account_id, metrics, source)
        return jsonify(result)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@kos_bp.route("/professional/metrics", methods=["GET"])
def api_professional_metrics():
    """查询专业号指标。未开启返回空列表。"""
    try:
        brand_id = request.args.get("brand_id", "default")
        account_id = request.args.get("account_id", "")
        start_date = request.args.get("start_date", "")
        end_date = request.args.get("end_date", "")
        kp = _professional()
        if not kp:
            return jsonify({"ok": True, "metrics": [], "enabled": False})
        metrics = kp.get_metrics(brand_id, account_id, start_date, end_date)
        return jsonify({"ok": True, "brand_id": brand_id, "metrics": metrics,
                        "enabled": kp.is_enabled(brand_id)})
    except Exception as e:
        return jsonify({"ok": False, "metrics": [], "error": str(e)})


def register_kos_api(app):





    """注册 KOS Blueprint 到 Flask app。"""





    app.register_blueprint(kos_bp)




