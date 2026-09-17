# -*- coding: utf-8 -*-
"""通用主体模块与香港 Cookie 绑定的隔离验收。"""
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def test_subject_registry_supports_both_domains_and_open_industry(tmp_path, monkeypatch):
    db_path = tmp_path / "subjects.db"
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))
    from subject_registry import add_subject, list_subjects

    cth, created = add_subject({
        "domain_id": "cth",
        "subject_type": "company",
        "name_en": "North Star Labs",
        "name_zh": "北辰实验室",
        "industry": "工业软件",
        "keywords": ["North Star", "北辰"],
    })
    assert created is True
    assert cth["domain_id"] == "CTH"
    assert cth["subject_type"] == "company"
    assert cth["industry"] == "工业软件"
    assert cth["keywords"] == ["North Star", "北辰"]

    bmp, created = add_subject({
        "domain_id": "zbmp",
        "subject_type": "品牌主体",
        "name_en": "North Star Labs",
        "name_zh": "北辰实验室",
        "industry": "",
    })
    assert created is True
    assert bmp["domain_id"] == "BMP"
    assert bmp["subject_type"] == "brand"
    assert {x["domain_id"] for x in list_subjects()} == {"CTH", "BMP"}

    duplicate, created = add_subject({
        "domain_id": "CTH",
        "subject_type": "company",
        "name_en": " north   star labs ",
        "name_zh": "北辰实验室",
    })
    assert created is False
    assert duplicate["subject_id"] == cth["subject_id"]


def test_subject_registry_requires_bilingual_names(tmp_path, monkeypatch):
    monkeypatch.setenv("ZBC_DB_PATH", str(tmp_path / "subjects.db"))
    from subject_registry import SubjectValidationError, add_subject

    with pytest.raises(SubjectValidationError, match="name_en 与 name_zh"):
        add_subject({"domain_id": "CTH", "subject_type": "brand", "name_en": "Only English"})


def test_hk_cookie_apply_targets_hk_profile_and_rejects_cn(tmp_path, monkeypatch):
    import app as app_module
    import xhs_cookie_bridge as bridge

    runtime_data = tmp_path / "runtime-data"
    hk_cookie = runtime_data / "private" / "xhs_cookie_retinaut.txt"
    cn_cookie = runtime_data / "private" / "xhs_cookie_header.txt"
    monkeypatch.setattr(bridge, "DATA_DIR", str(runtime_data))
    monkeypatch.setitem(bridge.ACCOUNT_PROFILES, bridge.DEFAULT_COLLECTION_ACCOUNT,
                        (str(hk_cookie), str(runtime_data / "profiles" / "hk")))

    payload = {
        "platform": "xhs",
        "account": bridge.DEFAULT_COLLECTION_ACCOUNT,
        "apply": True,
        "cookies": [{"name": "web_session", "value": "real-session-value", "domain": ".rednote.com"}],
    }
    with app_module.app.test_request_context("/api/cookies/import/raw", method="POST", json=payload):
        response = app_module.api_cookies_import_raw()
    body = response.get_json()
    assert response.status_code == 200
    assert body["applied"] is True
    assert body["account"] == bridge.DEFAULT_COLLECTION_ACCOUNT
    assert body["secrets_returned"] is False
    assert hk_cookie.read_text(encoding="utf-8") == "web_session=real-session-value"
    assert not cn_cookie.exists()

    payload["account"] = bridge.XHS_CN_PRIMARY_NAME
    with app_module.app.test_request_context("/api/cookies/import/raw", method="POST", json=payload):
        response = app_module.api_cookies_import_raw()
    response_body, response_status = response
    assert response_status == 403
    assert response_body.get_json()["code"] == "MAINLAND_COLLECTION_DISABLED"


def test_active_resident_plan_and_orchestrator_are_hk_only():
    import scripts.start_resident_browsers as resident
    import xhs_cookie_bridge as bridge
    import xhs_p0_orchestrator as orchestrator

    plan_accounts = {account for account, _ in resident.RESIDENT_PLAN}
    assert plan_accounts == {bridge.DEFAULT_COLLECTION_ACCOUNT}
    assert bridge.XHS_CN_PRIMARY_NAME not in plan_accounts
    assert orchestrator.ALLOWED_IDENTITY_NAMES == (bridge.DEFAULT_COLLECTION_ACCOUNT,)
    assert orchestrator._identity_allowed(bridge.XHS_CN_PRIMARY_NAME) is False
    assert orchestrator._identity_allowed(bridge.DEFAULT_COLLECTION_ACCOUNT) is True
