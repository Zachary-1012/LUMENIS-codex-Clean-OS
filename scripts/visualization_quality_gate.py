# -*- coding: utf-8 -*-
"""可视化质量门检查清单 · scripts/visualization_quality_gate.py。

依据：CONTRACT_IC035_044_048_20260904.md §三（IC-048 Cycle LL）。
目标：每图绑定待回答问题、零基线防误导、CVD-safe 色彩+多通道表达、
      role-based 信息架构、empty/error 状态同等设计。
原则：沉淀为**可调用检查函数 + 静态清单**，不引新框架、不改既有图表（增量）。
      GATE 结论用于新图上线前验收，不阻塞生产既有可视化。
"""
from __future__ import annotations

from typing import Any

# ---- 检查清单（每项：id / 检查项 / 说明 / 类型：必填|建议）----
QUALITY_CHECKS: list[dict] = [
    {"id": "VISQ-01", "item": "待回答问题绑定",
     "desc": "每张图必须绑定一个明确待回答的业务问题（如：负面占比趋势？），图无问题=不必要",
     "required": True},
    {"id": "VISQ-02", "item": "零基线防误导",
     "desc": "数值轴零基线不可省略/截断误导；若截断必须显式标注（如 ¥ 符号或断轴标记）",
     "required": True},
    {"id": "VISQ-03", "item": "CVD-safe 色彩",
     "desc": "红绿色盲友好：避免纯红/绿对比作为唯一信息通道（CVD-safe 色板）",
     "required": True},
    {"id": "VISQ-04", "item": "多通道表达",
     "desc": "颜色外同时用形状/文字/图例/线型等第二通道，禁止只靠颜色区分",
     "required": True},
    {"id": "VISQ-05", "item": "role-based 信息架构",
     "desc": "信息层级按角色/职责组织：决策者看结论，分析师看细节，运营看行动",
     "required": True},
    {"id": "VISQ-06", "item": "empty/error 状态同等设计",
     "desc": "空数据/加载失败必须有与正常态同等设计的空态与错误态（不空白）",
     "required": True},
    {"id": "VISQ-07", "item": "Canonical 消费",
     "desc": "数值图表必须消费 Canonical Dataset / Metric（VISUALIZATION_REGISTRY 规则），不页面内嵌公式",
     "required": True},
    {"id": "VISQ-08", "item": "数据来源标注",
     "desc": "图表标注数据口径/来源/时间范围；估算或示例数据显式声明",
     "required": True},
    {"id": "VISQ-09", "item": "移动端可读",
     "desc": "窄屏可读、可点、无重叠裁切；正文≥14px，轴标签≥12px",
     "required": False},
    {"id": "VISQ-10", "item": "动效克制",
     "desc": "动效只用于状态/因果/连续性，禁止无意义动画；可暂停可重置",
     "required": False},
]


def check(vis_id: str = "", question: str = "", has_zero_baseline: bool = True,
          uses_cvd_safe: bool = True, multi_channel: bool = True,
          role_arch: bool = True, has_empty_state: bool = True,
          canonical_source: str = "", data_source_note: str = "",
          mobile_ok: bool = True, motion_ok: bool = True) -> dict:
    """对一张图执行质量门检查。

    参数：传入该图是否满足各检查项。
    返回：结构化结果（pass/fail + 明细），供新图上线前验收记录。
    """
    checks = []
    for c in QUALITY_CHECKS:
        val = {
            "VISQ-01": bool(question),
            "VISQ-02": has_zero_baseline,
            "VISQ-03": uses_cvd_safe,
            "VISQ-04": multi_channel,
            "VISQ-05": role_arch,
            "VISQ-06": has_empty_state,
            "VISQ-07": bool(canonical_source),
            "VISQ-08": bool(data_source_note),
            "VISQ-09": mobile_ok,
            "VISQ-10": motion_ok,
        }.get(c["id"], False)
        checks.append({
            "id": c["id"], "item": c["item"], "desc": c["desc"],
            "required": c["required"], "pass": val,
        })
    failed_required = [c for c in checks if c["required"] and not c["pass"]]
    failed_all = [c for c in checks if not c["pass"]]
    return {
        "vis_id": vis_id,
        "question": question,
        "result": "PASS" if not failed_required else "FAIL",
        "required_pass": len(checks) - len(failed_required),
        "required_total": len(checks),
        "failed_required": [c["id"] for c in failed_required],
        "failed_optional": [c["id"] for c in checks if not c["required"] and not c["pass"]],
        "checks": checks,
        "canonical_source": canonical_source,
        "data_source_note": data_source_note,
        "gate_note": "新图上线前验收清单；不影响既有生产可视化",
    }


def checklist_md() -> str:
    """输出质量门清单（Markdown），供文档沉淀。"""
    lines = ["## 可视化质量门检查清单（VISQ）", ""]
    lines.append("| ID | 检查项 | 说明 | 类型 |")
    lines.append("|---|---|---|---|")
    for c in QUALITY_CHECKS:
        lines.append(f"| {c['id']} | {c['item']} | {c['desc']} | {'必填' if c['required'] else '建议'} |")
    return "\n".join(lines)
