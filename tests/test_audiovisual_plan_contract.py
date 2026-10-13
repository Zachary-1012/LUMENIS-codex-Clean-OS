"""Pure contract checks for retained audiovisual authoring intent."""
import builtins
import hashlib
import importlib
import json
from dataclasses import FrozenInstanceError

import pytest

from lumenis.shared.content_creation.contracts import (
    AudiovisualPlan,
    ContentContractError,
    Shot,
    ShotPlan,
)

_UNKNOWN = {"kind": "UNKNOWN", "locator": None}


def _provenance(locator="test:explicit"):
    return {"kind": "USER_EXPLICIT", "locator": locator}


def _output(
    output_id="out-1", *, medium="video", purpose="Retain the authored brief",
    canvas_ratio=None, duration=None, sound=None, languages=None, constraints=None, plan=None,
):
    duration = duration or {"min_seconds": None, "max_seconds": None, "tolerance_seconds": None}
    sound = sound or {"original": "unknown", "voice": "unknown", "music": "unknown"}
    languages = list(languages or ())
    constraints = constraints or {}
    provenance = {
        "purpose": _provenance(f"{output_id}:purpose"),
        "canvas_ratio": _UNKNOWN if canvas_ratio is None else _provenance(f"{output_id}:canvas"),
        "duration": _UNKNOWN if all(value is None for value in duration.values()) else _provenance(f"{output_id}:duration"),
        "languages": _UNKNOWN if not languages else _provenance(f"{output_id}:languages"),
        "constraints": _provenance(f"{output_id}:constraints"),
        "original": _UNKNOWN if sound["original"] == "unknown" else _provenance(f"{output_id}:original"),
        "voice": _UNKNOWN if sound["voice"] == "unknown" else _provenance(f"{output_id}:voice"),
        "music": _UNKNOWN if sound["music"] == "unknown" else _provenance(f"{output_id}:music"),
    }
    return {
        "output_id": output_id,
        "medium": medium,
        "purpose": purpose,
        "canvas_ratio": canvas_ratio,
        "duration": duration,
        "sound": sound,
        "languages": languages,
        "constraints": constraints,
        "provenance": provenance,
        "plan": plan,
    }


def _document(*, brief_text="Raw user brief.", outputs=None, rules=None):
    return {
        "schema": "lumenis.audiovisual-plan/v1",
        "brief_text": brief_text,
        "method_source": {
            "reference": "isolated-contract-test",
            "sha256": hashlib.sha256(b"declarative test method reference").hexdigest(),
        },
        "outputs": outputs if outputs is not None else [_output()],
        "rule_assessments": rules if rules is not None else [],
    }


def _shot_plan(*shots, brief_ref="", evidence_refs=()):
    return ShotPlan(tuple(shots), brief_ref=brief_ref, evidence_refs=tuple(evidence_refs)).to_dict()


