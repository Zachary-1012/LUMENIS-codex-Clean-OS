# -*- coding: utf-8 -*-
"""三方视角分级适配器（甲方 / 乙方 / 丙方）。

研究依据：广告行业三方分工与决策链路差异（广告主=付费方/需求方/最终决策者；
代理商/4A=服务方/创意与策略执行，靠平台返点+人效；平台/媒介/达人/独立第三方=
资源方/规则制定者/流量分配者）。国际评估标准（VoxComm/Hamilton Sherwind/Agency
Selection 2026）：甲方选乙方权重≈战略洞察30% / 创意25% / 团队20% / 测量ROI15% / 价格10%；
甲方买的是"confidence + measurable business outcome"，报告连 revenue 不连 vanity metric；
丙方强调整合资源/排期/结算/合规/品牌安全（MFA/IVT/Brand Suitability/TrueCPM）。

能力：把同一份方案（campaign_plan 输出）或同一个创意（idea_generator 输出），
按观众视角换语言与信息优先级，输出"给甲方的版本 / 给乙方的版本 / 给丙方的版本"。
视角是呈现层适配，不改变事实与创意本体（形可变，道不可移）。

用法：
  from scripts.perspective_adapter import adapt_plan, adapt_idea, perspective_brief
  plan = campaign_plan.generate_plan(...)
  client_view = adapt_plan(plan, "client")   # 给品牌方/金主
  agency_view = adapt_plan(plan, "agency")   # 给代理商/比稿
  vendor_view = adapt_plan(plan, "vendor")   # 给平台/媒介/执行方
"""
import json
import copy
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ---- 三方角色档案（研究提炼）----
PERSPECTIVES = {
    "client": {
        "role": "甲方",
        "role_name": "品牌方 / 需求方 / 金主",
        "positioning": "付费方，项目主导方，最终决策者；用最少的钱达成最好的生意结果",
        "core_concern": "ROI、预算控制、品牌资产沉淀、效果可测、内部汇报与决策证据、风险可控",
        "language": "生意语言：增长 / 回报 / 预算 / 数据 / 资产 / 风险",
        "decision_priorities": [
            "战略洞察（是否真的懂我的生意）",
            "创意（是否独特、可记忆、配得上品牌）",
            "测量与ROI（效果是否连得到生意结果）",
            "执行与团队（能否兑现、谁来做）",
            "价格与商业条款（透明、合理）",
        ],
        "kpi": "声量→互动→转化→私域资产的完整链路，且必须能连到 GMV / 新客 / 留存 / LTV（而非只看曝光）",
        "evidence_demands": "要真实数据、前后对比、可复现口径；拒绝 vanity metric 与不可解释的归因",
        "output_focus": "决策摘要 → 商业价值 → 预算回报逻辑 → 关键创意 → 执行计划 → 效果衡量(连生意) → 风险与保障 → 下一步",
        "call_to_action": "给决策依据与下一步验收节点（拍板/预算/时间表）",
        "international_benchmark": "对标：CMO 在董事会压力下要可预测 pipeline；甲方评价=战略洞察/创意/测量ROI/团队/价格",
    },
    "agency": {
        "role": "乙方",
        "role_name": "代理商 / 4A / 数字营销 / 公关 / 执行服务方",
        "positioning": "承接需求、提供专业服务、收取费用的创意与策略执行方",
        "core_concern": "策略成立、创意独特、说服客户、执行落地、成本毛利与人效、能力证明与比稿胜率",
        "language": "方法论语言：洞察 / 概念 / 策略 / 差异化 / 整合 / 执行",
        "decision_priorities": [
            "洞察是否锋利（对人、对品类、对文化）",
            "创意是否敢于做原创而非拼贴",
            "策略-创意-执行是否闭环（讲得通、做得到）",
            "资源整合与媒介组合是否最优",
            "报价与成本结构（返点透明化下靠人效胜出）",
        ],
        "kpi": "服务目标（客户目标）+ 自身运营指标（人效、返点、毛利率、产能）；AI 能力成为生存关键",
        "evidence_demands": "用案例证明方法论与真实结果（brief→约束→策略→可测结果），非 logo 墙",
        "output_focus": "Brief理解 → 洞察 → 策略 → Big Idea → 创意落地 → 整合触点 → 媒介 → 执行节奏 → 效果 → 风险 → 我方方法论/优势",
        "call_to_action": "给客户的明确下一步（确认方向/预算/节点）并展示我方差异化",
        "international_benchmark": "对标：阳狮/WPP/奥美比稿=策略×创意×执行力；Raut: 现在拼 ideas+chemistry+AI+data security+commercials",
    },
    "vendor": {
        "role": "丙方",
        "role_name": "平台 / 媒介 / 达人 / MCN / 制作 / 独立第三方",
        "positioning": "资源方、规则制定者、流量分配者；为乙方/甲方提供流量、渠道、制作与验证",
        "core_concern": "资源与流量、排期、结算口径、平台规则、合规与品牌安全、效果承诺与验收标准",
        "language": "平台语言：资源包 / 刊例 / 排期 / 消耗 / 核减 / 结算 / 合规分 / 品牌安全",
        "decision_priorities": [
            "资源与能力（流量、人群包、内容、制作产能）",
            "执行颗粒度（SOP、排期、对接人、验收标准）",
            "结算与成本（CPM/CPC/CPA/CPT、返点、核减规则）",
            "合规与安全（平台规则、品牌安全 MFA/IVT/内容适宜性）",
            "数据透明与可验证（三方监测、独立验证）",
        ],
        "kpi": "消耗、曝光/点击/转化、素材过审率、结算核对、品牌安全指标（0.4% MFA 基准线等）、合作续约",
        "evidence_demands": "透明的数据与结算对账（ANA TrueAdSpend/TrueCPM 基准；独立第三方验证更受信任）",
        "output_focus": "资源需求 → 渠道/达人组合 → 投放与排期 → 执行SOP → 结算口径 → 合规/品牌安全 → 效果承诺 → 验收标准",
        "call_to_action": "给明确资源包、排期、报价与验收清单（可直接进采购/下单）",
        "international_benchmark": "对标：平台/媒介质量（IAS 21st）与程序化透明度（ANA）规范；独立第三方（如 DV）以透明算法取胜",
    },
}

