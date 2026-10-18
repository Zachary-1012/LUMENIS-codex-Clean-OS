"""Deterministic editorial contracts and real isolated SavedWork persistence.

The authored test guest records are fixtures, not independently verified guest
facts or real-user interview acceptance. No model, network or publication runs.
"""
from copy import deepcopy
import hashlib
import math

import pytest

from podcast.intelligence import editorial_planning as editorial
from tests.test_saved_document_workflow import workspace


TOPIC = "品牌经营 消费研究"
SHARED_SCOPE = {"scope_kind": "shared_workspace", "version": 1}
EXPECTED_GATES = ("unique_experience_public_value", "expression_and_willingness", "resonance")
EXPECTED_DIMENSIONS = (
    "IP定位", "受众承诺", "选题架构", "嘉宾架构", "嘉宾选题匹配", "问题架构", "追问深度", "故事密度",
    "冲突密度", "情绪密度", "洞察密度", "时长架构", "开场钩子", "章节架构", "金句切片产出", "分发包装",
    "跨平台转译", "受众反应", "增长与时长序列", "有证据的制作成本", "失败案例", "可复用性", "因果置信度", "证据质量",
)
EXPECTED_SOP = ["约人", "提纲", "拍摄间", "开场", "叫停", "追问", "结束", "剪辑"]


def guests():
    return [
        {"guest_id": "researcher", "name": "研究嘉宾", "domains": [TOPIC],
         "prior_programmes": [], "viewpoints": [], "source_refs": ["user-note:researcher-01"]},
        {"guest_id": "musician", "name": "音乐嘉宾", "domains": ["古典音乐"],
         "prior_programmes": ["弦乐访谈"], "viewpoints": ["节奏与旋律"], "source_refs": []},
        {"guest_id": "retailer", "name": "零售嘉宾", "domains": ["品牌 零售"],
         "prior_programmes": [], "viewpoints": [], "source_refs": ["user-note:retailer-01"]},
    ]


def gates():
    return {key: {"decision": "pass", "note": f"用户人工评议：{key}"} for key in EXPECTED_GATES}


def preview(**changes):
    values = {"topic": TOPIC, "guests": guests(), "selected_guest_id": "researcher", "gates": gates()}
    values.update(changes)
    return editorial.build_editorial_preview(**values)


def test_tfidf_chinese_bigram_contributions_explain_deterministic_ranking():
    result = editorial.rank_guests(TOPIC, guests())
    assert result["method"] == "character_bigram_word_tfidf_cosine_v1"
    assert result["semantic_embedding"] is result["automatic_selection"] is False
    assert [item["guest_id"] for item in result["candidates"]] == ["researcher", "retailer", "musician"]
    first, middle, last = result["candidates"]
    assert first["similarity"] == pytest.approx(1.0)
    assert 0 < middle["similarity"] < first["similarity"]
    assert last["similarity"] == 0 and last["matching_terms"] == []
    assert {item["term"] for item in first["matching_terms"]} == {"品牌", "牌经", "经营", "消费", "费研", "研究"}
    assert sum(item["contribution"] for item in first["matching_terms"]) == pytest.approx(1, abs=1e-7)
    assert all(item["contribution"] > 0 and math.isfinite(item["contribution"]) for item in first["matching_terms"])
    # Independently computed corpus: query + three profiles. 品牌 occurs in
    # three documents; the five other query bigrams occur in two each.
    brand_idf, other_idf, retail_idf = 1 + math.log(5 / 4), 1 + math.log(5 / 3), 1 + math.log(5 / 2)
    query_norm_squared = brand_idf ** 2 + 5 * other_idf ** 2
    contributions = {item["term"]: item["contribution"] for item in first["matching_terms"]}
    assert contributions["品牌"] == pytest.approx(brand_idf ** 2 / query_norm_squared, abs=1e-8)
    assert contributions["消费"] == pytest.approx(other_idf ** 2 / query_norm_squared, abs=1e-8)
    assert middle["similarity"] == pytest.approx(
        brand_idf ** 2 / math.sqrt(query_norm_squared * (brand_idf ** 2 + retail_idf ** 2)), abs=1e-8)
    assert "共享词项" in first["reason"] and "没有共享词项" in last["reason"]
    assert first["source_refs"] == ["user-note:researcher-01"]
    assert all(item["facts_status"] == "user_supplied_not_independently_verified" for item in result["candidates"])
    assert editorial.rank_guests(TOPIC, guests()) == result
    assert editorial.rank_guests(TOPIC, guests(), limit=2)["candidates"] == result["candidates"][:2]


