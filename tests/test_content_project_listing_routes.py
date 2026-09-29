"""Saved-work discovery uses the real local Artifact and request boundaries."""
import pytest

from tests.test_local_content_source_routes import (
    HEADERS, local_client, media_store, imported_audio_project, export_project,
)


def test_saved_work_can_be_found_after_new_client_and_reopened(local_client):
    client, store, app = local_client
    url = "/api/experience/content-projects"
    before = client.get(url, headers=HEADERS)
    assert before.status_code == 200, before.get_json()
    assert before.get_json()["projects"] == []
    payload = imported_audio_project(client, store)
    exported = export_project(client, payload)
    assert exported.status_code == 200, exported.get_json()
    project_id = exported.get_json()["result"]["artifact"]["artifact_id"]
    fresh = app.test_client()
    listed = fresh.get(url, headers=HEADERS)
    assert listed.status_code == 200, listed.get_json()
    assert [item["artifact_id"] for item in listed.get_json()["projects"]] == [project_id]
    assert fresh.get(f"{url}/{project_id}", headers=HEADERS).status_code == 200
    # Another domain cannot discover any identifier, title or count for this work.
    other = fresh.get(url, headers={**HEADERS, "X-Domain-Id": "CTH", "X-Product-Id": "CTH"})
    assert other.status_code == 200, other.get_json()
    assert other.get_json()["projects"] == []
    assert project_id not in other.get_data(as_text=True)
    app.config["LUMENIS_OPEN_WORKSPACE"] = False
    denied = fresh.get(url, headers=HEADERS)
    assert denied.status_code == 401 and "projects" not in denied.get_json()
    app.config["LUMENIS_OPEN_WORKSPACE"] = True
    assert fresh.get(url, headers=HEADERS).get_json()["projects"] == listed.get_json()["projects"]


@pytest.mark.parametrize("query", ["limit=0", "limit=21", "limit=oops", "limit=1.0", "cursor=forged"])
def test_invalid_listing_request_is_honest_error(local_client, query):
    client, _store, _app = local_client
    response = client.get(f"/api/experience/content-projects?{query}", headers=HEADERS)
    assert response.status_code == 400, response.get_json()
    assert response.get_json()["ok"] is False
    assert "projects" not in response.get_json()


@pytest.mark.parametrize("extra", [{"Origin": "https://foreign.invalid"}, {"X-Forwarded-For": "127.0.0.1"}])
def test_remote_request_cannot_discover_local_work(local_client, extra):
    client, _store, _app = local_client
    response = client.get("/api/experience/content-projects", headers={**HEADERS, **extra})
    assert response.status_code in {401, 403}
    assert "projects" not in response.get_json()