# 视角 → 该视角最关心的方案章节（对 campaign_plan 的 sections 重排）
_PERSPECTIVE_SECTION_ORDER = {
    "client": ["Brief 理解与重构", "核心策略", "Big Idea / 创意概念", "整合传播规划", "媒介与资源",
               "效果衡量", "风险与合规", "执行节奏"],
    "agency": ["Brief 理解与重构", "市场与消费者洞察", "核心策略", "Big Idea / 创意概念", "创意落地",
               "整合传播规划", "媒介与资源", "执行节奏", "效果衡量", "风险与合规"],
    "vendor": ["媒介与资源", "整合传播规划", "执行节奏", "效果衡量", "风险与合规"],
}


def perspective_brief(role):
    """返回某视角的档案卡（做任何方案前先定位观众）。role: client/agency/vendor。"""
    return PERSPECTIVES.get(role, PERSPECTIVES["agency"])


def adapt_plan(plan, perspective="agency", *, summary=False):
    """把统一方案 plan（campaign_plan.generate_plan 输出）转成指定视角的呈现视图。

    默认保留全部原章节，包括用户自建章节；summary=True才显式生成摘要。
    每个视图带完整原稿快照引用，不修改或共享可变原稿内容。
    """
    if not isinstance(summary, bool):
        raise ValueError("summary must be a boolean")
    p = perspective_brief(perspective)
    sections = plan.get("sections", {})
    order = _PERSPECTIVE_SECTION_ORDER.get(perspective, list(sections.keys()))
    selected = [k for k in order if k in sections]
    remaining = [k for k in sections if k not in selected]
    if not summary:
        selected.extend(remaining)
    ordered = {k: copy.deepcopy(sections[k]) for k in selected}
    # 视角专属补充（从 plan 的事实中提炼，不新增无据信息）
    meta = copy.deepcopy(plan.get("meta", {}))
    play = copy.deepcopy(plan.get("category_playbook", ""))
    touch = copy.deepcopy(plan.get("touchpoints", []))
    risk = copy.deepcopy(plan.get("risk", ""))
    return {
        "role": p["role"],
        "role_name": p["role_name"],
        "perspective_lens": {
            "positioning": p["positioning"],
            "core_concern": p["core_concern"],
            "language": p["language"],
            "decision_priorities": p["decision_priorities"],
        },
        "brand": meta.get("brand", ""),
        "category": meta.get("category", ""),
        "goal": meta.get("goal", ""),
        "budget": meta.get("budget", ""),
        "audience": meta.get("audience", ""),
        "sections": ordered,
        "view_kind": "summary" if summary else "complete",
        "omitted_sections": remaining if summary else [],
        "source_plan_ref": {"kind": "inline_snapshot", "field": "source_plan"},
        "source_plan": copy.deepcopy(plan),
        "category_playbook": play,
        "touchpoints": touch,
        "risk": risk,
        "kpi_lens": p["kpi"],
        "evidence_demands": p["evidence_demands"],
        "call_to_action": p["call_to_action"],
        "international_benchmark": p["international_benchmark"],
    }