_RETAINED_V2_CASES = (
    {
        "case_id": "dot-av-v2:brief-01",
        "title": "用例一 多语访谈节选",
        "source_text": """### 用例一 多语访谈节选

**输入：** 40分钟中英混合访谈、两机位、独立录音；要8分钟16:9研究访谈节选，保留被访者限定条件，无音乐，中文字幕；素材和用途已授权。

**合格规划：** 先核同步和转写语言能力，建立论点与限定条件的证据关系；根据内容选择段落，以完整意思和反应为单位裁切。优先处理双机位连续、语音气口、字幕准确性，不强加产品式CTA或每三秒换镜。

**最少问题：** 若“重点主题”未给且40分钟涉及多个主题，问希望聚焦哪项或先交候选提纲；若专业名词无法核验，集中列出少量待确认项。

**负例：** 为缩短到8分钟删掉“仅适用于某条件”，用无关反应镜头暗示对方赞同；以无音乐为由取消对白实听。

**通过测试：** 选段都能回链原访谈；限定条件保留；无音乐轨；字幕语言与数字核验；完整听觉与事实审查通过。缺听觉能力时只能是可执行技术计划加待审项，不能终审PASS。

""",
    },
    {
        "case_id": "dot-av-v2:brief-02",
        "title": "用例二 完全静音的竖屏工艺演示",
        "source_text": """### 用例二 完全静音的竖屏工艺演示

**输入：** 12段授权手工制作素材；35秒9:16；无旁白、无音乐、无环境声；需要看清三个关键操作，节奏平稳，预算只允许现有素材。

**合格规划：** 检查手部和工具在竖裁后是否保留；按动作因果挑选素材，允许简单步骤文字；声音策略明确为无音轨或静音交付，并据实际交付合同测试。不能为了“更抓人”主动加音乐、击打声或快速变速。

**最少问题：** 若缺少某一步结果，询问是否允许以明确文字说明缺失或改为只覆盖已有步骤；不得生成假手部动作当实拍。

**负例：** 中心裁切切掉工具；删掉关键中间动作；自动套旅行模板和音乐卡点。

**通过测试：** 三步可读，关键物不出框，长度/画幅符合要求，实际输出无声音；相关音乐听感可记NOT_APPLICABLE，但视觉动作完整性必须PASS。

""",
    },
    {
        "case_id": "dot-av-v2:brief-03",
        "title": "用例三 产品发布 多目标画幅",
        "source_text": """### 用例三 产品发布 多目标画幅

**输入：** 产品实拍、屏幕录制、品牌字体授权；75秒横屏主片和30秒竖屏短版；必须准确显示两项功能与限制；有旁白，可选已授权音乐；预算不允许补拍。

**合格规划：** 功能与证据镜头绑定，屏幕信息保护；横竖分别构图和取舍。30秒版从核心证明重新组织，不能仅将75秒变速至30秒。配乐可选但不必要，首先确保功能文字和旁白可理解。

**最少问题：** 若两项功能都无法在30秒完整证明，问优先功能或是否允许短版只给一个明确信息；不擅自省掉重要限制。

**负例：** 以参考Orange的反转为由，先展示不存在的产品能力再补小字；自动添加未授权效果素材。

**通过测试：** 每个功能声明有来源；屏幕读得清；短版不误导；各画幅独立验收；未授权曲目不能进入候选执行节点。

""",
    },
    {
        "case_id": "dot-av-v2:brief-04",
        "title": "用例四 长教程保真剪辑",
        "source_text": """### 用例四 长教程保真剪辑

**输入：** 12分钟屏幕操作教程，含语音、鼠标轨迹和3次演示错误；目标12分钟以内，16:9，保留必要失败示范与恢复过程；不需要音乐和片尾关注提醒。

**合格规划：** 先区分真实教学必要的失败与录制等待；操作、讲解、鼠标和字幕同步；可压缩无信息加载等待并显式标示时间省略。不能把所有错误删除，导致教程无法解释恢复步骤。

**最少问题：** 若要删除的错误正是教学重点，询问是否保留该教学目标；若片长上限无法与全部必要操作同时满足，提出删减章节选择。

**负例：** 为“短视频节奏”每两秒切镜；裁掉菜单；伪称操作即时完成；添加未要求CTA。

**通过测试：** 观众能依步骤复现，错误/恢复因果完整；界面可读；被省略时间标明；导出后鼠标与语音同步。

""",
    },
    {
        "case_id": "dot-av-v2:brief-05",
        "title": "用例五 完整音乐表演",
        "source_text": """### 用例五 完整音乐表演

**输入：** 一段90秒已授权原创表演，三机位，同期多轨混音；保留整段音乐，不加旁白和特效；1:1输出；对舞台空间和演奏动作有要求。

**合格规划：** 先确认全段音频连续和各机位同步，再按演奏动作、人物互动及空间切换选镜。允许长驻留，不要求每拍切换；首尾完整音乐是硬约束，画面裁切不能截掉关键演奏动作。

**最少问题：** 若1:1无法同时容纳关键演奏者，问优先主体或是否允许保留黑边/重新排版；不得自行换成16:9。

**负例：** 为追求高潮删音乐小节；用RMS峰值自动定义所有切点；剪到另一时间的演奏动作却未检查同步。

**通过测试：** 90秒表演连续，音频无不当重拼，关键动作同步，声道和峰值符合交付，实际听觉验收必需。

""",
    },
    {
        "case_id": "dot-av-v2:brief-06",
        "title": "用例六 人物纪念与纪录",
        "source_text": """### 用例六 人物纪念与纪录

**输入：** 旧手机家庭录像、照片、少量语音；两分钟私下纪念片；允许不同画质；无煽情文案，不推断逝者心理；音乐可不用。

**合格规划：** 根据真实人物关系与可验证时间组织，不把低清素材自动排除；优先完整的人际动作、语音意思与照片背景。可以保留沉默和没有戏剧转折的生活段落。

**最少问题：** 人物身份或事件时间不清时，只问会影响叙事的少数事实；用途若从私下改公开，重新确认相关授权。

**负例：** 套用CALM的反转结构把私人经历当惊讶；生成“他当时一定很幸福”的旁白；为了统一画质改坏面部。

**通过测试：** 没有虚构身份、关系、心理与事件顺序；私下用途得到遵守；语音/画面完整复核；未公开授权不能上传分享。

""",
    },
    {
        "case_id": "dot-av-v2:brief-07",
        "title": "用例七 活动回顾的快速交付",
        "source_text": """### 用例七 活动回顾的快速交付

**输入：** 当天活动多机位素材、嘈杂现场声、官方议程；60–90秒区间可接受；横屏和竖屏；两小时内交付初版；只用现有素材与已授权音乐。

**合格规划：** 先快速探测与代理，按议程确认事实与关键人物，再规划覆盖与预览。预算紧时降低预览质量、重用缓存、先交需反馈的版本；最终母版仍按合同验收。可因信息需要保留真实短话语，也可在经授权的意义不变情况下选择无对白方案。

**最少问题：** 询问必须出现的关键人/环节，及是否允许某个缺失环节不进片；不要要求用户决定每一刀。

**负例：** 随机挑欢呼镜头暗示对应另一位讲话者；未检听就覆盖所有现场声；把低清代理当最终输出。

**通过测试：** 人物/环节对应真实；多画幅分别可读；时间范围合格；初版明确未决项；最终输出与批准版本一致。

""",
    },
    {
        "case_id": "dot-av-v2:brief-08",
        "title": "用例八 长时观察与环境记录",
        "source_text": """### 用例八 长时观察与环境记录

**输入：** 20分钟稳定机位自然环境记录，原始环境声；只修头尾、轻微色彩偏差和明显技术瑕疵；保留20分钟连续时间体验，不要音乐、标题或叙事重组。

**合格规划：** 以保留为主，只执行授权范围内的修整；针对实际瑕疵提供可撤销处理，并检查是否损害空间声和自然变化。用户时长与头尾修剪发生矛盾时，说明净时长变化。

**最少问题：** 只有“必须恰好20分钟”与“剪去故障头尾”不可兼得时，询问优先项；不为了填满增加假静帧或循环片段。

**负例：** 加三秒钩子、音乐高潮、CTA；自动加速无明显动作部分；循环环境声却声称连续实录。

**通过测试：** 时间连续性和保真要求满足；无新增音乐/文字；处理没有可听/可见伪影；必要完整观看与监听未完成时不最终通过。

""",
    },
)


