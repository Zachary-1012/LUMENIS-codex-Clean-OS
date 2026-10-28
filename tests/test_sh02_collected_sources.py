"""GLOBAL source inspection through original product owners; acquisition is a fixture."""
import json
import socket
import sqlite3

import pytest
from flask import Flask

from tests.test_collector_transaction_truth import collector_case as collector_case, URL, GLOBAL_MODE


LIBRARY = "/api/experience/screen/SH-02"


@pytest.fixture
def collected_library(collector_case, monkeypatch, tmp_path):
    import experience_runtime as runtime
    import experience_screens as screens
    import shared_artifacts
    from lumenis.system.collector.adapters.public_http import PublicHttpAdapter
    from lumenis.system.collector.adapters.public_source import PublicResponse
    from lumenis.system.collector.guard import task_queue

    def deny_network(*args, **kwargs):
        raise AssertionError("offline source-custody test must not access a network")
    monkeypatch.setattr(socket.socket, "connect", deny_network)
    case = collector_case
    monkeypatch.setenv("ZBC_ARTIFACT_DIR", str(tmp_path / "artifacts"))
    shared_artifacts.ensure_artifact_table()
    monkeypatch.setattr(task_queue, "DEFAULT_PATH", str(tmp_path / "queue.sqlite3"))
    monkeypatch.setattr(runtime, "_all_builders", lambda: {"SH-02": screens._build_sh02})
    source_url = "https://public.example.test/independent-original"
    text = "A permitted public statement retains its original source and missing metrics. " * 30
    raw = ("<html><head><title>Independent public original</title></head><body><main><h1>"
           "Independent public original</h1><p>" + text + "</p><img src='/source-image.png'>"
           "</main></body></html>").encode()
    reads = []
    def fetch(url):
        reads.append(url)
        return PublicResponse(url=url, requested_url=url, content=raw,
                              content_type="text/html", status_code=200)
    adapter = PublicHttpAdapter(fetcher=fetch)
    monkeypatch.setattr(case["surface"], "_get_runtime_adapter", lambda *args: adapter)
    monkeypatch.setitem(case["surface"]._last_action, "public_http", 0.0)
    case["gate"].grant_permission(case["permission"].PermissionLevel.HUMAN_APPROVAL)
    source = {"platform": "public_http", "keyword": source_url, "max_results": 1}
    def post(action, **extra):
        return case["client"].post(URL, headers=GLOBAL_MODE, json={**source,
            "operator": "human", "confirm_read_only": True, "action": action, **extra})
    prepared = post("prepare").get_json()
    confirmed = post("confirm", confirmed_resource=prepared["approval_resource"])
    assert confirmed.get_json()["approved"], confirmed.get_json()
    task = post("start", request_id="global-library-original-fixture").get_json()
    task_id = task["task_id"]
    finished = case["client"].post(URL, headers=GLOBAL_MODE, json={"operator": "human",
        "confirm_read_only": True, "action": "step", "task_id": task_id}).get_json()
    assert finished["status"] == "COMPLETED", finished
    assert finished["result"]["canonical_synced"] == 1
    case.update(task_id=task_id, reads=reads, queue=task_queue)
    return case


def _inspection(case):
    response = case["client"].get(LIBRARY)
    assert response.status_code == 200, response.get_json()
    value = response.get_json()
    assert response.headers["Cache-Control"] == "no-store"
    assert len(value["data"]["evidence"]) == 1, value
    return value, value["data"]["evidence"][0]


def test_global_original_appears_and_reopens_without_focus_promotion_or_queue_writes(
        collected_library, monkeypatch):
    import experience_runtime as runtime
    case = collected_library
    queue = case["queue"].TaskQueue()
    original = queue.get(case["task_id"])
    payload = json.loads(json.dumps(original["payload"]))
    payload["binding"]["identity"] = {"principal_ref": "another-workspace"}
    queue.enqueue_once("collector_manual_request", payload, "different-owner-same-source")
    queue.close()
    def no_queue_constructor(*args, **kwargs):
        raise AssertionError("library read must not initialize/migrate the task queue")
    monkeypatch.setattr(case["queue"].TaskQueue, "__init__", no_queue_constructor)
    value, row = _inspection(case)
    assert value["data"]["partial"] is False
    assert value["truth"]["coverage"]["CTH"]["rejected_count"] == 1
    assert value["truth"]["coverage"]["CTH"]["unresolved_rejected_count"] == 0
    assert row["kind"] == "COLLECTED_SOURCE" and row["lineage"] == ["SOURCE", "EVIDENCE"]
    projection, source = row["projection"], row["inspection"]
    assert projection["version"] == 3 and projection["purpose"] == "SOURCE_INSPECTION"
    assert projection["stored_scope"]["scope_status"] == "UNASSIGNED"
    assert projection["stored_scope"]["global"] is True
    assert projection["integrity"]["verified"] is True
    assert source["metrics"]["views"] is None and source["metric_states"]["views"] == "NOT_REPORTED"
    assert source["source_use"]["grants_source_use"] is False
    assert source["source_use"]["research_reference"] == "NOT_EVALUATED"
    assert source["collection_task"]["task_id"] == case["task_id"]
    assert source["collection_task_state"] == "AVAILABLE"
    assert source["media"][0]["original_bytes_state"] == "NOT_ACQUIRED"
    original_action = source["original"]
    reopened = case["client"].get(original_action["endpoint"], headers=GLOBAL_MODE,
                                   query_string=original_action["query"])
    assert reopened.status_code == 200, reopened.get_json()
    body = reopened.get_json()["items"][0]["body"]
    assert len(body) > 1000 and source["body_preview"] == body[:1000]
    new_app = Flask(__name__)
    new_app.config["LUMENIS_OPEN_WORKSPACE"] = True
    new_app.register_blueprint(runtime.experience_bp)
    cold = new_app.test_client().get(LIBRARY).get_json()["data"]["evidence"][0]
    assert cold == row
    assert case["reads"] == ["https://public.example.test/independent-original"]
    with sqlite3.connect(case["db_path"]) as connection:
        canonical = connection.execute("SELECT scope_status,subject_id,brand_focus_id,content FROM canonical_data").fetchone()
        assert canonical[0] == "UNASSIGNED" and not canonical[1] and not canonical[2]
        assert canonical[3] == body
        assert connection.execute("SELECT COUNT(*) FROM canonical_data").fetchone()[0] == 1
    focused = case["client"].get(LIBRARY, headers=case["focus_headers"])
    assert focused.status_code == 200 and focused.get_json()["data"]["evidence"] == []


