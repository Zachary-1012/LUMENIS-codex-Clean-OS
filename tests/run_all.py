# -*- coding: utf-8 -*-
"""Z-Brand-Core 统一测试入口（GAP-01）。

分层执行，替代过去十几个零散启动命令：

  python tests/run_all.py            # 阶段A：仅规范 pytest 用例（含 def test_ 的文件，CI/默认）
  python tests/run_all.py --scripts  # 阶段A + 阶段B：纯脚本式以【子进程隔离】逐个运行，
                                     #   真实平台/网络副作用互不污染、单脚本超时不拖垮整体
  python tests/run_all.py --online   # 阶段A 同时放开 online 标记用例（默认跳过需真实平台的用例）

退出码：阶段A 失败=1；阶段B 失败默认仅汇总不阻塞（--strict-scripts 时返回 1）。
"""
import argparse
import glob
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
SCRIPT_TIMEOUT = 120


def list_script_style():
    """纯脚本式 test_ 文件：全文无 def test_（默认被 conftest 钩子忽略收集）。"""
    out = []
    for p in sorted(glob.glob(os.path.join(ROOT, 'test_*.py'))):
        txt = open(p, encoding='utf-8', errors='replace').read()
        if not re.search(r'^\s*def test_', txt, re.M):
            out.append(p)
    return out


def stage_a_pytest(online: bool) -> int:
    import pytest
    args = [ROOT, '-q', '-p', 'no:cacheprovider']
    if not online:
        args += ['-m', 'not online']
    print('\n========== 阶段A：规范 pytest 用例 ==========')
    return pytest.main(args)


def stage_b_scripts() -> int:
    scripts = list_script_style()
    print(f'\n========== 阶段B：脚本式子进程隔离（{len(scripts)} 个，超时 {SCRIPT_TIMEOUT}s）==========')
    passed, failed, timed = [], [], []
    for p in scripts:
        name = os.path.basename(p)
        try:
            r = subprocess.run([PY, p], cwd=os.path.dirname(ROOT),
                               capture_output=True, text=True, timeout=SCRIPT_TIMEOUT,
                               encoding='utf-8', errors='replace')
            (passed if r.returncode == 0 else failed).append(name)
            if r.returncode != 0:
                tail = (r.stderr or r.stdout or '')[-400:]
                print(f'  FAIL {name}\n{tail}')
        except subprocess.TimeoutExpired:
            timed.append(name)
            print(f'  TIMEOUT {name}')
    print(f'\n阶段B 汇总：PASS {len(passed)} / FAIL {len(failed)} / TIMEOUT {len(timed)}')
    if failed:
        print('  失败：', ', '.join(failed))
    if timed:
        print('  超时：', ', '.join(timed))
    return 1 if (failed or timed) else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--scripts', action='store_true', help='额外子进程跑纯脚本式')
    ap.add_argument('--online', action='store_true', help='放开需真实网络/平台的 online 用例')
    ap.add_argument('--strict-scripts', action='store_true', help='阶段B 失败也返回非零')
    a = ap.parse_args()

    rc_a = stage_a_pytest(a.online)
    rc_b = stage_b_scripts() if a.scripts else 0

    print('\n================ 统一入口结论 ================')
    print(f'阶段A 规范用例: {"PASS" if rc_a == 0 else "FAIL"}'
          + (f' | 阶段B 脚本: {"PASS" if rc_b == 0 else "FAIL/TIMEOUT"}' if a.scripts else ' | 阶段B 未运行(加 --scripts)'))
    if rc_a != 0:
        return 1
    if a.scripts and a.strict_scripts and rc_b != 0:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