def test_snapshots_are_canonical_immutable_and_brief_specific():
    output = _output(languages=["中文", "English"], constraints={"raw_constraint": "retain the full condition"})
    original = _document(brief_text="Original unabridged brief.", outputs=[output])
    plan = AudiovisualPlan.from_dict(original)
    snapshot = plan.snapshot()
    canonical = plan.document

    assert canonical == json.dumps(json.loads(canonical), ensure_ascii=False, allow_nan=False,
                                   sort_keys=True, separators=(",", ":"))
    assert snapshot["input_sha256"] == hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    assert snapshot["brief_sha256"] == hashlib.sha256(b"Original unabridged brief.").hexdigest()
    assert plan.snapshot() == snapshot
    assert plan.to_dict()["outputs"][0]["languages"] == ["中文", "English"]

    returned = plan.to_dict()
    returned["brief_text"] = "Mutated caller copy."
    returned["outputs"][0]["constraints"]["raw_constraint"] = "Mutated caller copy."
    snapshot["input"]["brief_text"] = "Mutated snapshot copy."
    snapshot["outputs"][0]["constraints"] = "Mutated snapshot copy."
    assert plan.document == canonical
    assert plan.snapshot()["input"]["brief_text"] == "Original unabridged brief."
    assert plan.snapshot()["outputs"][0]["constraints"] == "NOT_EVALUATED_ON_MEDIA"
    with pytest.raises(FrozenInstanceError):
        plan.document = "replacement"

    changed_brief = AudiovisualPlan.from_dict({**original, "brief_text": "Changed brief."})
    assert changed_brief.snapshot()["brief_sha256"] != snapshot["brief_sha256"]
    assert changed_brief.snapshot()["input_sha256"] != snapshot["input_sha256"]
    assert plan.snapshot()["brief_sha256"] == hashlib.sha256(b"Original unabridged brief.").hexdigest()


