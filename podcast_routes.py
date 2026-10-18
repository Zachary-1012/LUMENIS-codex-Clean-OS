# -*- coding: utf-8 -*-
"""
播客情报模块 · Flask 路由层（Podcast Routes）
对齐 podcast/IMPLEMENTATION_PLAN_V1：可插拔，不改变 ZBC 品牌舆情核心链路。
- 实体图 CRUD 走 podcast_store
- 选题打分 / 故事节点 / 运行时校验 / 内容产出 / 破圈分类走 podcast/intelligence 确定性算法
- AI 行为从 Shadow 开始，每次运行记录 model/input_hash/runtime/status，可追溯
- 缺失指标留 null，不虚构平台数据、不虚构播放/转化
"""
import os
import sys
import time
import hashlib
import math
import traceback
from flask import Blueprint, request, jsonify

# podcast/intelligence 作为独立算法目录加入路径
_INTEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "podcast", "intelligence")
if _INTEL_DIR not in sys.path:
    sys.path.insert(0, _INTEL_DIR)

podcast_bp = Blueprint("podcast", __name__, url_prefix="/api/podcast")


def _ok(data=None, **kw):
    out = {"ok": True}
    if data is not None:
        out["data"] = data
    out.update(kw)
    return jsonify(out)


def _err(msg, code=400):
    return jsonify({"ok": False, "error": str(msg)}), code


def _store():
    import podcast_store
    return podcast_store


def _entity_scope_unavailable():
    # Legacy podcast_entities has no canonical domain/focus/actor columns.
    # Do not infer ownership from a header or silently expose all rows.
    return jsonify({
        "ok": False,
        "code": "PODCAST_ENTITY_SCOPE_UNAVAILABLE",
        "status": "blocked",
        "message": "Podcast entities need a scoped migration before use",
    }), 503


# ---------- 实体图 ----------
@podcast_bp.route("/overview", methods=["GET"])
def api_overview():
    return _entity_scope_unavailable()


@podcast_bp.route("/entities", methods=["GET"])
def api_entities():
    return _entity_scope_unavailable()


@podcast_bp.route("/entity", methods=["GET"])
def api_get_entity():
    return _entity_scope_unavailable()


@podcast_bp.route("/entity", methods=["POST"])
def api_create_entity():
    return _entity_scope_unavailable()


# ---------- 确定性智能算法（不依赖外部模型，结果可复现） ----------
@podcast_bp.route("/topic-score", methods=["POST"])
def api_topic_score():
    """选题十维打分（信号均为 0..1 归一化；前端 0..10 滑块自行 /10）。

    确定性权重：正向 0.90（demand .16/timeliness .12/novelty .10/human .14/
    guest .12/evidence .10/yield .10/distribution .06），risk+cost 惩罚 0.10。
    AI 只可建议输入信号，最终分必须由本确定性函数计算，规则是真值。
    """
    try:
        import topic_scoring as ts
        b = request.get_json(silent=True)
        if not isinstance(b, dict):
            raise ValueError("INVALID_TOPIC_SIGNALS")
        sig_in = b.get("signals", b)
        fields_def = ts.TopicSignals.__dataclass_fields__
        if not isinstance(sig_in, dict) or set(sig_in) - set(fields_def):
            raise ValueError("INVALID_TOPIC_SIGNALS")
        sig = ts.TopicSignals(**sig_in)
        missing = [name for name in fields_def if getattr(sig, name) is None]
        score = ts.score_topic(sig)
        stage = ts.classify_topic(score, sig.timeliness)
        return _ok(
            state="scored" if score is not None else "input_required",
            score=score, stage=stage, missing_signals=missing,
            signals={k: round(float(getattr(sig, k)), 3) if getattr(sig, k) is not None else None
                     for k in fields_def},
            weights=getattr(ts, "WEIGHTS", None),
        )
    except (ValueError, TypeError):
        return jsonify({"ok": False, "state": "invalid_input", "score": None, "stage": None,
                        "code": "PODCAST_TOPIC_SIGNALS_INVALID"}), 400
    except Exception:
        return jsonify({"ok": False, "state": "unavailable", "score": None, "stage": None,
                        "code": "PODCAST_TOPIC_SCORING_UNAVAILABLE"}), 503


@podcast_bp.route("/story-nodes", methods=["POST"])
def api_story_nodes():
    """从分段提取故事节点：输入 segments[{segment_id,start_ms,end_ms,text,node_type?}]"""
    try:
        import story_nodes as sn
        b = request.get_json(force=True, silent=True) or {}
        segs = b.get("segments", [])
        nodes = []
        for i, sg in enumerate(segs):
            ntype = sg.get("node_type", "story")
            seg_ids = sg.get("segment_ids") or [sg.get("segment_id", f"s{i}")]
            node = sn.make_node(
                sg.get("node_id", f"n{i}"), ntype,
                int(sg.get("start_ms", 0)), int(sg.get("end_ms", 0)), seg_ids,
                evidence_ids=sg.get("evidence_ids", []),
                confidence=float(sg.get("confidence", 0.0)),
                rationale=sg.get("rationale", ""),
            )
            nodes.append(_dataclass_to_dict(node))
        return _ok(nodes=nodes, count=len(nodes))
    except Exception as e:
        return _err(f"故事节点提取失败: {e}", 500)


