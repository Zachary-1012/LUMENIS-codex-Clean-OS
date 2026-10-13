"""SH-06 read-only inbox backend (SH-06.md section 1-5, 7). Signed: 阿康1（bot）."""
import hashlib
import json
import re

import pytest

import experience_screens as es

GLOBAL = {"module": "operational_inbox", "canonical_scope": "GLOBAL_ALL", "domain_id": None,
          "subject_id": None, "brand_focus_id": None, "read_allowed": True,
          "global_all_granted": True}
FOCUS = {"module": "operational_inbox", "canonical_scope": "FOCUS", "domain_id": "CTH",
         "subject_id": "subj-a", "brand_focus_id": None, "display_name": "示例商场",
         "read_allowed": True, "global_all_granted": False}


def _chain(task_id, contents):
    rows, prev = [], None
    for i, content in enumerate(contents):
        ev, now = f"ev-{task_id}-{i}", f"2026-10-13T10:00:0{i}"
        cur = hashlib.sha256(f"{prev or 'genesis'}|{ev}|{task_id}|{content}|{now}".encode()).hexdigest()
        rows.append({"evidence_id": ev, "task_id": task_id, "content": content,
                     "created_at": now, "previous_hash": prev, "current_hash": cur})
        prev = cur
    return rows


class _Engine:
    def __init__(self, tasks, evidence):
        self.tasks, self.evidence = tasks, evidence

    def list_tasks(self, limit=50):
        return self.tasks

    def get_evidence(self, task_id):
        return self.evidence.get(task_id, [])

    def health_check(self):
        return {"status": "healthy"}


def _task(task_id, context=None, status="running", risk="L3"):
    return {"task_id": task_id, "intent": "整理本周待办", "status": status,
            "risk_level": risk, "context_json": json.dumps(context or {})}


@pytest.fixture
def engine(monkeypatch):
    import ai_task_engine

    holder = {}
    monkeypatch.setattr(ai_task_engine, "get_task_engine", lambda: holder["engine"])
    return holder


def _build(holder, tasks, evidence, binding):
    holder["engine"] = _Engine(tasks, evidence)
    return es._build_sh06(binding=binding)


def test_scope_unavailable_returns_no_items_scope_or_totals(engine):
    for binding in (None, {**GLOBAL, "read_allowed": False}):
        r = _build(engine, [_task("t1")], {"t1": _chain("t1", ["a"])}, binding)
        assert r["bound"] is True and r["sections"][0]["type"] == "head"
        assert "scope" not in r and "permission" not in r and "data" not in r


def test_global_inbox_emits_projection_v2_for_verified_task(engine):
    r = _build(engine, [_task("t1")], {"t1": _chain("t1", ["a", "b"])}, GLOBAL)
    assert r["scope"] == {"mode": "GLOBAL_ALL", "global_all_granted": True}
    assert r["permission"]["decision"] == "ALLOW" and r["permission"]["read"] is True
    [item] = r["data"]["tasks"]
    p = item["projection"]
    assert p["contract"] == "lumenis.shared.experience-row-projection" and p["version"] == 2
    assert p["read_allowed"] is True and p["origin_verified"] is True
    assert re.match(r"^evidence:canonical:[A-Za-z0-9._:-]+$", p["evidence"]["canonical_reference"])
    i = p["integrity"]
    assert (i["integrity_version"], i["verified"], i["lineage_verified"]) == (2, True, True)
    assert i["assurance"] == "content-integrity-only" and i["algorithm"] == "sha256"
    assert i["digest"] == _chain("t1", ["a", "b"])[-1]["current_hash"]
    assert item["kind"] == "TASK" and item["state"] == "running" and item["priority"] == "HIGH"
    assert r["data"]["notifications"] == [] and r["data"]["alerts"] == []


def test_tasks_without_verified_evidence_lineage_are_dropped(engine):
    broken = _chain("t2", ["a", "b"])
    broken[1]["content"] = "tampered"
    unlinked = _chain("t4", ["a", "b"])
    unlinked[1]["previous_hash"] = None
    r = _build(engine, [_task("t1"), _task("t2"), _task("t3"), _task("t4")],
               {"t1": _chain("t1", ["a"]), "t2": broken, "t4": unlinked}, GLOBAL)
    assert [t["id"] for t in r["data"]["tasks"]] == ["t1"]
    assert r["truth"]["dropped_unverified"] == 3


def test_global_envelope_rejects_focus_scoped_task_and_focus_accepts_only_exact(engine):
    tasks = [_task("tg"), _task("ta", {"domain_id": "CTH", "subject_id": "subj-a"}),
             _task("tb", {"domain_id": "CTH", "subject_id": "subj-b"}),
             _task("tx", {"domain_id": "BMP", "subject_id": "subj-a"})]
    ev = {t["task_id"]: _chain(t["task_id"], ["a"]) for t in tasks}
    assert [t["id"] for t in _build(engine, tasks, ev, GLOBAL)["data"]["tasks"]] == ["tg"]
    r = _build(engine, tasks, ev, FOCUS)
    assert [t["id"] for t in r["data"]["tasks"]] == ["ta"]
    assert r["scope"]["mode"] == "FOCUS" and r["scope"]["subject_id"] == "subj-a"
    assert r["data"]["tasks"][0]["projection"]["scope"]["global_all_granted"] is False


def test_inbox_cards_carry_no_actions_or_raw_diagnostics(engine):
    r = _build(engine, [_task("t1")], {"t1": _chain("t1", ["a"])}, GLOBAL)
    text = json.dumps(r, ensure_ascii=False)
    assert "actions" not in r["sections"][0]
    for word in ("approve", "assign", "snooze", "retry", "dismiss", "dlq", "circuit"):
        assert word not in text.lower()
    assert all(set(t) <= {"id", "kind", "title", "source_label", "priority", "state", "projection"}
               for t in r["data"]["tasks"])


def test_route_without_signed_in_actor_shows_not_displayed_state(monkeypatch):
    from flask import Flask
    import experience_runtime

    app = Flask(__name__)
    app.register_blueprint(experience_runtime.experience_bp)
    import lumenis.auth.service as auth
    monkeypatch.setattr(auth, "get_current_user", lambda: None)
    body = app.test_client().get("/api/experience/screen/SH-06").get_json()
    assert body["bound"] is True and "data" not in body and "scope" not in body