def test_eight_v2_case_intents_keep_raw_text_unknowns_and_distinct_purposes():
    assert len(_RETAINED_V2_CASES) == 8
    assert len({case["case_id"] for case in _RETAINED_V2_CASES}) == 8
    assert len({case["source_text"] for case in _RETAINED_V2_CASES}) == 8

    for case in _RETAINED_V2_CASES:
        language = ["Chinese"] if case["case_id"] == "dot-av-v2:brief-01" else []
        output = _output(
            output_id=case["case_id"].replace(":", "-"),
            purpose=case["title"],
            languages=language,
            constraints={"retained_case_id": case["case_id"], "source_text": case["source_text"]},
        )
        plan = AudiovisualPlan.from_dict(_document(brief_text=case["source_text"], outputs=[output]))
        snapshot = plan.snapshot()
        reopened = plan.to_dict()
        retained = reopened["outputs"][0]

        assert reopened["brief_text"] == case["source_text"]
        assert retained["constraints"]["source_text"] == case["source_text"]
        assert retained["purpose"] == case["title"]
        assert retained["languages"] == language
        assert retained["sound"] == {"original": "unknown", "voice": "unknown", "music": "unknown"}
        assert retained["plan"] is None
        assert "hook" not in retained and "cta" not in retained
        assert snapshot["outputs"][0]["status"] == "NEEDS_MATERIAL"
        assert snapshot["execution"] == "NOT_EXECUTED"


def _predicate(name, value, kind=None):
    if kind is None:
        kind = "UNKNOWN" if value is None else "USER_EXPLICIT"
    provenance = _UNKNOWN if kind == "UNKNOWN" else {"kind": kind, "locator": f"test:{name}"}
    return {"predicate": name, "value": value, "provenance": provenance}


def _rule(ref, *, conditions, exclusions):
    return {
        "rule_ref": ref,
        "output_ids": ["out-1"],
        "required_conditions": conditions,
        "exclusions": exclusions,
    }


def test_unknown_and_planner_proposal_predicates_remain_unactivated():
    rules = [
        _rule("unknown-condition", conditions=[_predicate("source-sync", None)], exclusions=[]),
        _rule("proposal-condition", conditions=[_predicate("music-rights", True, "PLANNER_PROPOSAL")], exclusions=[]),
        _rule("proposal-false-condition", conditions=[_predicate("source-sync", False, "PLANNER_PROPOSAL")], exclusions=[]),
        _rule("proposal-exclusion", conditions=[_predicate("source-sync", True)],
              exclusions=[_predicate("rights-revoked", True, "PLANNER_PROPOSAL")]),
    ]
    snapshot = AudiovisualPlan.from_dict(_document(rules=rules)).snapshot()

    assert [item["decision"] for item in snapshot["rule_decisions"]] == [
        "NEEDS_REVIEW", "NEEDS_REVIEW", "NEEDS_REVIEW", "NEEDS_REVIEW",
    ]
    assert all(item["decision"] != "SELECTABLE_CANDIDATE" for item in snapshot["rule_decisions"])
    assert snapshot["execution"] == "NOT_EXECUTED"
    assert snapshot["predicate_evidence"] == "DECLARED_NOT_REVALIDATED"


def test_true_exclusion_precedes_false_condition_and_false_condition_precedes_unknown():
    unknown = _predicate("transcript-check", None)
    rules = [
        _rule(
            "excluded-first",
            conditions=[_predicate("available-source", False), unknown],
            exclusions=[_predicate("rights-revoked", True)],
        ),
        _rule(
            "false-condition-first",
            conditions=[_predicate("available-source", False), unknown],
            exclusions=[_predicate("optional-requirement", None)],
        ),
        _rule(
            "confirmed-false-condition-over-proposed-exclusion",
            conditions=[_predicate("available-source", False)],
            exclusions=[_predicate("rights-revoked", True, "PLANNER_PROPOSAL")],
        ),
        _rule(
            "confirmed-exclusion-over-proposed-condition",
            conditions=[_predicate("available-source", False, "PLANNER_PROPOSAL")],
            exclusions=[_predicate("rights-revoked", True)],
        ),
    ]
    snapshot = AudiovisualPlan.from_dict(_document(rules=rules)).snapshot()

    assert [item["decision"] for item in snapshot["rule_decisions"]] == [
        "EXCLUDED", "NOT_APPLICABLE", "NOT_APPLICABLE", "EXCLUDED",
    ]
    assert snapshot["execution"] == "NOT_EXECUTED"


