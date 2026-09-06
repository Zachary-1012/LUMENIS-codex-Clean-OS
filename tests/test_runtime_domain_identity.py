# -*- coding: utf-8 -*-
"""Test Runtime Domain Identity — workers/tasks carry domain_id, Guardian isolates by domain.

Verifies:
1. register_worker accepts domain_id/product_id and stores them
2. heartbeat accepts domain_id and updates worker metadata
3. get_tasks_by_domain(domain_id) returns only workers in that domain
4. list_workers_by_domain(domain_id) filters correctly
5. DLQ.enqueue accepts domain_id/product_id
6. Domain isolation: CTH workers not returned in ZBMP query and vice versa
7. Worker record carries task_id/trace_id in metadata
"""
import os
import sys
import tempfile
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from runtime_guardian import RuntimeGuardian, WorkerStatus


@pytest.fixture
def guardian():
    """Create a RuntimeGuardian with a temp DB for each test."""
    tmpdb = os.path.join(tempfile.gettempdir(), f"test_rg_domain_{uuid.uuid4().hex[:8]}.db")
    g = RuntimeGuardian(name=f"test_{uuid.uuid4().hex[:8]}", db_path=tmpdb)
    yield g
    # Cleanup
    try:
        os.remove(tmpdb)
    except Exception:
        pass


class TestWorkerDomainIdentity:
    """Worker registration and heartbeat with domain_id."""

    def test_register_worker_with_domain_cth(self, guardian):
        wid = guardian.register_worker(
            "xhs_collector_cth",
            domain_id="cth",
            product_id="CTH",
            metadata={"task_id": "task_001", "trace_id": "trace_001"},
        )
        worker = guardian.get_worker(wid)
        assert worker is not None
        assert worker["domain_id"] == "cth"
        assert worker["product_id"] == "CTH"
        assert worker["metadata"].get("task_id") == "task_001"
        assert worker["metadata"].get("trace_id") == "trace_001"

    def test_register_worker_with_domain_zbmp(self, guardian):
        wid = guardian.register_worker(
            "brand_collector_zbmp",
            domain_id="zbmp",
            product_id="ZBMP",
        )
        worker = guardian.get_worker(wid)
        assert worker["domain_id"] == "zbmp"
        assert worker["product_id"] == "ZBMP"

    def test_register_worker_default_domain_system(self, guardian):
        """Workers registered without domain_id default to 'system'."""
        wid = guardian.register_worker("default_worker")
        worker = guardian.get_worker(wid)
        assert worker["domain_id"] == "system"
        assert worker["product_id"] == "SYSTEM"

    def test_heartbeat_with_domain_id(self, guardian):
        wid = guardian.register_worker("hb_test", domain_id="cth", product_id="CTH")
        result = guardian.heartbeat(wid, domain_id="cth")
        assert result is True
        worker = guardian.get_worker(wid)
        assert worker["last_heartbeat_at"] != ""
        assert worker["metadata"].get("domain_id") == "cth"


class TestTasksByDomain:
    """get_tasks_by_domain and domain isolation."""

    def test_get_tasks_by_domain_cth(self, guardian):
        wid_cth = guardian.register_worker("cth_worker", domain_id="cth", product_id="CTH")
        wid_zbmp = guardian.register_worker("zbmp_worker", domain_id="zbmp", product_id="ZBMP")
        guardian.heartbeat(wid_cth, domain_id="cth")

        cth_tasks = guardian.get_tasks_by_domain("cth")
        assert cth_tasks["domain_id"] == "cth"
        assert cth_tasks["total_workers"] == 1
        worker_names = [w["worker_name"] for w in cth_tasks["workers"]]
        assert "cth_worker" in worker_names
        assert "zbmp_worker" not in worker_names

    def test_get_tasks_by_domain_zbmp(self, guardian):
        guardian.register_worker("cth_worker", domain_id="cth", product_id="CTH")
        guardian.register_worker("zbmp_worker", domain_id="zbmp", product_id="ZBMP")
        guardian.register_worker("zbmp_worker2", domain_id="zbmp", product_id="ZBMP")

        zbmp_tasks = guardian.get_tasks_by_domain("zbmp")
        assert zbmp_tasks["total_workers"] == 2

    def test_domain_isolation_cth_not_in_zbmp(self, guardian):
        """CTH workers must not appear in ZBMP task query."""
        guardian.register_worker("cth_only", domain_id="cth", product_id="CTH")
        zbmp_tasks = guardian.get_tasks_by_domain("zbmp")
        worker_names = [w["worker_name"] for w in zbmp_tasks["workers"]]
        assert "cth_only" not in worker_names

    def test_domain_isolation_zbmp_not_in_cth(self, guardian):
        """ZBMP workers must not appear in CTH task query."""
        guardian.register_worker("zbmp_only", domain_id="zbmp", product_id="ZBMP")
        cth_tasks = guardian.get_tasks_by_domain("cth")
        worker_names = [w["worker_name"] for w in cth_tasks["workers"]]
        assert "zbmp_only" not in worker_names

    def test_list_workers_by_domain(self, guardian):
        guardian.register_worker("w1", domain_id="cth", product_id="CTH")
        guardian.register_worker("w2", domain_id="cth", product_id="CTH")
        guardian.register_worker("w3", domain_id="zbmp", product_id="ZBMP")

        cth_workers = guardian.list_workers_by_domain("cth")
        assert len(cth_workers) == 2
        zbmp_workers = guardian.list_workers_by_domain("zbmp")
        assert len(zbmp_workers) == 1


class TestDLQDomainIdentity:
    """DLQ entries carry domain_id."""

    def test_dlq_enqueue_with_domain(self, guardian):
        dlq_id = guardian.dlq.enqueue(
            worker_id="w_cth",
            run_id="run_001",
            domain_id="cth",
            product_id="CTH",
            task_type="collection",
            payload={"keywords": ["test"]},
            error="test error",
        )
        item = guardian.dlq.get(dlq_id)
        assert item is not None
        assert item["domain_id"] == "cth"
        assert item["product_id"] == "CTH"

    def test_dlq_appears_in_domain_query(self, guardian):
        guardian.dlq.enqueue(
            worker_id="w_cth", domain_id="cth", product_id="CTH",
            task_type="test", error="err",
        )
        cth_tasks = guardian.get_tasks_by_domain("cth")
        assert cth_tasks["dlq_count"] >= 1

        zbmp_tasks = guardian.get_tasks_by_domain("zbmp")
        # ZBMP should not see CTH DLQ entries
        zbmp_dlq_ids = [d["dlq_id"] for d in zbmp_tasks["dlq_entries"]]
        cth_dlq = guardian.dlq.list_pending()
        for d in cth_dlq:
            if d.get("domain_id") == "cth":
                assert d["dlq_id"] not in zbmp_dlq_ids
