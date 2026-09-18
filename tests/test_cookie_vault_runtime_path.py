"""Cookie Vault runtime-root tests; all files stay under pytest tmp_path."""
from __future__ import annotations

import json


def test_cookie_vault_follows_runtime_data_dir_without_reimport(monkeypatch, tmp_path):
    from lumenis.adapters import cookie_vault

    runtime_root = tmp_path / "protected-runtime"
    cookie_dir = runtime_root / "cookies"
    cookie_dir.mkdir(parents=True)
    cookie_file = cookie_dir / "douyin.json"
    cookie_file.write_text(json.dumps([{"name": "sessionid", "value": "fixture"}]), encoding="utf-8")

    monkeypatch.setenv("ZBC_DATA_DIR", str(runtime_root))
    monkeypatch.delenv("ZBC_DB_PATH", raising=False)

    assert cookie_vault._resolve_path("douyin") == cookie_file.resolve()
    assert cookie_vault.load_cookies("douyin")[0]["name"] == "sessionid"