def adapt_idea(idea, perspective="agency"):
    """把同一个创意 idea（idea_generator.generate_ideas 输出元素）转成三方话术。

    创意本体（big_idea/mechanism）不变，只换"对谁说/怎么讲/讲什么"的呈现。
    """
    p = perspective_brief(perspective)
    bi = idea.get("big_idea", "")
    mech = idea.get("mechanism", "")
    why = idea.get("why", "")
    budget = idea.get("budget", {}).get("name", "未定")
    touch = idea.get("touchpoints", [])
    if perspective == "client":
        pov = {
            "audience_pitch": "给品牌方/老板：这个创意如何带来生意结果（声量→互动→转化→资产），预算「%s」如何被花在刀刃上" % budget,
            "frame": "一句话讲清价值：%s（机制：%s）——它为什么值得你投钱、投多少、多久看到回报" % (bi, mech),
            "risk_note": "决策依据：需要真实数据回填与效果验证，不做无数据承诺",
        }
    elif perspective == "agency":
        pov = {
            "audience_pitch": "给比稿/客户：策略-创意-执行如何闭环，为什么这个 idea 赢在洞察与原创而非拼贴",
            "frame": "创意概念：%s（机制：%s）。逻辑：%s" % (bi, mech, why),
            "risk_note": "比稿要点：展示洞察来源、创意独特性、执行颗粒度与测算逻辑",
        }
    else:  # vendor
        pov = {
            "audience_pitch": "给执行方/平台：这个 idea 落地要什么资源、怎么排期、怎么结算、怎么验收",
            "frame": "执行需求：围绕「%s」需要 内容/媒介/达人/制作 的资源配置与 SOP（触点：%s）" % (bi, "、".join(touch)),
            "risk_note": "合规与结算：平台规则、品牌安全、结算口径与验收标准需提前对齐",
        }
    return {
        "role": p["role"],
        "role_name": p["role_name"],
        "big_idea": bi,
        "mechanism": mech,
        "budget": budget,
        "perspective": pov,
        "kpi_lens": p["kpi"],
        "call_to_action": p["call_to_action"],
    }


def main():
    ap = argparse.ArgumentParser(description="三方视角分级适配器（甲方/乙方/丙方）")
    ap.add_argument("--perspective", default="client", choices=list(PERSPECTIVES.keys()),
                    help="视角: client=甲方品牌方 / agency=乙方代理商 / vendor=丙方平台媒介")
    ap.add_argument("--brand", default="示例品牌")
    ap.add_argument("--category", default="通用")
    ap.add_argument("--goal", default="品牌声量提升")
    ap.add_argument("--budget", default="")
    ap.add_argument("--audience", default="目标人群")
    ap.add_argument("--summary", action="store_true", help="显式摘要视图，保留完整原稿引用")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    from scripts.campaign_plan import generate_plan
    plan = generate_plan(a.brand, a.category, a.goal, a.budget, a.audience)
    view = adapt_plan(plan, a.perspective, summary=a.summary)
    if a.json:
        print(json.dumps(view, ensure_ascii=False, indent=2))
    else:
        p = view
        print("=" * 56)
        print("【%s · %s】视角视图" % (p["role"], p["role_name"]))
        print("定位：%s" % p["perspective_lens"]["positioning"])
        print("核心关切：%s" % p["perspective_lens"]["core_concern"])
        print("沟通语言：%s" % p["perspective_lens"]["language"])
        print("=" * 56)
        if p["view_kind"] == "summary":
            print("[摘要视图] 未展示章节：%s；完整原稿见下方。" % "、".join(p["omitted_sections"]))
        for k, v in p["sections"].items():
            print("\n【%s】\n%s" % (k, v))
        if p["view_kind"] == "summary":
            print("\n[完整原稿]")
            for k, v in p["source_plan"]["sections"].items():
                print("\n【%s】\n%s" % (k, v))
        print("\n[KPI 视角] %s" % p["kpi_lens"])
        print("[下一步] %s" % p["call_to_action"])


if __name__ == "__main__":
    main()
