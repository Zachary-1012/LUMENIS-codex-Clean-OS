"""Independent interpreter for the isolated Collector commit/death regression.

This helper never loads app.py, a platform session, or an inherited signing key.
The test manifest identifies the disposable stores and the test-owned Atom bytes.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import sys


def main() -> None:
    manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    mode = sys.argv[2]
    assert mode in {"crash", "recover"}
    root = Path(manifest["root"]).resolve()
    db_path = Path(manifest["db_path"]).resolve()
    queue_path = Path(manifest["queue_path"]).resolve()
    assert db_path.is_relative_to(root) and queue_path.is_relative_to(root)
    assert db_path.is_file() and queue_path.is_file()
    os.environ.update(
        ZBC_DB_PATH=str(db_path),
        ZBC_DATA_DIR=str(queue_path.parent),
        ZBC_EVIDENCE_DB_PATH=str(db_path),
        ZBC_TEST_OFFLINE="1",
        LUMENIS_EVIDENCE_HMAC_KEY_RING=json.dumps({
            "collector-transaction-test": "isolated-test-signing-key-only"}),
        LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID="collector-transaction-test",
    )
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

    def no_network(*args, **kwargs):
        raise AssertionError("isolated commit worker attempted network access")

    socket.socket.connect = no_network
    socket.socket.connect_ex = no_network
    socket.create_connection = no_network

    from lumenis.adapters import collector_service as service
    from lumenis.auth import service as auth
    from lumenis.system.collector.adapters import secondary_collection as entry
    from lumenis.system.collector.adapters.public_source import PublicResponse
    from lumenis.system.collector.adapters.web_atom import AtomAdapter
    from lumenis.system.collector.guard import task_queue
    from lumenis.system import security
    from lumenis.system.security import permission

    task_queue.DEFAULT_PATH = str(queue_path)
    auth._initialized = True
    permission._TESTING_BYPASS_ENABLED = False
    gate = permission.PermissionGate()
    gate.grant_permission(permission.PermissionLevel.COMMIT)
    permission.get_permission_gate = security.get_permission_gate = lambda: gate
    queue = service._queue()
    row = queue.get(int(manifest["task_id"][3:]))
    queue.close()
    payload = row["payload"]
    _, denial = entry._manual_collection_guard(
        {"id": payload["actor_id"]}, payload["scope"], "web_atom",
        payload["keyword"], payload["max_results"])
    if denial is not None:
        assert denial["status"] == "APPROVAL_REQUIRED", denial
        gate.grant_approval("data_import", resource=denial["approval_resource"],
                            granted_by="explicit isolated independent worker")

    if mode == "crash":
        def fetch_fixture(url):
            assert url == manifest["source_url"]
            return PublicResponse(url=url, content=manifest["atom"].encode("utf-8"),
                                  content_type="application/atom+xml", status_code=200)
        adapter = AtomAdapter(fetcher=fetch_fixture)
        entry._get_runtime_adapter = lambda *args: adapter
        task_queue.TaskQueue.save_progress = lambda *args, **kwargs: os._exit(86)
    else:
        def no_refetch(*args, **kwargs):
            raise AssertionError("receipt recovery fetched source")
        entry._get_runtime_adapter = no_refetch
    service._job(manifest["task_id"])
    completed = service.get_task(manifest["task_id"])
    assert mode == "recover", "crash worker missed the injected death point"
    assert completed["success"] is True, completed
    assert completed["per_platform"]["web_atom"]["commit_reconciled"] is True
    print(json.dumps(completed))


if __name__ == "__main__":
    main()
