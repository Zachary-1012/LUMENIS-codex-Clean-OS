# -*- coding: utf-8 -*-
import base64
import json
import os
import subprocess
import sys


def test_runtime_identity_http_contract_isolated(tmp_path):
    db_path = tmp_path / "runtime-http.db"
    env = dict(os.environ)
    env.update(
        {
            "ZBC_DB_PATH": str(db_path),
            "ZBC_TEST_OFFLINE": "1",
            "TAIKOO_AUTH_USER": "runtime-test-owner",
            "TAIKOO_AUTH_PASSWORD": "runtime-test-password",
            "LUMENIS_PRODUCT_MODE": "CUSTOMER_RELEASE",
        }
    )
    token = base64.b64encode(b"runtime-test-owner:runtime-test-password").decode("ascii")
    code = f"""
import json
import app
c = app.app.test_client()
public = c.get('/healthz')
foundation = c.get('/lumenis/healthz')
anonymous = c.get('/api/runtime/attestation')
controlled = c.get('/api/runtime/attestation', headers={{'Authorization': 'Basic {token}'}})
print(json.dumps({{
    'public_code': public.status_code,
    'public': public.get_json(),
    'foundation_code': foundation.status_code,
    'foundation': foundation.get_json(),
    'anonymous_code': anonymous.status_code,
    'controlled_code': controlled.status_code,
    'controlled': controlled.get_json(),
}}, ensure_ascii=False))
"""
    run = subprocess.run(
        [sys.executable, "-c", code],
        cwd=os.path.dirname(os.path.dirname(__file__)),
        env=env,
        capture_output=True,
        text=True,
        timeout=90,
        check=True,
    )
    payload = json.loads(run.stdout.strip().splitlines()[-1])

    assert payload["public_code"] == 200
    assert payload["foundation_code"] == 200
    assert payload["anonymous_code"] == 401
    assert payload["controlled_code"] == 200
    public_identity = payload["public"]["runtime_identity"]
    full_identity = payload["controlled"]["runtime_identity"]
    assert public_identity["identity_schema"] == "lumenis.runtime-identity.v1"
    assert public_identity["product_mode"] == "CUSTOMER_RELEASE"
    assert "database" not in public_identity
    assert full_identity["database"]["exists"] is True
    assert str(db_path) not in json.dumps(payload, ensure_ascii=False)
