# -*- coding: utf-8 -*-
"""阶段5：RedNote 运行策略 SoT 单测（纯配置、不触网、不连浏览器）。"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_default_policy_matches_signed_off_strategy(monkeypatch):
    for k in ("REDNOTE_AUTO_RUN", "REDNOTE_AUTO_SCOPE", "REDNOTE_AUTO_SOURCE",
              "REDNOTE_AUTO_CADENCE_MINUTES", "REDNOTE_DAILY_LOGIN_KEEPALIVE",
              "REDNOTE_KIND_TOPIC", "REDNOTE_KIND_PUBLIC_OPINION",
              "REDNOTE_KIND_EVENT", "REDNOTE_PRIMARY_REGION", "REDNOTE_CN_PAUSED"):
        monkeypatch.delenv(k, raising=False)
    from lumenis.system.collector.adapters.rednote_policy import effective_policy
    p = effective_policy()
    assert p.primary_region == "intl" and p.cn_paused is True
    assert p.to_dict()["collection_account"] == "XHS_RETINAUT"
    assert p.to_dict()["collection_region"] == "intl"
    # 默认不自动跑真实平台（不撞熔断）
    assert p.auto_run_enabled is False and p.daily_login_keepalive is False
    # 三端：话题开、舆情笔记开、事件笔记关
    assert p.can_run_kind("topic") is True
    assert p.can_run_kind("public_opinion") is True
    assert p.can_run_kind("event") is False


def test_unknown_kind_denied_by_default(monkeypatch):
    from lumenis.system.collector.adapters.rednote_policy import effective_policy
    assert effective_policy().can_run_kind("something_else") is False


def test_env_overrides_are_explicit(monkeypatch):
    monkeypatch.setenv("REDNOTE_AUTO_RUN", "true")
    monkeypatch.setenv("REDNOTE_AUTO_SCOPE", "ALL_REGISTERED_SUBJECTS")
    monkeypatch.setenv("REDNOTE_AUTO_SOURCE", "rednote_hk")
    monkeypatch.setenv("REDNOTE_AUTO_CADENCE_MINUTES", "720")
    monkeypatch.setenv("REDNOTE_DAILY_LOGIN_KEEPALIVE", "true")
    monkeypatch.setenv("REDNOTE_KIND_EVENT", "true")
    from lumenis.system.collector.adapters.rednote_policy import effective_policy
    p = effective_policy()
    assert p.auto_run_enabled and p.daily_login_keepalive and p.can_run_kind("event")


def test_auto_run_flag_without_explicit_scope_source_and_cadence_stays_manual(monkeypatch):
    from lumenis.system.collector.adapters.rednote_policy import effective_policy

    monkeypatch.setenv("REDNOTE_AUTO_RUN", "true")
    monkeypatch.delenv("REDNOTE_AUTO_SCOPE", raising=False)
    monkeypatch.delenv("REDNOTE_AUTO_SOURCE", raising=False)
    monkeypatch.delenv("REDNOTE_AUTO_CADENCE_MINUTES", raising=False)
    assert effective_policy().auto_run_enabled is False


def test_auto_opt_in_rejects_scope_source_or_cadence_outside_current_scheduler(monkeypatch):
    from lumenis.system.collector.adapters.rednote_policy import effective_policy

    monkeypatch.setenv("REDNOTE_AUTO_RUN", "true")
    monkeypatch.setenv("REDNOTE_AUTO_SCOPE", "GLOBAL/ALL")
    monkeypatch.setenv("REDNOTE_AUTO_SOURCE", "rednote_hk")
    monkeypatch.setenv("REDNOTE_AUTO_CADENCE_MINUTES", "720")
    assert effective_policy().auto_run_enabled is False

    monkeypatch.setenv("REDNOTE_AUTO_SCOPE", "ALL_REGISTERED_SUBJECTS")
    monkeypatch.setenv("REDNOTE_AUTO_SOURCE", "xhs_cn")
    assert effective_policy().auto_run_enabled is False

    monkeypatch.setenv("REDNOTE_AUTO_SOURCE", "rednote_hk")
    monkeypatch.setenv("REDNOTE_AUTO_CADENCE_MINUTES", "90")
    assert effective_policy().auto_run_enabled is False


def test_mainland_pause_cannot_be_unlocked_by_runtime_env(monkeypatch):
    monkeypatch.setenv("REDNOTE_MAINLAND_ENABLE", "true")
    monkeypatch.setenv("REDNOTE_CN_PAUSED", "false")
    monkeypatch.setenv("REDNOTE_PRIMARY_REGION", "cn")
    from lumenis.system.collector.adapters.rednote_policy import effective_policy
    p = effective_policy()
    assert p.cn_paused is True
    assert p.to_dict()["mainland_opt_in"] is False


def test_production_gate_and_forced_route_remain_hk_only(monkeypatch):
    from lumenis.system.collector.adapters.rednote_policy import (
        collection_gate,
        effective_policy,
        select_region,
    )

    # Runtime configuration cannot re-enable the Product Owner's paused
    # Mainland account or redirect the production route to its local profile.
    monkeypatch.setenv("REDNOTE_PRIMARY_REGION", "cn")
    monkeypatch.setenv("REDNOTE_CN_PAUSED", "false")
    monkeypatch.setenv("REDNOTE_MAINLAND_ENABLE", "true")

    policy = effective_policy()
    allowed = collection_gate(account="XHS_RETINAUT", region="intl")
    mainland_account = collection_gate(account="XHS_CN_PRIMARY", region="cn")
    mainland_region = collection_gate(account="XHS_RETINAUT", region="cn")
    forced_mainland = select_region(force_region="cn")

    assert policy.cn_paused is True
    assert allowed["ok"] is True
    assert allowed["account"] == "XHS_RETINAUT"
    assert allowed["region"] == "intl"
    assert allowed["cdp_port"] is None
    assert allowed["host"] == "www.rednote.com"
    assert mainland_account["ok"] is False
    assert mainland_account["code"] == "account_paused"
    assert mainland_region["ok"] is False
    assert mainland_region["code"] == "region_paused"
    assert forced_mainland["blocked"] is True
    assert forced_mainland["requested_region"] == "cn"
    assert forced_mainland["region"] == "intl"
    assert forced_mainland["cdp_port"] is None
    assert forced_mainland["host"] == "www.rednote.com"


def test_human_cadence_marked_not_verified(monkeypatch):
    from lumenis.system.collector.adapters.rednote_policy import effective_policy, HUMAN_CADENCE_PLACEHOLDER
    # 真人频率在最新实测前必须显式标 NOT_VERIFIED，不得伪装实测值
    assert effective_policy().human_cadence["status"] == "NOT_VERIFIED"
    assert HUMAN_CADENCE_PLACEHOLDER["daily_login_keepalive"] == "once_per_day"


def test_auto_scope_is_all_registered_subjects_not_single_venue(monkeypatch):
    from lumenis.system.collector.adapters.rednote_policy import effective_policy

    monkeypatch.setenv("REDNOTE_AUTO_RUN", "true")
    monkeypatch.setenv("REDNOTE_AUTO_SOURCE", "rednote_hk")
    monkeypatch.setenv("REDNOTE_AUTO_CADENCE_MINUTES", "720")
    monkeypatch.setenv("REDNOTE_AUTO_SCOPE", "ALL_REGISTERED_SUBJECTS")
    assert effective_policy().auto_run_enabled is True
    # The single-venue legacy token is no longer the authorized scope.
    monkeypatch.setenv("REDNOTE_AUTO_SCOPE", "GUANGZHOU_TAIKOO_HUI")
    assert effective_policy().auto_run_enabled is False