@pytest.mark.parametrize(
    ("sound_field", "shot_field", "shot_value"),
    [
        ("voice", "voice_over", "Proposed voice-over"),
        ("voice", "audio_role", "voice"),
        ("voice", "audio_role", "voiceover"),
        ("original", "original_sound", "Retained source sound"),
        ("original", "audio_role", "original"),
        ("music", "audio_role", "music"),
    ],
)
def test_forbidden_sound_policy_rejects_conflicting_shot_fields(sound_field, shot_field, shot_value):
    shot = Shot(shot_purpose="Contract-only shot", duration_sec=4, **{shot_field: shot_value})
    output = _output(
        sound={"original": "unknown", "voice": "unknown", "music": "unknown"},
        plan=_shot_plan(shot),
    )
    output["sound"][sound_field] = "forbidden"
    output["provenance"][sound_field] = _provenance(f"out-1:{sound_field}")

    with pytest.raises(ContentContractError, match="AV_PLAN_SOUND_CONFLICT"):
        AudiovisualPlan.from_dict(_document(outputs=[output]))


def test_landscape_and_portrait_outputs_keep_independent_plans_and_durations():
    landscape = _output(
        output_id="landscape-main",
        purpose="Main landscape release",
        canvas_ratio="16:9",
        duration={"min_seconds": 75, "max_seconds": 75, "tolerance_seconds": 0},
        constraints={"source_text": _RETAINED_V2_CASES[2]["source_text"], "delivery": "main"},
        plan=_shot_plan(Shot(shot_purpose="Feature proof", duration_sec=75)),
    )
    portrait = _output(
        output_id="portrait-short",
        purpose="Independently composed portrait short",
        canvas_ratio="9:16",
        duration={"min_seconds": 30, "max_seconds": 30, "tolerance_seconds": 0},
        constraints={"source_text": _RETAINED_V2_CASES[2]["source_text"], "delivery": "short"},
        plan=_shot_plan(Shot(shot_purpose="Short proof", duration_sec=30)),
    )
    snapshot = AudiovisualPlan.from_dict(_document(
        brief_text=_RETAINED_V2_CASES[2]["source_text"], outputs=[landscape, portrait],
    )).snapshot()

    assert [item["output_id"] for item in snapshot["outputs"]] == ["landscape-main", "portrait-short"]
    assert [item["canvas_ratio"] for item in snapshot["input"]["outputs"]] == ["16:9", "9:16"]
    assert [item["estimated_duration_seconds"] for item in snapshot["outputs"]] == [75.0, 30.0]
    assert [item["constraints"]["delivery"] for item in snapshot["input"]["outputs"]] == ["main", "short"]


def test_full_performance_requires_exact_90_seconds_when_tolerance_is_zero():
    source_text = _RETAINED_V2_CASES[4]["source_text"]

    def full_performance(seconds):
        return _output(
            output_id="complete-performance",
            purpose="Preserve the full performance",
            canvas_ratio="1:1",
            duration={"min_seconds": 90, "max_seconds": 90, "tolerance_seconds": 0},
            sound={"original": "required", "voice": "forbidden", "music": "forbidden"},
            constraints={"source_text": source_text, "full_performance": True},
            plan=_shot_plan(Shot(
                shot_purpose="One continuous performance", original_sound="Original performance mix",
                duration_sec=seconds,
            )),
        )

    accepted = AudiovisualPlan.from_dict(_document(
        brief_text=source_text, outputs=[full_performance(90)],
    )).snapshot()
    assert accepted["outputs"][0]["estimated_duration_seconds"] == 90.0
    with pytest.raises(ContentContractError, match="AV_PLAN_PLANNED_DURATION_CONFLICT"):
        AudiovisualPlan.from_dict(_document(brief_text=source_text, outputs=[full_performance(88)]))


