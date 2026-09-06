# -*- coding: utf-8 -*-
"""Update subject_rules.py get_active_brand to check thread context first."""
fp = r'D:\Taikoo-monitor-new\subject_rules.py'

with open(fp, 'r', encoding='utf-8') as f:
    content = f.read()

old = '''def get_active_brand() -> str:
    """获取当前激活品牌key。

    V2 P0-19: 委托给 SubjectContext 管理主体边界。
    active_brand 不再承担系统数据边界职责，仅作为兼容层返回 brand_key。
    真实的主体边界由 subject_context.get_subject_context() 统一管理。
    """
    try:
        from subject_context import get_subject_context
        return get_subject_context().brand_key
    except Exception:
        import os
        return os.environ.get("ZBC_ACTIVE_BRAND", ACTIVE_BRAND)'''

new = '''def get_active_brand() -> str:
    """获取当前激活品牌key。

    V2 P0-19: 委托给 SubjectContext 管理主体边界。
    active_brand 不再承担系统数据边界职责，仅作为兼容层返回 brand_key。
    真实的主体边界由 subject_context.get_subject_context() 统一管理。

    优先级（Shard D 请求级隔离）：
      1. 线程级 SubjectContext（由 Flask before_request 或 brand_scope 设置）
      2. 环境变量 ZBC_ACTIVE_BRAND
      3. CTH 默认 guangzhou_taikoo_hui
    """
    try:
        from subject_context import get_thread_context, get_subject_context
        ctx = get_thread_context()
        if ctx is not None:
            return ctx.brand_key
        return get_subject_context().brand_key
    except Exception:
        import os
        return os.environ.get("ZBC_ACTIVE_BRAND", ACTIVE_BRAND)'''

if old in content:
    content = content.replace(old, new)
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(content)
    print('[OK] Updated get_active_brand in subject_rules.py')
else:
    print('[FAIL] Could not find old function text')
    # Try to find it
    import re
    m = re.search(r'def get_active_brand.*?(?=\ndef )', content, re.DOTALL)
    if m:
        print(f'Found function at pos {m.start()}-{m.end()}')
        print(repr(m.group()[:200]))

# Verify compile
import py_compile
try:
    py_compile.compile(fp, doraise=True)
    print('[OK] subject_rules.py compiles')
except Exception as e:
    print(f'[FAIL] compile error: {e}')
