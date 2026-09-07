# -*- coding: utf-8 -*-
"""临时 hang 看门狗：用例运行超阈值时连续 dump 全部线程栈，定位死锁/持GIL阻塞。跑完即删。
用 `pytest -p hangwatch`，PYTHONPATH 含项目根。"""
import threading, time, faulthandler, os, sys
_OUT = open(os.path.join(os.environ.get('TEMP', '/tmp'), 'zbc_hang_dump.log'),
            'w', encoding='utf-8')
_state = {'node': None, 'start': 0.0, 'dumped': 0}
_lock = threading.Lock()

def _watch():
    while True:
        time.sleep(1.0)
        with _lock:
            node = _state['node']; st = _state['start']; dumped = _state['dumped']
            if node is None:
                continue
            el = time.time() - st
            if el > 8 and dumped < 5:
                _state['dumped'] += 1
                _OUT.write('\n\n########## HANG SNAPSHOT #%d elapsed=%.1fs node=%s ##########\n'
                           % (_state['dumped'], el, node))
                _OUT.flush()
                faulthandler.dump_traceback(file=_OUT, all_threads=True)
                _OUT.flush()

_t = threading.Thread(target=_watch, name='hangwatch', daemon=True)
_t.start()

import pytest

@pytest.fixture(autouse=True)
def _hang_mark(request):
    with _lock:
        _state['node'] = request.node.nodeid
        _state['start'] = time.time()
        _state['dumped'] = 0
    yield
    with _lock:
        _state['node'] = None

def pytest_sessionfinish(session, exitstatus):
    try:
        _OUT.write('\n=== session finish exit=%s ===\n' % exitstatus)
        _OUT.close()
    except Exception:
        pass
