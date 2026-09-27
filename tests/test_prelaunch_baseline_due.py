"""Fixture-only tests for the prelaunch public-baseline due policy."""
from datetime import datetime, timedelta, timezone
import json
import unittest
from dataclasses import asdict
import hashlib
import hmac
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lumenis.system.collector.adapters.scheduling import (
    BaselineRunHistory,
    PublicBaselinePlan,
    ScheduleDecisionStore,
    evaluate_baseline_due,
    BaselineConfigError,
    load_prelaunch_baseline_config,
    maintenance_authorization,
    run_due_prelaunch_baseline,
)
from lumenis.system.collector.adapters.scheduling.prelaunch_baseline import _canonical_config


NOW = datetime(2026, 9, 28, 12, 0, tzinfo=timezone.utc)


def plan(**changes):
    values = dict(
        source_key="public:bluesky-search",
        source_version="1",
        exact_scope="global-public-baseline/v2026-09-28",
        scope_version="2026-09-28",
        cadence_seconds=86400,
        authorization_ref="prelaunch-approval:2026-09-28",
        enabled=True,
        prelaunch_authorized=True,
        end_user_auto=False,
    )
    values.update(changes)
    return PublicBaselinePlan(**values)


class PrelaunchBaselineDueTests(unittest.TestCase):
    def authorized_plan(self, tmp):
        path, _ = self.signed_config(tmp)
        return load_prelaunch_baseline_config(path, hmac_key="fixture-key")["plans"][0]

    def test_first_run_due_and_repeat_evaluation_is_stable(self):
        p = plan()
        h = BaselineRunHistory()
        first = evaluate_baseline_due(p, h, now=NOW)
        repeated = evaluate_baseline_due(p, h, now=NOW)
        self.assertTrue(first.due)
        self.assertEqual(first.reason, "FIRST_RUN")
        self.assertEqual(first, repeated)

    def test_plan_identity_versions_source_scope_cadence_and_authority(self):
        p = plan()
        self.assertNotEqual(p.plan_id, plan(scope_version="2026-09-29").plan_id)
        self.assertNotEqual(p.plan_id, plan(cadence_seconds=172800).plan_id)
        self.assertNotEqual(p.plan_id, plan(authorization_ref="approval:next").plan_id)
        self.assertNotEqual(p.plan_id, plan(source_version="2").plan_id)

    def test_manual_prelaunch_permission_is_required_and_auto_stays_off(self):
        denied = evaluate_baseline_due(plan(prelaunch_authorized=False),
                                       BaselineRunHistory(), now=NOW)
        disabled = evaluate_baseline_due(plan(enabled=False),
                                         BaselineRunHistory(), now=NOW)
        self.assertEqual(denied.reason, "AUTHORIZATION_REQUIRED")
        self.assertFalse(denied.due)
        self.assertEqual(disabled.reason, "DISABLED")
        with self.assertRaises(ValueError):
            plan(end_user_auto=True)

    def test_unsigned_plan_cannot_claim_existing_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ScheduleDecisionStore(os.path.join(tmp, "scheduler.db"))
            with self.assertRaises(BaselineConfigError) as denied:
                store.claim_public_baseline_attempt(plan(), now=NOW)
            self.assertEqual(denied.exception.code, "HMAC_UNAVAILABLE")

    def test_success_cadence_and_attempt_in_progress(self):
        success_at = NOW - timedelta(hours=23)
        history = BaselineRunHistory(last_attempt_at=success_at,
                                     last_success_at=success_at)
        self.assertEqual(evaluate_baseline_due(plan(), history, now=NOW).reason,
                         "NOT_DUE")
        due = evaluate_baseline_due(plan(), history, now=NOW + timedelta(hours=1))
        self.assertTrue(due.due)
        pending = BaselineRunHistory(last_attempt_at=success_at,
                                     last_success_at=success_at,
                                     attempt_in_progress=True)
        self.assertEqual(evaluate_baseline_due(plan(), pending, now=NOW).reason,
                         "ATTEMPT_IN_PROGRESS")

    def test_failure_backoff_grows_and_preserves_history_across_reload(self):
        attempt = NOW - timedelta(minutes=2)
        history = BaselineRunHistory(last_attempt_at=attempt,
                                     last_success_at=attempt - timedelta(days=1),
                                     consecutive_failures=2)
        # A durable run store can reopen this exact record without changing policy.
        reopened = BaselineRunHistory(**json.loads(json.dumps(asdict(history), default=str)))
        # Restore timestamp values as the store reader would.
        reopened = BaselineRunHistory(
            last_attempt_at=datetime.fromisoformat(reopened.last_attempt_at),
            last_success_at=datetime.fromisoformat(reopened.last_success_at),
            consecutive_failures=reopened.consecutive_failures,
            attempt_in_progress=reopened.attempt_in_progress,
        )
        early = evaluate_baseline_due(plan(), reopened, now=NOW)
        self.assertEqual(early.reason, "RETRY_BACKOFF")
        self.assertEqual(early.due_at, attempt + timedelta(seconds=600))
        late = evaluate_baseline_due(plan(), reopened, now=attempt + timedelta(seconds=600))
        self.assertTrue(late.due)
        self.assertEqual(late.reason, "RETRY_DUE")

    def test_exact_scope_and_cadence_are_validated(self):
        with self.assertRaises(ValueError):
            plan(exact_scope="global/*")
        with self.assertRaises(ValueError):
            plan(cadence_seconds=30)

    def test_existing_schedule_store_claim_survives_reopen_and_success_cadence(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "isolated-scheduler-test.db")
            p = self.authorized_plan(tmp)
            first_store = ScheduleDecisionStore(db_path)
            attempt_id, decision = first_store.claim_public_baseline_attempt(p, now=NOW)
            self.assertEqual(decision.reason, "FIRST_RUN")
            self.assertIsNotNone(attempt_id)
            duplicate_id, duplicate = first_store.claim_public_baseline_attempt(p, now=NOW)
            self.assertIsNone(duplicate_id)
            self.assertEqual(duplicate.reason, "ATTEMPT_IN_PROGRESS")

            reopened_store = ScheduleDecisionStore(db_path)
            persisted = reopened_store.public_baseline_history(p)
            self.assertTrue(persisted.attempt_in_progress)
            self.assertTrue(reopened_store.finish_public_baseline_attempt(
                p, attempt_id, success=True, now=NOW + timedelta(minutes=1)))
            self.assertFalse(reopened_store.finish_public_baseline_attempt(
                p, attempt_id, success=True, now=NOW + timedelta(minutes=2)))
            next_id, next_decision = ScheduleDecisionStore(db_path).claim_public_baseline_attempt(
                p, now=NOW + timedelta(hours=23))
            self.assertIsNone(next_id)
            self.assertEqual(next_decision.reason, "NOT_DUE")
            next_id, next_decision = ScheduleDecisionStore(db_path).claim_public_baseline_attempt(
                p, now=NOW + timedelta(hours=24, minutes=1))
            self.assertIsNotNone(next_id)
            self.assertEqual(next_decision.reason, "CADENCE_DUE")

    def test_failed_attempt_is_persistent_and_backs_off(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "isolated-scheduler-test.db")
            p = self.authorized_plan(tmp)
            store = ScheduleDecisionStore(db_path)
            attempt_id, _ = store.claim_public_baseline_attempt(p, now=NOW)
            self.assertTrue(store.finish_public_baseline_attempt(
                p, attempt_id, success=False, now=NOW + timedelta(seconds=5),
                error_code="SOURCE_UNAVAILABLE"))
            reopened = ScheduleDecisionStore(db_path)
            history = reopened.public_baseline_history(p)
            self.assertEqual(history.consecutive_failures, 1)
            self.assertEqual(history.last_failure_at, NOW + timedelta(seconds=5))
            retry_id, decision = reopened.claim_public_baseline_attempt(
                p, now=NOW + timedelta(minutes=4))
            self.assertIsNone(retry_id)
            self.assertEqual(decision.reason, "RETRY_BACKOFF")
            retry_id, decision = ScheduleDecisionStore(db_path).claim_public_baseline_attempt(
                p, now=NOW + timedelta(minutes=5, seconds=5))
            self.assertIsNotNone(retry_id)
            self.assertEqual(decision.reason, "RETRY_DUE")

    def test_expired_worker_claim_becomes_failure_and_is_not_replayed_immediately(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ScheduleDecisionStore(os.path.join(tmp, "scheduler.db"))
            p = self.authorized_plan(tmp)
            attempt_id, _ = store.claim_public_baseline_attempt(p, now=NOW)
            self.assertIsNotNone(attempt_id)
            retry_id, decision = store.claim_public_baseline_attempt(
                p, now=NOW + timedelta(hours=2), lease_seconds=3600)
            self.assertIsNone(retry_id)
            self.assertEqual(decision.reason, "RETRY_BACKOFF")
            history = store.public_baseline_history(p)
            self.assertEqual(history.consecutive_failures, 1)
            self.assertFalse(history.attempt_in_progress)

    def signed_config(self, tmp, key="fixture-key"):
        config = {
            "schema_version": 1,
            "plan_version": "test-v1",
            "policy_id": "public-read-only-exact-import-v1",
            "enabled": True,
            "end_user_auto": False,
            "sources": [{
                "source_key": "feed:one",
                "source_version": "1",
                "platform": "web_atom",
                "source_url": "https://example.org/feed.atom",
                "domain_id": "cth",
                "subject_id": "subject-1",
                "scope_version": "scope-v1",
                "cadence_seconds": 86400,
                "authorization_ref": "approval-v1",
                "max_results": 8,
            }],
            "hmac": {"algorithm": "HMAC-SHA256", "value": ""},
        }
        config["hmac"]["value"] = hmac.new(
            key.encode(), _canonical_config(config), hashlib.sha256
        ).hexdigest()
        path = os.path.join(tmp, "prelaunch_public_baseline.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(config, handle)
        return path, config

    def test_signed_config_requires_hmac_and_exact_typed_authorization(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, config = self.signed_config(tmp)
            loaded = load_prelaunch_baseline_config(path, hmac_key="fixture-key")
            self.assertEqual(loaded["status"], "READY")
            plan = loaded["plans"][0]
            auth = maintenance_authorization(plan)
            exact_scope = {"domain_id": "cth", "subject_id": "subject-1",
                           "brand_focus_id": None}
            self.assertTrue(auth.matches_request(
                source_url="https://example.org/feed.atom",
                platform="web_atom", scope=exact_scope))
            self.assertFalse(auth.matches_request(
                source_url="https://other.example/feed.atom",
                platform="web_atom", scope=exact_scope))
            with self.assertRaises(BaselineConfigError) as missing:
                load_prelaunch_baseline_config(path, hmac_key="")
            self.assertEqual(missing.exception.code, "HMAC_UNAVAILABLE")
            config["sources"][0]["subject_id"] = "subject-2"
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(config, handle)
            with self.assertRaises(BaselineConfigError) as tampered:
                load_prelaunch_baseline_config(path, hmac_key="fixture-key")
            self.assertEqual(tampered.exception.code, "HMAC_MISMATCH")

    def test_scheduler_executor_claims_once_and_fails_closed_without_hmac(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, _ = self.signed_config(tmp)
            db_path = os.path.join(tmp, "scheduler.db")
            calls = []
            def fake_collect(*args, **kwargs):
                calls.append((args, kwargs))
                return {"ok": True, "status": "SUCCESS", "evidence_recorded": True,
                        "returned_count": 1, "canonical_synced": 1,
                        "scope_status": "VERIFIED", "refresh_verified": True}
            first = run_due_prelaunch_baseline(
                now=NOW, config_path=path, hmac_key="fixture-key",
                store=ScheduleDecisionStore(db_path), collect=fake_collect)
            second = run_due_prelaunch_baseline(
                now=NOW, config_path=path, hmac_key="fixture-key",
                store=ScheduleDecisionStore(db_path), collect=fake_collect)
            self.assertEqual(first["status"], "COMPLETED")
            self.assertEqual(second["status"], "COMPLETED")
            self.assertEqual(first["summary"]["succeeded"], 1)
            self.assertEqual(second["summary"]["deferred"], 1)
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0][1]["operator"], "prelaunch_maintenance")
            denied = run_due_prelaunch_baseline(
                now=NOW, config_path=path, hmac_key="",
                store=ScheduleDecisionStore(db_path), collect=fake_collect)
            self.assertEqual(denied["status"], "FAILED")
            self.assertEqual(denied["reason"], "HMAC_UNAVAILABLE")

    def test_scheduler_recovers_abandoned_worker_then_obeys_backoff(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, _ = self.signed_config(tmp)
            db_path = os.path.join(tmp, "scheduler.db")
            loaded = load_prelaunch_baseline_config(path, hmac_key="fixture-key")
            store = ScheduleDecisionStore(db_path)
            store.claim_public_baseline_attempt(loaded["plans"][0], now=NOW)
            calls = []
            def collect(*args, **kwargs):
                calls.append(1)
                return {"ok": True, "status": "SUCCESS", "evidence_recorded": True,
                        "returned_count": 1, "canonical_synced": 1,
                        "scope_status": "VERIFIED", "refresh_verified": True}
            recovered = run_due_prelaunch_baseline(
                now=NOW + timedelta(hours=2), config_path=path, hmac_key="fixture-key",
                store=ScheduleDecisionStore(db_path), collect=collect)
            self.assertEqual(recovered["runs"][0]["status"], "RETRY_BACKOFF")
            self.assertEqual(calls, [])
            retried = run_due_prelaunch_baseline(
                now=NOW + timedelta(hours=2, minutes=5), config_path=path,
                hmac_key="fixture-key", store=ScheduleDecisionStore(db_path), collect=collect)
            self.assertEqual(retried["summary"]["succeeded"], 1)
            self.assertEqual(calls, [1])

    def test_scheduler_surfaces_source_failure_and_persists_backoff(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, _ = self.signed_config(tmp)
            store = ScheduleDecisionStore(os.path.join(tmp, "scheduler.db"))
            def failed_collect(*args, **kwargs):
                return {"ok": False, "status": "SOURCE_UNAVAILABLE",
                        "evidence_recorded": False}
            first = run_due_prelaunch_baseline(
                now=NOW, config_path=path, hmac_key="fixture-key",
                store=store, collect=failed_collect,
                finish_now=lambda: NOW + timedelta(seconds=5))
            self.assertEqual(first["status"], "FAILED")
            self.assertEqual(first["summary"]["failed"], 1)
            second = run_due_prelaunch_baseline(
                now=NOW + timedelta(seconds=30), config_path=path,
                hmac_key="fixture-key", store=store, collect=failed_collect,
                finish_now=lambda: NOW + timedelta(seconds=35))
            self.assertEqual(second["status"], "COMPLETED")
            self.assertEqual(second["runs"][0]["status"], "RETRY_BACKOFF")
            self.assertEqual(second["summary"]["deferred"], 1)

    def test_empty_or_unverified_refresh_never_records_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, _ = self.signed_config(tmp)
            store = ScheduleDecisionStore(os.path.join(tmp, "scheduler.db"))
            def empty_collect(*args, **kwargs):
                return {"ok": True, "status": "NO_NEW_DATA", "evidence_recorded": True,
                        "returned_count": 0, "canonical_synced": 0,
                        "scope_status": "VERIFIED", "refresh_verified": True}
            result = run_due_prelaunch_baseline(
                now=NOW, config_path=path, hmac_key="fixture-key",
                store=store, collect=empty_collect,
                finish_now=lambda: NOW + timedelta(seconds=1))
            self.assertEqual(result["runs"][0]["status"], "NO_SOURCE_RESULT")
            self.assertEqual(store.public_baseline_history(
                load_prelaunch_baseline_config(path, hmac_key="fixture-key")["plans"][0]
            ).consecutive_failures, 1)

    def test_disabled_default_config_does_not_require_key(self):
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                   "config", "prelaunch_public_baseline.json")
        loaded = load_prelaunch_baseline_config(config_path, hmac_key="")
        self.assertEqual(loaded, {"status": "DISABLED", "plans": []})

    def _write_signed_config(self, path, config, key="fixture-key"):
        config["hmac"]["value"] = hmac.new(
            key.encode(), _canonical_config(config), hashlib.sha256
        ).hexdigest()
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(config, handle)

    def test_server_config_environment_path_and_full_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, config = self.signed_config(tmp)
            template = config["sources"][0]
            config["sources"] = [
                {**template, "source_key": f"feed:{index}",
                 "source_url": f"https://example.org/feed-{index}.atom"}
                for index in range(1401)
            ]
            self._write_signed_config(path, config)
            old = os.environ.get("LUMENIS_PRELAUNCH_BASELINE_CONFIG")
            os.environ["LUMENIS_PRELAUNCH_BASELINE_CONFIG"] = path
            try:
                loaded = load_prelaunch_baseline_config(hmac_key="fixture-key")
            finally:
                if old is None:
                    os.environ.pop("LUMENIS_PRELAUNCH_BASELINE_CONFIG", None)
                else:
                    os.environ["LUMENIS_PRELAUNCH_BASELINE_CONFIG"] = old
            self.assertEqual(loaded["status"], "READY")
            self.assertEqual(len(loaded["plans"]), 1401)

    def test_due_batch_is_oldest_first_and_bounded_to_eight_attempts(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, config = self.signed_config(tmp)
            template = config["sources"][0]
            config["sources"] = [
                {**template, "source_key": f"feed:{index:02}",
                 "source_url": f"https://example.org/feed-{index:02}.atom"}
                for index in range(10)
            ]
            self._write_signed_config(path, config)
            plans = load_prelaunch_baseline_config(path, hmac_key="fixture-key")["plans"]
            store = ScheduleDecisionStore(os.path.join(tmp, "scheduler.db"))
            for index, current in enumerate(plans):
                succeeded_at = NOW - timedelta(days=1, minutes=index)
                attempt_id, decision = store.claim_public_baseline_attempt(
                    current, now=succeeded_at)
                self.assertIsNotNone(attempt_id)
                self.assertTrue(store.finish_public_baseline_attempt(
                    current, attempt_id, success=True, now=succeeded_at))
            calls = []
            def successful_collect(platform, source_url, **kwargs):
                calls.append(source_url)
                return {"ok": True, "status": "SUCCESS", "evidence_recorded": True,
                        "returned_count": 1, "canonical_synced": 1,
                        "scope_status": "VERIFIED", "refresh_verified": True}
            first = run_due_prelaunch_baseline(
                now=NOW, config_path=path, hmac_key="fixture-key",
                store=store, collect=successful_collect)
            self.assertEqual(len(calls), 8)
            self.assertEqual(first["summary"]["deferred"], 2)
            self.assertEqual(calls, [f"https://example.org/feed-{i:02}.atom"
                                     for i in range(9, 1, -1)])
            second = run_due_prelaunch_baseline(
                now=NOW, config_path=path, hmac_key="fixture-key",
                store=store, collect=successful_collect)
            self.assertEqual(len(calls), 10)
            self.assertEqual(calls[-2:], ["https://example.org/feed-01.atom",
                                          "https://example.org/feed-00.atom"])
            self.assertEqual(second["summary"]["succeeded"], 2)

    def test_success_requires_persisted_terminal_outcome(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, _ = self.signed_config(tmp)
            class FinishFailureStore(ScheduleDecisionStore):
                def finish_public_baseline_attempt(self, *args, **kwargs):
                    return False
            result = run_due_prelaunch_baseline(
                now=NOW, config_path=path, hmac_key="fixture-key",
                store=FinishFailureStore(os.path.join(tmp, "scheduler.db")),
                collect=lambda *args, **kwargs: {
                    "ok": True, "status": "SUCCESS", "evidence_recorded": True,
                    "returned_count": 1, "canonical_synced": 1,
                    "scope_status": "VERIFIED", "refresh_verified": True})
            self.assertEqual(result["runs"][0]["status"],
                             "OUTCOME_PERSISTENCE_FAILED")
            self.assertEqual(result["summary"]["succeeded"], 0)
            self.assertEqual(result["summary"]["failed"], 1)

    def test_maintenance_operator_cannot_spoof_human_or_skip_signed_plan(self):
        from lumenis.system.collector.adapters.secondary_collection import collect_search
        result = collect_search(
            "web_atom", "https://example.org/feed.atom", operator="prelaunch_maintenance",
            scope={"domain_id": "cth", "subject_id": "subject-1",
                   "brand_focus_id": None},
            prelaunch_local_import=True, prelaunch_authorization=None,
        )
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "SCOPE_UNAUTHORIZED")


if __name__ == "__main__":
    unittest.main()
