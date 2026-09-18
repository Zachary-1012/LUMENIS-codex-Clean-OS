# -*- coding: utf-8 -*-





"""Z-Brand-Core KOS API Blueprint（KOS 传播主体 API）











复用 kos_engine.py 与 Shared Reporting KOS owner，不重复建设。





API 统一前缀 /api/kos/。





"""





from flask import Blueprint, request, jsonify, send_from_directory





# KOS采集专用香港账号（rednote_hk）
try:
    from dual_account_rotation import select_account_for_collection
    KOS_DUAL_ACCOUNT = True
except ImportError:
    KOS_DUAL_ACCOUNT = False

import os, sys





from pathlib import Path











kos_bp = Blueprint("kos", __name__, url_prefix="/api/kos")











# 延迟导入，避免循环依赖





def _engine():





    if "kos_engine" not in sys.modules:





        import kos_engine





    return sys.modules["kos_engine"]











def _report():
    from lumenis.shared.reporting import kos as kos_report
    return kos_report


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





    """生成博主触达邀约文案（DRAFT 状态，不伪造已发送）。"""





    try:





        ke = _engine()





        data = request.get_json(silent=True) or {}





        author_id = data.get("author_id", "")





        brand_name = data.get("brand_name", "广州太古汇")





        campaign_name = data.get("campaign_name", "")





        if not author_id:





            return jsonify({"ok": False, "error": "author_id required"}), 400





        result = ke.generate_outreach(author_id, brand_name=brand_name, campaign_name=campaign_name)





        # HCG（HUMAN_CONTROL_GATE_v1）：生成触达/邀约文案 → 登记 AI_GENERATED 执行（DRAFT，不伪造已发送）
        if isinstance(result, dict) and result.get("ok", True):
            try:
                import kos_execution as _kx
                _exec = _kx.create_execution(
                    action_type="outreach_send",
                    target_author_id=data.get("author_id", ""),
                    target_brand=data.get("brand_name", ""),
                    payload={"campaign_name": data.get("campaign_name", ""),
                             "generated_draft": result.get("draft") or result.get("content") or ""},
                    actor="AI")
                result["hcg"] = {"status": "AI_GENERATED", "execution_id": _exec["execution_id"],
                                 "note": "生成≠已发送；人工审核通过后才可执行触达"}
            except Exception as _e:
                result["hcg"] = {"status": "HCG_ERROR", "error": str(_e)}
        return jsonify(result)





    except Exception as e:





        return jsonify({"ok": False, "error": str(e)}), 500

















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





    """生成 KOS 动态 HTML 报告。"""





    try:





        kr = _report()





        data = request.get_json(silent=True) or {}





        brand_name = data.get("brand_name", "广州太古汇")





        result = kr.generate_report(brand_name=brand_name)





        return jsonify(result)





    except Exception as e:





        return jsonify({"ok": False, "error": str(e)}), 500

















@kos_bp.route("/report/view", methods=["GET"])





def api_report_view():





    """查看最新 KOS 报告（静态 HTML）。"""





    try:





        report_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "reports")





        if not os.path.exists(report_dir):





            return jsonify({"ok": False, "error": "No reports found"}), 404





        files = sorted([f for f in os.listdir(report_dir) if f.endswith(".html") and f.startswith("KOS_Report")], reverse=True)





        if not files:





            return jsonify({"ok": False, "error": "No KOS reports found"}), 404





        return send_from_directory(report_dir, files[0])





    except Exception as e:





        return jsonify({"ok": False, "error": str(e)}), 500





























@kos_bp.route("/reply/generate", methods=["POST"])