@pytest.mark.parametrize("target", ["evidence", "source"])
def test_current_source_or_signed_observation_change_denies_and_original_bytes_recover(
        collected_library, target):
    case = collected_library
    _, row = _inspection(case)
    source = row["inspection"]
    with sqlite3.connect(case["db_path"]) as connection:
        if target == "evidence":
            evidence_id = int(source["evidence_ref"].split(":")[1])
            previous = connection.execute("SELECT inputs_json FROM app_evidence_records WHERE id=?", (evidence_id,)).fetchone()[0]
            statement = "UPDATE app_evidence_records SET inputs_json=? WHERE id=?"
            key = evidence_id
            connection.execute(statement, ('{"changed":true}', key))
        else:
            previous = connection.execute("SELECT content FROM canonical_data WHERE source_id=?", (source["source_id"],)).fetchone()[0]
            statement = "UPDATE canonical_data SET content=? WHERE source_id=?"
            key = source["source_id"]
            connection.execute(statement, ("Unobserved content replacement", key))
    hidden = case["client"].get(LIBRARY).get_json()
    assert hidden["data"]["evidence"] == [] and hidden["data"]["partial"] is True
    original_action = source["original"]
    denied = case["client"].get(original_action["endpoint"], headers=GLOBAL_MODE,
                                 query_string=original_action["query"])
    assert denied.status_code == 403
    with sqlite3.connect(case["db_path"]) as connection:
        connection.execute(statement, (previous, key))
    _, recovered = _inspection(case)
    assert recovered == row and len(case["reads"]) == 1


def test_evidence_read_does_not_grant_collector_inspection(collected_library, monkeypatch):
    from types import SimpleNamespace
    from lumenis.system.security import permission
    case = collected_library
    checker = permission.check_local_workspace_scope_permission
    def deny_collector(actor, **scope):
        if scope.get("module") == "collector":
            return SimpleNamespace(allowed=False, verification_state="verified")
        return checker(actor, **scope)
    monkeypatch.setattr(permission, "check_local_workspace_scope_permission", deny_collector)
    response = case["client"].get(LIBRARY)
    assert response.status_code == 200, response.get_json()
    value = response.get_json()
    assert value["data"]["evidence"] == [] and value["data"]["partial"] is True
    assert len(case["reads"]) == 1


def test_collector_revocation_during_projection_discards_the_response(collected_library, monkeypatch):
    from types import SimpleNamespace
    from lumenis.system.collector.adapters import secondary_collection as collector
    from lumenis.system.security import permission
    case = collected_library
    reader = collector.read_collected_items
    checker = permission.check_local_workspace_scope_permission
    def revoke_after_source_read(*args, **kwargs):
        result = reader(*args, **kwargs)
        def revoked(actor, **scope):
            if scope.get("module") == "collector":
                return SimpleNamespace(allowed=False, verification_state="verified")
            return checker(actor, **scope)
        monkeypatch.setattr(permission, "check_local_workspace_scope_permission", revoked)
        return result
    monkeypatch.setattr(collector, "read_collected_items", revoke_after_source_read)
    response = case["client"].get(LIBRARY)
    assert response.status_code == 403 and "data" not in response.get_json()
    assert len(case["reads"]) == 1


def test_missing_task_store_retains_source_and_never_creates_another_store(
        collected_library, monkeypatch, tmp_path):
    case = collected_library
    absent = tmp_path / "never-created" / "queue.sqlite3"
    monkeypatch.setattr(case["queue"], "DEFAULT_PATH", str(absent))
    _, row = _inspection(case)
    assert row["inspection"]["collection_task"] is None
    assert row["inspection"]["collection_task_state"] == "NOT_RECORDED"
    assert not absent.exists() and not absent.parent.exists()