def test_chinese_repetition_and_latin_case_use_counted_terms():
    assert editorial._terms("品牌品牌 Growth growth") == {"品牌": 2, "牌品": 1, "growth": 2}


def test_zero_match_ties_use_stable_ids_without_inventing_relevance():
    result = editorial.rank_guests("航天工程", list(reversed(guests())))
    assert [row["guest_id"] for row in result["candidates"]] == ["musician", "researcher", "retailer"]
    assert all(row["similarity"] == 0 and row["matching_terms"] == [] for row in result["candidates"])


def test_selection_required_never_chooses_highest_ranked_guest():
    result = editorial.build_editorial_preview(TOPIC, guests())
    assert result["state"] == "selection_required" and result["automatic_selection"] is False
    assert "selected_guest_id" not in result and "saved_work_draft" not in result
    assert "outline" not in result


def test_explicit_lower_ranked_choice_is_preserved():
    result = preview(selected_guest_id="musician")
    assert result["ranking"]["candidates"][0]["guest_id"] == "researcher"
    assert result["selected_guest_id"] == "musician"
    payload = result["saved_work_draft"]["payload"]
    assert payload["guest_selection"] == {"guest_id": "musician", "selection_method": "explicit_user_selection"}
    assert payload["interview_outline"]["guest_id"] == "musician"
    assert "嘉宾：音乐嘉宾" in result["saved_work_draft"]["markdown"]


@pytest.mark.parametrize("gate", EXPECTED_GATES)
@pytest.mark.parametrize("decision", ["unknown", "fail"])
def test_each_human_gate_blocks_outline_and_saved_draft(gate, decision):
    values = gates()
    values[gate] = {"decision": decision, "note": "待人工核实"}
    result = preview(gates=values)
    assert result["state"] == "manual_gate_blocked"
    assert result["blocked_gates"] == [gate]
    assert result["outline"] is None and "saved_work_draft" not in result
    assert result["gates"][gate] == values[gate]


def test_all_unknown_gates_preserve_unknown_without_defaulting_to_pass():
    values = {key: {"decision": "unknown", "note": "没有证据"} for key in EXPECTED_GATES}
    result = preview(gates=values)
    assert result["blocked_gates"] == list(EXPECTED_GATES)
    assert all(item["decision"] == "unknown" for item in result["gates"].values())


@pytest.mark.parametrize("include_sop", [False, True])
def test_editable_outline_has_24_unobserved_dimensions_and_opt_in_sop(include_sop):
    result = preview(include_sop=include_sop)
    assert result["state"] == "editable_draft"
    assert result["automatic_selection"] is result["source_facts_verified"] is False
    draft = result["saved_work_draft"]
    assert draft["kind"] == "podcast_episode" and draft["citations"] == []
    assert draft["contract"]["id"] == "lumenis.podcast-editorial"
    outline = draft["payload"]["interview_outline"]
    assert tuple(item["dimension"] for item in outline["research_checks"]) == EXPECTED_DIMENSIONS
    assert len(set(EXPECTED_DIMENSIONS)) == 24
    assert all(item == {"dimension": item["dimension"], "note": "", "evidence_status": "not_observed"}
               for item in outline["research_checks"])
    assert outline["optional_recording_sop"] == (EXPECTED_SOP if include_sop else [])
    assert len(outline["mainline"]) == 6 and len(outline["subtext"]) == 4
    assert all(item["question"] and item["followups"] and item["user_answer"] == "" for item in outline["mainline"])
    assert all(item["question"] and item["user_answer"] == "" for item in outline["subtext"])
    assert "尚未独立核实" in draft["markdown"]
    assert "## 明线" in draft["markdown"] and "## 暗线" in draft["markdown"]


def test_input_records_are_not_mutated_and_hash_tracks_human_changes():
    library, decisions = guests(), gates()
    before = deepcopy((library, decisions))
    first = preview(guests=library, gates=decisions)
    assert (library, decisions) == before
    assert first == preview(guests=library, gates=decisions)
    decisions[EXPECTED_GATES[0]]["note"] += "；补充人工依据"
    second = preview(guests=library, gates=decisions)
    assert first["input_hash"] != second["input_hash"]
    assert first["ranking"]["input_hash"] == second["ranking"]["input_hash"]
    library[0]["viewpoints"].append("新增用户提供观点")
    third = preview(guests=library, gates=decisions)
    assert second["ranking"]["input_hash"] != third["ranking"]["input_hash"]
    assert first["saved_work_draft"]["payload"]["guest_library"] == before[0]


@pytest.mark.parametrize("topic", [None, True, 1, [], {}, "", " \t\n", "字" * 2001, "bad\x00", "bad\u202e"],
                         ids=["null", "boolean", "number", "array", "object", "empty", "whitespace", "oversized", "nul", "bidi"])
