"""Registry publication is atomic and failed imports remain retryable."""
import builtins
from concurrent.futures import ThreadPoolExecutor


def test_import_failure_can_recover(monkeypatch):
    import experience_runtime as runtime
    monkeypatch.setattr(runtime, '_PROPAGATION_LOADED', False)
    monkeypatch.setattr(runtime, '_BUILDERS', {'CTH-01': runtime._build_cth01,
                                             'AI-01': runtime._build_ai01})
    original = builtins.__import__
    def fail(name, *args, **kwargs):
        if name == 'experience_screens':
            raise ImportError('controlled test failure')
        return original(name, *args, **kwargs)
    with monkeypatch.context() as scoped:
        scoped.setattr(builtins, '__import__', fail)
        assert len(runtime._all_builders()) == 2
        assert not runtime._PROPAGATION_LOADED
    with ThreadPoolExecutor(max_workers=8) as pool:
        counts = list(pool.map(lambda _: len(runtime._all_builders()), range(16)))
    assert counts == [44] * 16
    assert runtime._PROPAGATION_IMPORT_ERROR == ''