def test_malformed_nonfinite_duplicate_and_unknown_documents_are_rejected():
    valid = _document()
    with pytest.raises(ContentContractError, match="AV_PLAN_INPUT_INVALID"):
        AudiovisualPlan("{")

    duplicate_key = (
        '{"schema":"lumenis.audiovisual-plan/v1",'
        '"schema":"lumenis.audiovisual-plan/v1"}'
    )
    with pytest.raises(ContentContractError, match="AV_PLAN_DUPLICATE_KEY"):
        AudiovisualPlan(duplicate_key)

    nonfinite = json.dumps(valid, ensure_ascii=False).replace(
        '"tolerance_seconds": null', '"tolerance_seconds": NaN', 1,
    )
    assert nonfinite != json.dumps(valid, ensure_ascii=False)
    with pytest.raises(ContentContractError, match="AV_PLAN_NONFINITE_VALUE"):
        AudiovisualPlan(nonfinite)

    unknown_field = {**valid, "unrecognized": True}
    with pytest.raises(ContentContractError, match="AV_PLAN_INPUT_INVALID"):
        AudiovisualPlan.from_dict(unknown_field)


def test_malformed_shot_text_field_is_rejected():
    plan = _shot_plan(Shot(shot_purpose="Preserve the declared shot", duration_sec=4))
    plan["shots"][0]["visual_motif"] = ["not", "text"]

    with pytest.raises(ContentContractError):
        AudiovisualPlan.from_dict(_document(outputs=[_output(plan=plan)]))


def test_legacy_shot_plan_shape_roundtrips_without_loading_podcast(monkeypatch):
    legacy = {
        "brief_ref": "",
        "evidence_refs": [],
        "shots": [{
            "narrative_beat": "Preserve the original order",
            "emotional_beat": "",
            "shot_purpose": "Show the complete step",
            "visual_motif": "",
            "shot_size": "",
            "camera_motion": "static",
            "subject_action": "The documented action",
            "continuity": "",
            "audio_role": "",
            "original_sound": "",
            "voice_over": "",
            "text_subtitles": "",
            "transition_type": "cut",
            "transition_reason": "",
            "duration_sec": 5,
            "hold_sec": None,
            "pacing": "",
            "evidence_refs": [],
        }],
    }
    output = _output(plan=legacy)
    real_import = builtins.__import__

    def reject_podcast_import(name, *args, **kwargs):
        if name == "podcast.intelligence.episode_runtime":
            raise AssertionError("video ShotPlan validation imported PodcastPlan")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", reject_podcast_import)
    plan = AudiovisualPlan.from_dict(_document(outputs=[output]))
    assert plan.to_dict()["outputs"][0]["plan"] == legacy
    assert set(legacy) == {"brief_ref", "evidence_refs", "shots"}


def test_podcast_plan_is_imported_locally_for_podcast_duration(monkeypatch):
    from podcast.intelligence.episode_runtime import PodcastPlan, PodcastSegment

    podcast = PodcastPlan(
        "Contract-only episode",
        "No media or source permission is asserted.",
        "en",
        (PodcastSegment(
            segment_id="segment-1",
            media_asset_id="UNRESOLVED_MEDIA",
            source_in=0,
            source_out=3,
            original_text="Declared source text",
            corrected_text="Declared source text",
            speaker="Guest",
            chapter_title="Opening",
            evidence_refs=(),
        ),),
    )
    output = _output(
        output_id="podcast-output",
        medium="podcast",
        purpose="Keep the declared episode plan",
        duration={"min_seconds": 3, "max_seconds": 3, "tolerance_seconds": 0},
        sound={"original": "required", "voice": "forbidden", "music": "forbidden"},
        constraints={"source_text": "Pure contract fixture; no media is opened."},
        plan=podcast.to_dict(),
    )
    contracts_module = importlib.import_module("lumenis.shared.content_creation.contracts")
    assert "PodcastPlan" not in vars(contracts_module)
    real_import = builtins.__import__
    local_imports = []

    def record_podcast_plan_import(name, *args, **kwargs):
        fromlist = args[2] if len(args) > 2 else kwargs.get("fromlist", ())
        if name == "podcast.intelligence.episode_runtime" and "PodcastPlan" in fromlist:
            local_imports.append((name, tuple(fromlist)))
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", record_podcast_plan_import)
    plan = AudiovisualPlan.from_dict(_document(outputs=[output]))
    assert local_imports == [("podcast.intelligence.episode_runtime", ("PodcastPlan",))]
    assert plan.to_dict()["outputs"][0]["plan"] == podcast.to_dict()
    assert plan.snapshot()["outputs"][0]["estimated_duration_seconds"] == 3.0