def test_invalid_topic_is_a_stable_input_error(topic):
    with pytest.raises(ValueError, match="PODCAST_EDITORIAL_TEXT_INVALID"):
        preview(topic=topic)


@pytest.mark.parametrize("limit", [True, False, None, "1", 1.0, 0, -1, 51, [], {}])
def test_limit_is_bounded_exact_integer(limit):
    with pytest.raises(ValueError, match="PODCAST_GUEST_LIMIT_INVALID"):
        editorial.rank_guests(TOPIC, guests(), limit=limit)


@pytest.mark.parametrize("library", [None, {}, (), [], [None], [{}]])
def test_guest_library_requires_complete_bounded_records(library):
    with pytest.raises(ValueError, match="PODCAST_GUEST_(LIBRARY|RECORD)_INVALID"):
        preview(guests=library)


@pytest.mark.parametrize("field,value,code", [
    ("guest_id", "has spaces", "ID_INVALID"), ("guest_id", "../guest", "ID_INVALID"),
    ("guest_id", "中文", "ID_INVALID"), ("name", "", "TEXT_INVALID"),
    ("domains", "品牌", "RECORD_INVALID"), ("domains", [None], "TEXT_INVALID"),
    ("prior_programmes", ["字" * 1001], "TEXT_INVALID"),
    ("viewpoints", ["one"] * 31, "RECORD_INVALID"),
    ("source_refs", [True], "TEXT_INVALID"), ("source_refs", "note:01", "RECORD_INVALID"),
], ids=["id-spaces", "id-path", "id-non-ascii", "empty-name", "domains-scalar", "domains-null",
        "programme-oversized", "viewpoint-count", "source-boolean", "sources-scalar"])
def test_invalid_record_fields_fail_closed(field, value, code):
    library = guests()
    library[0][field] = value
    with pytest.raises(ValueError, match=code):
        preview(guests=library)


def test_unknown_fields_duplicate_ids_empty_profile_and_library_cap_rejected():
    library = guests()
    library[0]["verified"] = True
    with pytest.raises(ValueError, match="RECORD_INVALID"):
        preview(guests=library)
    library = guests()
    library[1]["guest_id"] = library[0]["guest_id"]
    with pytest.raises(ValueError, match="ID_INVALID"):
        preview(guests=library)
    library = guests()
    library[0].update(domains=[], prior_programmes=[], viewpoints=[])
    with pytest.raises(ValueError, match="PROFILE_EMPTY"):
        preview(guests=library)
    with pytest.raises(ValueError, match="LIBRARY_INVALID"):
        preview(guests=[guests()[0]] * 201)


@pytest.mark.parametrize("choice", ["missing", "", True, 1, [], {}])
def test_unknown_or_wrong_type_guest_selection_is_rejected(choice):
    with pytest.raises(ValueError, match="PODCAST_GUEST_SELECTION_INVALID"):
        preview(selected_guest_id=choice)


@pytest.mark.parametrize("value", [None, 0, 1, "true", [], {}])
def test_sop_is_explicit_boolean(value):
    with pytest.raises(ValueError, match="PODCAST_SOP_OPTION_INVALID"):
        preview(include_sop=value)


@pytest.mark.parametrize("value", [None, [], {}, {"resonance": {"decision": "pass", "note": "人工判断"}}])
def test_all_three_manual_gates_are_required(value):
    with pytest.raises(ValueError, match="PODCAST_MANUAL_GATES_REQUIRED"):
        preview(gates=value)


@pytest.mark.parametrize("decision", [None, True, 1, "PASS", "approved", [], {}])
def test_invalid_gate_decision_returns_value_error_not_server_error(decision):
    values = gates()
    values[EXPECTED_GATES[0]]["decision"] = decision
    with pytest.raises(ValueError, match="PODCAST_MANUAL_GATE_INVALID"):
        preview(gates=values)


@pytest.mark.parametrize("item", [None, [], {}, {"decision": "pass"},
                                   {"decision": "pass", "note": "人为判断", "verified": True}])
def test_gate_shape_cannot_claim_extra_verified_fields(item):
    values = gates()
    values[EXPECTED_GATES[0]] = item
    with pytest.raises(ValueError, match="PODCAST_MANUAL_GATE_INVALID"):
        preview(gates=values)


@pytest.mark.parametrize("note", [None, True, "", " ", "\x00", "字" * 2001],
                         ids=["null", "boolean", "empty", "whitespace", "nul", "oversized"])
