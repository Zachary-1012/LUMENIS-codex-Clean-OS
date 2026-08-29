"""本地部署健康检查。"""
from __future__ import annotations
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
URL = "http://127.0.0.1:8200/healthz"

print("=== Taikoo Monitor v5.6.3 Health Check ===")
print("Project:", ROOT)
print(".env:", (ROOT/'.env').exists())
print("DB:", (ROOT/'data'/'monitor.db').exists())
print("cloudflared:", bool(__import__('shutil').which('cloudflared')))
try:
    with urllib.request.urlopen(URL, timeout=5) as r:
        data=json.loads(r.read().decode('utf-8'))
    print("HTTP:", r.status)
    print("Health:", data)
except Exception as exc:
    print("HTTP: NOT RUNNING", exc)