@podcast_bp.route("/runtime/validate", methods=["POST"])
def api_runtime_validate():
    """运行时分段校验：时间轴必须单调递增、非负、kind 合法；非法直接报错。"""
    try:
        import episode_runtime as er
        b = request.get_json(force=True, silent=True) or {}
        raw = b.get("segments", [])
        segs = []
        for sg in raw:
            kind = sg.get("kind", "story")
            kind_enum = er.SegmentKind(kind) if not isinstance(kind, er.SegmentKind) else kind
            segs.append(er.RuntimeSegment(
                segment_id=sg["segment_id"], start_ms=int(sg["start_ms"]), end_ms=int(sg["end_ms"]),
                kind=kind_enum, speaker_ids=sg.get("speaker_ids", []), evidence_ids=sg.get("evidence_ids", []),
            ))
        er.validate_segments(segs)  # 非法抛 ValueError
        total_ms = sum(s.end_ms - s.start_ms for s in segs)
        return _ok(valid=True, segment_count=len(segs), total_runtime_seconds=round(total_ms / 1000, 2))
    except ValueError as ve:
        return jsonify({"ok": False, "valid": False, "reason": str(ve), "code": "PODCAST_SEGMENT_INVALID"}), 400
    except Exception as e:
        return _err(f"运行时校验失败: {e}", 500)


@podcast_bp.route("/breakout", methods=["POST"])
def api_breakout():
    """破圈分类：current vs baseline，返回 normal/breakout/viral"""
    try:
        from podcast.intelligence import breakout as bo
        b=request.get_json(silent=True)
        if not isinstance(b,dict) or set(b)-{"current","baseline","breakout_ratio","viral_ratio"}:
            raise ValueError("PODCAST_BREAKOUT_INPUT_INVALID")
        current,baseline=b.get("current"),b.get("baseline")
        state=bo.classify_breakout(current,baseline,breakout_ratio=b.get("breakout_ratio",1.8),viral_ratio=b.get("viral_ratio",3.0))
        missing=[name for name in ("current","baseline") if b.get(name) is None]
        ratio=current/baseline if current is not None and baseline else None
        ratio_finite=ratio is None or math.isfinite(ratio)
        return _ok(state=state.value,current=current,baseline=baseline,
                   ratio=ratio if ratio_finite else None,
                   missing_inputs=missing,reason="missing_observations" if missing else ("zero_baseline_ratio_undefined" if baseline==0 else ("ratio_out_of_numeric_range" if not ratio_finite else None)),
                   provenance="caller_supplied_observations_not_independently_verified")
    except (ValueError,TypeError):
        return jsonify({"ok":False,"state":"invalid_input","code":"PODCAST_BREAKOUT_INPUT_INVALID"}),400
    except Exception:
        return jsonify({"ok":False,"state":"unavailable","code":"PODCAST_BREAKOUT_UNAVAILABLE"}),503



@podcast_bp.route("/content-yield", methods=["POST"])
def api_content_yield():
    """内容产出规划：输入一个内容信号，返回可衍生资产计划"""
    try:
        from podcast.intelligence import content_yield as cy
        b=request.get_json(silent=True)
        if not isinstance(b,dict) or set(b)-set(cy.YieldSignal.__dataclass_fields__):
            raise ValueError("PODCAST_YIELD_INPUT_INVALID")
        signal=cy.YieldSignal(**b)
        plan=cy.plan_yield(signal)
        return _ok(plan=_dataclass_to_dict(plan,deep=True),signals={k:getattr(signal,k) for k in signal.__dataclass_fields__},
                   provenance="caller_supplied_counts_not_independently_verified",assets_created=False)
    except (ValueError,TypeError):
        return jsonify({"ok":False,"state":"invalid_input","code":"PODCAST_YIELD_INPUT_INVALID"}),400
    except Exception:
        return jsonify({"ok":False,"state":"unavailable","code":"PODCAST_YIELD_UNAVAILABLE"}),503



def _dataclass_to_dict(obj, deep=False):
    if obj is None:
        return None
    if hasattr(obj, "__dataclass_fields__"):
        out = {}
        for k in obj.__dataclass_fields__:
            v = getattr(obj, k)
            if deep and hasattr(v, "__dataclass_fields__"):
                out[k] = _dataclass_to_dict(v, True)
            elif isinstance(v, (list, tuple)):
                out[k] = [_dataclass_to_dict(x, True) if hasattr(x, "__dataclass_fields__") else
                          (getattr(x, "value", x) if hasattr(x, "value") else x) for x in v]
            elif hasattr(v, "value"):
                out[k] = v.value
            else:
                out[k] = v
        return out
    if hasattr(obj, "value"):
        return obj.value
    return str(obj)


def register_podcast_api(app):
    """在 app.py 中调用以注册播客蓝图。"""
    app.register_blueprint(podcast_bp)
    print("[podcast_routes] Podcast API registered: /api/podcast/*")