def test_gate_requires_nonempty_bounded_human_note(note):
    values = gates()
    values[EXPECTED_GATES[0]]["note"] = note
    with pytest.raises(ValueError, match="PODCAST_EDITORIAL_TEXT_INVALID"):
        preview(gates=values)


def test_saved_editorial_draft_revises_reopens_and_preserves_immutable_parent(workspace, monkeypatch):
    from lumenis.shared.database import DatabaseRepository
    ws = workspace
    owner = ws["work"]
    draft = preview(include_sop=True)["saved_work_draft"]
    arguments = {"actor": ws["actor"], "scope": SHARED_SCOPE}
    first = owner.save_work(**deepcopy(draft), request_id="editorial-first-save-01", **arguments)
    artifact_id = first["artifact"]["artifact_id"]
    parent_bytes = owner.read_committed_work(artifact_id, **arguments)["content"]
    assert hashlib.sha256(parent_bytes).hexdigest() == first["artifact"]["sha256"]
    assert first["document"]["version"] == 1
    assert first["document"]["context"]["scope_kind"] == "shared_workspace"
    assert first["document"]["payload"] == draft["payload"]
    assert first["document"]["citations"] == []
    assert first["receipt"]["constraint_observations"]["parent_chain_verified"] is True
    revised_draft = deepcopy(draft)
    revised_draft["payload"]["interview_outline"]["mainline"][0]["question"] = "请从第一次研究消费者需求的亲身经历讲起。"
    revised_draft["payload"]["interview_outline"]["research_checks"][0]["note"] = "用户补充的待验证定位假设"
    revised_draft["markdown"] += "\n\n用户修订：首问采用具体研究经历，定位仍待核验。"
    revision_args = {**deepcopy(revised_draft), "request_id": "editorial-revision-save-02",
                     "work_id": first["document"]["work_id"], "previous_artifact_id": artifact_id,
                     "expected_draft_digest": first["document"]["draft_digest"], **arguments}
    second = owner.save_work(**revision_args)
    assert second["document"]["version"] == 2
    assert second["document"]["work_id"] == first["document"]["work_id"]
    assert second["document"]["parent_artifact_id"] == artifact_id
    assert second["document"]["parent_sha256"] == first["artifact"]["sha256"]
    assert second["document"]["payload"] == revised_draft["payload"]
    assert second["document"]["payload"]["manual_gates"] == first["document"]["payload"]["manual_gates"]
    replay = owner.save_work(**revision_args)
    assert replay["replayed"] is True and replay["artifact"]["artifact_id"] == second["artifact"]["artifact_id"]
    before_count = ws["repo"].query_one("SELECT COUNT(*) FROM lumenis_shared_artifacts")[0]
    with pytest.raises(ValueError, match="WORK_REVISION_CONFLICT"):
        owner.save_work(**{**revision_args, "request_id": "editorial-stale-parent-03"})
    assert ws["repo"].query_one("SELECT COUNT(*) FROM lumenis_shared_artifacts")[0] == before_count
    # Reopen from a newly constructed repository/connection, not a returned dict.
    repository = DatabaseRepository(str(ws["root"] / "isolated.sqlite3"))
    monkeypatch.setattr(owner, "get_repository", lambda: repository)
    reopened = owner.reopen_work(second["artifact"]["artifact_id"], **arguments)
    original = owner.read_committed_work(artifact_id, **arguments)
    assert reopened["document"] == second["document"]
    assert original["content"] == parent_bytes
    assert original["document"] == first["document"]
    assert original["document"]["payload"]["interview_outline"]["mainline"][0]["question"] == draft["payload"]["interview_outline"]["mainline"][0]["question"]
    print("EDITORIAL_SAVED_WORK", {"work_id": first["document"]["work_id"],
          "parent_artifact_id": artifact_id, "parent_sha256": first["artifact"]["sha256"],
          "revision_artifact_id": second["artifact"]["artifact_id"],
          "revision_sha256": second["artifact"]["sha256"], "version": 2,
          "parent_bytes_unchanged": True, "new_connection_reopen": True})


def test_saved_editorial_revision_requires_exact_draft_baseline(workspace):
    ws = workspace
    draft = preview()["saved_work_draft"]
    arguments = {"actor": ws["actor"], "scope": SHARED_SCOPE}
    first = ws["work"].save_work(**draft, request_id="editorial-baseline-save-01", **arguments)
    for digest in (None, "0" * 64):
        with pytest.raises(ValueError, match="WORK_DRAFT_REVISION_CONFLICT"):
            ws["work"].save_work(**draft, request_id="editorial-baseline-bad-02", **arguments,
                                work_id=first["document"]["work_id"],
                                previous_artifact_id=first["artifact"]["artifact_id"],
                                expected_draft_digest=digest)