def api_reply_generate():





    """生成评论回复建议（高风险NO_REPLY）。"""





    try:





        ke = _engine()





        data = request.get_json(silent=True) or {}





        result = ke.generate_reply(





            comment_text=data.get("comment_text", ""),





            brand_name=data.get("brand_name", "广州太古汇"),





            reply_style=data.get("reply_style", "professional"),





            risk_level=data.get("risk_level", "low"),





        )





        # HCG（HUMAN_CONTROL_GATE_v1）：生成回复建议 → 登记 AI_GENERATED 执行（待人工审核，不自动发送）
        if isinstance(result, dict) and result.get("ok", True) and result.get("action") != "NO_REPLY":
            try:
                import kos_execution as _kx
                _exec = _kx.create_execution(
                    action_type="reply_send",
                    target_author_id=data.get("author_id", ""),
                    target_brand=data.get("brand_name", ""),
                    payload={"comment_text": data.get("comment_text", ""),
                             "reply_style": data.get("reply_style", "professional"),
                             "generated_reply": result.get("reply") or result.get("draft") or ""},
                    actor="AI")
                result["hcg"] = {"status": "AI_GENERATED", "execution_id": _exec["execution_id"],
                                 "note": "生成≠已发送；人工审核通过后才可执行回复"}
            except Exception as _e:
                result["hcg"] = {"status": "HCG_ERROR", "error": str(_e)}
        return jsonify(result)





    except Exception as e:





        return jsonify({"ok": False, "error": str(e)}), 500

















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





    """KOS多触点归因（单KOS或多触点）。"""





    try:





        import kos_attribution





        author_id = request.args.get("author_id", "")





        note_ids = request.args.get("note_ids", "")





        brand_name = request.args.get("brand_name", "广州太古汇")





        if author_id:





            result = kos_attribution.calculate_attribution(author_id, brand_name=brand_name)





        elif note_ids:





            nids = [n.strip() for n in note_ids.split(",") if n.strip()]





            result = kos_attribution.calculate_multi_touch_attribution(nids, brand_name=brand_name)





        else:





            return jsonify({"ok": False, "error": "author_id or note_ids required"}), 400





        return jsonify(result)





    except Exception as e:





        return jsonify({"ok": False, "error": str(e)}), 500











def _intel():





    """延迟导入 KOS Intel 增量模块（意向分层 / KOS号识别 / 竞品对标）。"""





    if "kos_intel" not in sys.modules:





        import kos_intel





    return sys.modules["kos_intel"]

















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
        from subject_rules import get_active_brand, get_brand_config, collect_keywords_for
        import juguang_api
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
    """品牌采集：统一暂停门 + 品牌主体过滤 + CDP 复用（链路复用 live_engine，不重写采集逻辑）。

    遵循统一采集规则：is_user_paused() 暂停门（与主链同一规则）；主体过滤用 subject_hit_for_brand
    （品牌词/排除词，不修改全局激活品牌口径）；CDP 复用常驻浏览器（不 new browser）。
    数据隔离：笔记落库 source_keyword=品牌采集词（方案 A），KOS 聚合按品牌实时计算，不污染广州。
    """
    try:
        from subject_rules import collect_keywords_for, subject_hit_for_brand
        from xhs_cookie_bridge import is_user_paused, cdp_url_for, XHS_RETINAUT_NAME
        body = request.get_json(silent=True) or {}
        brand = (body.get("brand") or request.args.get("brand") or "").strip()
        if not brand:
            return jsonify({"ok": False, "error": "brand required"}), 400
        kws = collect_keywords_for(brand)
        if not kws:
            return jsonify({"ok": False, "error": f"no collect keywords for brand: {brand}"}), 400
        # 统一暂停门（与主链同一规则；测试模式豁免）
        paused = is_user_paused()
        if paused and not os.environ.get("ZBC_TEST_MODE"):
            return jsonify({"ok": False, "status": "USER_PAUSED",
                            "reason": paused.get("reason", "采集已暂停"), "brand": brand}), 200
        cdp_url = (body.get("cdp_url") or "").strip() or cdp_url_for(XHS_RETINAUT_NAME)  # KOS 统一香港账号采集（用户指令，可 body 覆盖）
        comments = bool(body.get("comments", True))
        from collector_v2.xhs.live_engine import run_live, persist_live

        def brand_hit(text):
            try:
                return subject_hit_for_brand(title=str(text or ""), brand_key=brand)
            except Exception:
                return False

        max_scroll = int(body.get("max_scroll", 5) or 5)
        max_details = int(body.get("max_details", 20) or 20)
        max_comment_pages = int(body.get("max_comment_pages", 5) or 5)
        results, accepted_total = [], 0
        for kw in kws:
            data = run_live(kw, max_scroll=max_scroll, max_details=max_details,
                            max_comment_pages=max_comment_pages, comments=comments, cdp_url=cdp_url)
            stats = persist_live(data, brand_hit)
            accepted_total += int(stats.get("persisted", 0))
            results.append({"keyword": kw, "stats": stats,
                            "verification_required": data.get("verification_required", False)})
        ke = _engine()
        return jsonify({"ok": True, "brand": brand, "accepted_total": accepted_total,
                        "collection": ke.brand_collection_stats(brand), "results": results}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


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
    import sqlite3
    conn = sqlite3.connect(_DB())
    try:
        r = conn.execute(f"SELECT {field} FROM kos_profiles WHERE author_id = ?", (author_id,)).fetchone()
        return r[0] if r else None
    finally:
        conn.close()


def _DB():
    import os
    from pathlib import Path
    return os.environ.get("ZBC_DB_PATH", str(Path(__file__).parent / "data" / "monitor.db"))





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




