# -*- coding: utf-8 -*-
"""验证 CollectorGuard 接入逻辑：健康透传 + 显式风控熔断后不再调用采集函数。"""
import io, os, sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from lumenis.system.collector.guard.guard import CollectorGuard
from lumenis.system.collector.guard.state import CollectState

import tempfile
from pathlib import Path
from lumenis.shared.database import registry
from unittest.mock import patch


def main():
    # Both metrics and checkpoints must stay in the disposable test root.
    with tempfile.TemporaryDirectory(prefix='guard-wiring-') as temp_root:
        with patch.dict(os.environ, {'ZBC_DATA_DIR': temp_root}), \
                patch.object(registry, '_registry', registry.RepositoryRegistry()):
            fails = []
            def ck(n, c, x=''):
                print(('PASS' if c else 'FAIL'), n, x)
                if not c: fails.append(n)

            g = CollectorGuard('xiaohongshu', enabled=True, base_interval=0, checkpoint_dir=os.path.join(temp_root, 'checkpoints'))  # 0间隔，测试不等

            assert Path(g.metrics._persist_path).resolve().is_relative_to(Path(temp_root).resolve())
            assert Path(g.checkpoint.path).resolve().is_relative_to(Path(temp_root).resolve())

            # 1 健康：透传 notes
            calls = {'n': 0}
            def ok_fn():
                calls['n'] += 1
                return {'notes': [{'note_id': 'a'}, {'note_id': 'b'}], 'error': '', 'total': 2}
            r = g.run(ok_fn, 'kw1')
            ck('健康态ok', r.ok and r.state == CollectState.HEALTHY and len(r.notes) == 2, r.state)
            ck('健康确实调用1次', calls['n'] == 1, str(calls))

            # 2 显式 NEED_VERIFY -> 受控暂停
            def verify_fn():
                calls['n'] += 1
                return {'notes': [], 'error': 'NEED_VERIFY'}
            r2 = g.run(verify_fn, 'kw2')
            ck('验证码->NEED_VERIFY且should_stop', r2.state == CollectState.NEED_VERIFY and r2.should_stop, r2.state)

            # 3 熔断后再次 run：采集函数不应再被调用（停止危险请求）
            before = calls['n']
            r3 = g.run(ok_fn, 'kw3')
            ck('熔断后不再发请求', calls['n'] == before, f'before={before} after={calls["n"]}')
            ck('熔断后直接返回受控态', r3.should_stop and r3.state in CollectState.STOP_REQUEST, r3.state)

            # 4 disabled 直通
            gd = CollectorGuard('x', enabled=False, checkpoint_dir=os.path.join(temp_root, 'checkpoints'))
            rd = gd.run(lambda: {'notes': [{'note_id': 'z'}], 'error': ''}, 'k')
            ck('关闭时直通健康', rd.ok and len(rd.notes) == 1)

            print('\nGuard接入逻辑:', '全部通过' if not fails else f'{len(fails)}失败 {fails}')
            return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
