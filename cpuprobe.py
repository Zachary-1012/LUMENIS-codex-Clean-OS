# -*- coding: utf-8 -*-
"""临时 CPU/线程诊断插件：每用例后测 pbkdf2(10000) 耗时，慢则记录存活线程，定位忙等线程。
跑完即删。用 `pytest -p cpuprobe` 加载（本文件需在 rootdir 可 import）。"""
import hashlib, threading, time, json, os, collections
_OUT = os.path.join(os.environ.get('TEMP', '/tmp'), 'zbc_cpu_probe.jsonl')

def _pbkdf_ms():
    t = time.perf_counter()
    hashlib.pbkdf2_hmac('sha256', b'probe', b'salt', 10000)
    return (time.perf_counter() - t) * 1000.0

import pytest

@pytest.fixture(autouse=True)
def _cpu_probe(request):
    yield
    try:
        ms = _pbkdf_ms()
        names = collections.Counter(t.name for t in threading.enumerate())
        rec = {'node': request.node.nodeid, 'pbkdf_ms': round(ms, 1),
               'n_threads': len(names), 'threads': dict(names)}
        # 慢于 300ms 视为 CPU 被挤占；前两次也记录建立基线
        if ms > 300.0 or getattr(_cpu_probe, 'n', 0) < 2:
            with open(_OUT, 'a', encoding='utf-8') as f:
                f.write(json.dumps(rec, ensure_ascii=False) + '\n')
        _cpu_probe.n = getattr(_cpu_probe, 'n', 0) + 1
        if ms > 300.0:
            _cpu_probe.slow = getattr(_cpu_probe, 'slow', 0) + 1
    except Exception:
        pass

def pytest_sessionstart(session):
    open(_OUT, 'w', encoding='utf-8').close()

def pytest_sessionfinish(session, exitstatus):
    try:
        with open(_OUT, 'a', encoding='utf-8') as f:
            f.write(json.dumps({'session_done': True, 'slow_total': getattr(_cpu_probe, 'slow', 0)},
                               ensure_ascii=False) + '\n')
    except Exception:
        pass
