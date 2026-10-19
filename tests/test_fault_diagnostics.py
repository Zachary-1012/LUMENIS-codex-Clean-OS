"""Real subprocess checks for native-fault visibility and safe periodic dumps."""
import ast
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def run_probe(code, tmp_path):
    env = os.environ.copy()
    env['PYTHONPATH'] = str(ROOT) + os.pathsep + env.get('PYTHONPATH', '')
    return subprocess.run([sys.executable, '-c', code, str(tmp_path)],
                          env=env, cwd=ROOT, text=True, capture_output=True, timeout=15)


def test_app_keeps_fatal_and_periodic_diagnostics_without_native_watchdog():
    tree = ast.parse((ROOT / 'app.py').read_text())
    calls = [node.func for node in ast.walk(tree) if isinstance(node, ast.Call)]
    assert any(isinstance(call, ast.Name) and call.id == 'install_fault_diagnostics' for call in calls)
    assert not any(isinstance(call, ast.Attribute) and call.attr == 'dump_traceback_later' for call in calls)


def test_reload_reuses_worker_and_path_change_closes_previous_sink(tmp_path):
    result = run_probe('''
import faulthandler, pathlib, sys, threading
from lumenis.system.runtime import fault_diagnostics as d
root=pathlib.Path(sys.argv[1]); first=d.install_fault_diagnostics(str(root/'first.log'))
worker=d._current.thread
assert d._current.interval == 120.0
for _ in range(10):
 assert d.install_fault_diagnostics(str(root/'first.log')) is first
 assert d._current.thread is worker
assert faulthandler.is_enabled()
second=d.install_fault_diagnostics(str(root/'second.log'))
assert first.closed and not worker.is_alive()
assert second is not first and not second.closed
assert len([t for t in threading.enumerate() if t.name=='lumenis-fault-diagnostics'])==1
d.shutdown_fault_diagnostics(); d.shutdown_fault_diagnostics()
assert second.closed
assert not any(t.name=='lumenis-fault-diagnostics' for t in threading.enumerate())
''', tmp_path)
    assert result.returncode == 0, result.stderr


def test_periodic_dump_survives_live_recursive_frame_churn(tmp_path):
    result = run_probe('''
import pathlib,sys,threading,time,faulthandler
from lumenis.system.runtime.fault_diagnostics import FaultDiagnostics
root=pathlib.Path(sys.argv[1]); stop=threading.Event()
def rec(n):
 a=1; b=2; c=3
 if n: return rec(n-1)
def churn():
 while not stop.is_set(): rec(123)
t=threading.Thread(target=churn);t.start()
d=FaultDiagnostics(str(root/'periodic.log'), interval=.0001)
try:
 assert faulthandler.is_enabled()
 time.sleep(.3)
finally:
 stop.set();t.join();d.close()
text=(root/'periodic.log').read_text()
assert '[PeriodicDiagnostics]' in text and 'in rec' in text
assert d.file.closed and not d.thread.is_alive()
''', tmp_path)
    assert result.returncode == 0, result.stderr


def test_fatal_signal_still_produces_traceback(tmp_path):
    result = run_probe('''
import faulthandler,pathlib,sys
from lumenis.system.runtime.fault_diagnostics import install_fault_diagnostics
install_fault_diagnostics(str(pathlib.Path(sys.argv[1])/'fatal.log'))
faulthandler._sigsegv()
''', tmp_path)
    text = (tmp_path / 'fatal.log').read_text()
    if sys.platform == 'win32':
        assert result.returncode & 0xffffffff == 0xc0000005, result.stderr
        assert 'Windows fatal exception: access violation' in text
    else:
        assert result.returncode == -11, result.stderr
        assert 'Fatal Python error: Segmentation fault' in text
    assert '<module>' in text


def test_failed_replacement_preserves_live_fatal_sink(tmp_path):
    result = run_probe('''
import pathlib,sys,faulthandler
from lumenis.system.runtime import fault_diagnostics as d
root=pathlib.Path(sys.argv[1]); first=d.install_fault_diagnostics(str(root/'first.log'))
owner=d._current
try:
 d.install_fault_diagnostics(str(root/'missing'/'failed.log'))
 raise AssertionError('missing parent unexpectedly worked')
except FileNotFoundError: pass
assert d._current is owner and not first.closed and owner.thread.is_alive()
assert d._handler_owner is owner and faulthandler.is_enabled()
d.shutdown_fault_diagnostics()
''', tmp_path)
    assert result.returncode == 0, result.stderr


def test_retiring_old_instance_does_not_disable_new_fatal_sink(tmp_path):
    result = run_probe('''
import pathlib,sys,faulthandler
from lumenis.system.runtime import fault_diagnostics as d
root=pathlib.Path(sys.argv[1]); old=d.FaultDiagnostics(str(root/'old.log'))
new=d.FaultDiagnostics(str(root/'new.log'))
old.close()
assert old.file.closed and not new.file.closed
assert d._handler_owner is new and faulthandler.is_enabled()
new.close()
''', tmp_path)
    assert result.returncode == 0, result.stderr


def test_blocked_sink_close_is_bounded_and_defers_file_close(tmp_path):
    result = run_probe('''
import pathlib,sys,threading,time
from lumenis.system.runtime import fault_diagnostics as d
root=pathlib.Path(sys.argv[1]); entered=threading.Event();release=threading.Event()
real=d.faulthandler.dump_traceback
def blocked(**kwargs):
 entered.set();release.wait(5)
d.faulthandler.dump_traceback=blocked
owner=d.FaultDiagnostics(str(root/'blocked.log'),interval=.001)
assert entered.wait(3)
start=time.monotonic();owner.close();elapsed=time.monotonic()-start
assert elapsed<1.5 and owner.thread.is_alive() and not owner.file.closed
release.set();owner.thread.join(timeout=3)
assert not owner.thread.is_alive() and owner.file.closed
d.faulthandler.dump_traceback=real
''', tmp_path)
    assert result.returncode == 0, result.stderr
