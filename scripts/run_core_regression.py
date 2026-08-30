# -*- coding: utf-8 -*-
"""Z-Brand Core 核心回归 runner（提交前 / 定时同步前必跑）。

纯子进程方式顺序执行核心口径测试，输出每个文件退出码与结论。
覆盖：数据库、六态、采集韧性、风险、发布时间、报告周期、安全边界、
标题兜底、动态调度、广州太古汇主体红线。用法：.venv\\Scripts\\python.exe scripts\\run_core_regression.py
"""
import io, os, subprocess, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = os.path.join(ROOT, '.venv', 'Scripts', 'python.exe')
FILES = [
    'test_database', 'test_collect_state', 'test_guard_wiring', 'test_risk_engine',
    'test_event_date', 'test_report_periods', 'test_safety_boundary', 'test_title_fallback',
    'test_scheduling', 'test_subject_redline',
]


def main():
    summary = []
    for f in FILES:
        path = os.path.join(ROOT, 'tests', f + '.py')
        if not os.path.exists(path):
            summary.append((f, 'MISSING', 'file not found'))
            print(f'[{f}] MISSING')
            continue
        try:
            r = subprocess.run([PY, path], cwd=ROOT, capture_output=True, text=True,
                               encoding='utf-8', errors='replace', timeout=180)
            lines = [x.strip() for x in (r.stdout or '').splitlines() if x.strip()]
            tail = lines[-1] if lines else '(no stdout)'
            summary.append((f, r.returncode, tail))
            print(f'[{f}] rc={r.returncode} :: {tail[:140]}')
            if r.returncode != 0:
                for e in (r.stderr or '').strip().splitlines()[-3:]:
                    print('    ERR:', e[:180])
        except subprocess.TimeoutExpired:
            summary.append((f, 'TIMEOUT', '>180s'))
            print(f'[{f}] TIMEOUT >180s')
    print('\n==== SUMMARY ====')
    bad = 0
    for f, rc, _ in summary:
        ok = (rc == 0)
        bad += 0 if ok else 1
        print(f'{"PASS" if ok else "FAIL"}  {f}  rc={rc}')
    total = len(summary)
    print(f'CORE_REGRESSION: {total-bad}/{total} pass, {bad} fail')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
