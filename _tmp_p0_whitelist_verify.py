# -*- coding: utf-8 -*-
"""_tmp_p0_whitelist_verify.py — 双子星库 Contract 双身份白名单 3+3 断言单元验证。

3 条必过断言 (Acceptance Matrix 条目 1 + 9):
  T1. PRIMARY 身份 select_account 成功，且 cookie_configured 为 True
  T2. 非白身份 "XHS_FAKE_HACKER" select_account 明确返回 False（不崩溃）
  T3. RETINAUT=None 配置 select_account 返回详细错误（不崩溃，友好错误）

运行方式：
  .venv\Scripts\python.exe _tmp_p0_whitelist_verify.py
输出：PASS / FAIL + 每步证据链
"""
import os, sys, json, traceback

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
# 先清任何残留 override，保持测试纯净
for k in ('XHS_COOKIE_FILE_OVERRIDE','XHS_TEST_MODE'):
    os.environ.pop(k, None)

# 只导入常量/函数，不触发 DB
import xhs_cookie_bridge as xcb

def run():
    failed = 0; passed = 0; ev = []

    # ── 0. 常量 Contract 审计 ──
    try:
        assert hasattr(xcb, 'XHS_CN_PRIMARY_NAME') and xcb.XHS_CN_PRIMARY_NAME == 'XHS_CN_PRIMARY'
        assert hasattr(xcb, 'XHS_RETINAUT_NAME') and xcb.XHS_RETINAUT_NAME == 'XHS_RETINAUT'
        assert hasattr(xcb, 'ALLOWED_USER_IDS') and isinstance(xcb.ALLOWED_USER_IDS, tuple)
        assert hasattr(xcb, 'ALLOWED_USER_ID') and xcb.ALLOWED_USER_ID == xcb.XHS_CN_PRIMARY  # LEGACY
        assert hasattr(xcb, 'ACCOUNT_PROFILES') and isinstance(xcb.ACCOUNT_PROFILES, dict)
        assert xcb.XHS_CN_PRIMARY_NAME in xcb.ACCOUNT_PROFILES
        assert xcb.XHS_RETINAUT_NAME in xcb.ACCOUNT_PROFILES
        assert hasattr(xcb, '_ACTIVE_ACCOUNT') and xcb._ACTIVE_ACCOUNT is None  # 初始 None
        if xcb.XHS_RETINAUT is None:
            assert len(xcb.ALLOWED_USER_IDS) == 1, f"RETINAUT=None 时 ALLOWED_USER_IDS 应为 len=1，实际={xcb.ALLOWED_USER_IDS}"
        else:
            assert len(xcb.ALLOWED_USER_IDS) == 2
        passed += 1; ev.append("[CONST ✓] 双子星库 Contract 常量齐全 (双身份/tuple/ACCOUNT_PROFILES/LEGACY alias)")
    except AssertionError as e:
        failed += 1; ev.append(f"[CONST ✗] {e}\n{traceback.format_exc()}")

    # ── T1. PRIMARY 身份切换 + verify_account ──
    try:
        ok1, msg1 = xcb.select_account(xcb.XHS_CN_PRIMARY_NAME)
        assert ok1, f"PRIMARY select_account 失败: {msg1}"
        assert xcb._ACTIVE_ACCOUNT == xcb.XHS_CN_PRIMARY_NAME
        assert 'XHS_COOKIE_FILE_OVERRIDE' in os.environ
        assert xcb.cookie_configured() is True
        # 白名单校验：PRIMARY real user_id ∈ ALLOWED_USER_IDS
        ok_ver, msg_ver = xcb.verify_account()
        assert ok_ver, f"PRIMARY verify_account 失败: {msg_ver}"
        passed += 1; ev.append(f"[T1 ✓] PRIMARY 身份激活成功 | {msg1} | verify_account PASS")
    except AssertionError as e:
        failed += 1; ev.append(f"[T1 ✗] {e}\n{traceback.format_exc()}")

    # ── T2. 非白身份 → 明确拒绝（绝不静默降级）──
    try:
        ok2, msg2 = xcb.select_account("XHS_FAKE_HACKER")
        assert not ok2, "非白身份应被拒绝，但 select_account 返回 True"
        assert "不在双子星库 Contract 硬白名单中" in msg2
        assert xcb.XHS_CN_PRIMARY_NAME in msg2 and xcb.XHS_RETINAUT_NAME in msg2
        passed += 1; ev.append(f"[T2 ✓] 非白身份 XHS_FAKE_HACKER 明确拒绝 | 原因: {msg2[:80]}...")
    except AssertionError as e:
        failed += 1; ev.append(f"[T2 ✗] {e}\n{traceback.format_exc()}")

    # ── T3. RETINAUT 未配置 → 友好错误（不崩溃）──
    try:
        ok3, msg3 = xcb.select_account(xcb.XHS_RETINAUT_NAME)
        if xcb.XHS_RETINAUT is None:
            assert not ok3, "RETINAUT=None 时应返回配置缺失错误"
            assert ("尚未配置" in msg3) or ("Cookie 文件不存在" in msg3)
            ev.append(f"[T3 ✓] RETINAUT=None 未配置友好错误（预期）| 原因: {msg3[:100]}...")
        else:
            # 用户已配置 RETINAUT → 正常检查 cookie 文件
            if ok3:
                ev.append(f"[T3 ✓] RETINAUT 已配置并成功激活 | {msg3[:100]}")
            else:
                # cookie 文件未导入等正常友好错误
                assert ("Cookie 文件不存在" in msg3) or ("尚未配置" in msg3)
                ev.append(f"[T3 ✓] RETINAUT cookie 文件未导入友好错误 | {msg3[:100]}")
        passed += 1
    except AssertionError as e:
        failed += 1; ev.append(f"[T3 ✗] {e}\n{traceback.format_exc()}")

    # ── T4. sync() 返回 identity evidence 字段 ──
    # 不真实跑 sync（会触发真实网络 BLOCKED），只 import + 用 inspect 查 signature
    try:
        import inspect
        sig = inspect.signature(xcb.sync)
        params = list(sig.parameters.keys())
        assert 'account' in params, f"sync 签名应包含 account 参数，实际={params}"
        # 默认 None（向后兼容）
        assert sig.parameters['account'].default is None
        passed += 1; ev.append(f"[T4 ✓] sync(account=None) signature OK，默认 None 向后兼容 | params={params}")
    except AssertionError as e:
        failed += 1; ev.append(f"[T4 ✗] {e}\n{traceback.format_exc()}")

    # ── T5. LEGACY ALLOWED_USER_ID 调用点兼容（模拟旧代码写 xcb.ALLOWED_USER_ID == id）──
    try:
        primary_id = xcb.XHS_CN_PRIMARY
        # 模拟旧代码：cb.ALLOWED_USER_ID != current_id (Phase A2 verify_account 兼容写法)
        assert isinstance(xcb.ALLOWED_USER_ID, str) and len(xcb.ALLOWED_USER_ID) > 10
        assert primary_id == xcb.ALLOWED_USER_ID
        # 模拟旧代码 tuple in
        assert primary_id in xcb.ALLOWED_USER_IDS
        passed += 1; ev.append(f"[T5 ✓] LEGACY ALLOWED_USER_ID 兼容 (只读 alias PRIMARY) + tuple in OK")
    except AssertionError as e:
        failed += 1; ev.append(f"[T5 ✗] {e}\n{traceback.format_exc()}")

    # ── T6. get_account_status 新增字段存在 ──
    try:
        st = xcb.get_account_status()
        assert isinstance(st, dict), f"get_account_status 应返回 dict，实际={type(st)}"
        for k in ('active_account','active_cookie_file','allowed_user_ids','allowed_accounts'):
            assert k in st, f"get_account_status 缺 A2 新增字段 {k}，实际 keys={list(st.keys())}"
        assert st['active_account'] == xcb.XHS_CN_PRIMARY_NAME  # T1 刚切
        assert xcb.XHS_CN_PRIMARY_NAME in st['allowed_accounts']
        assert xcb.XHS_RETINAUT_NAME in st['allowed_accounts']
        passed += 1; ev.append(f"[T6 ✓] get_account_status 4 个 A2 字段齐全 | active={st['active_account']} allowed={st['allowed_accounts']}")
    except AssertionError as e:
        failed += 1; ev.append(f"[T6 ✗] {e}\n{traceback.format_exc()}")

    # ── 结果汇总 ──
    total = passed + failed
    print("\n" + "="*80)
    print(f"  _tmp_p0_whitelist_verify.py — 双子星库 Contract 白名单单元验证")
    print(f"  结果: {'PASS ✓' if failed==0 else 'FAIL ✗'}  (PASSED={passed}/{total}, FAILED={failed}/{total})")
    print("="*80)
    for line in ev:
        print("  • " + line)
    print("="*80 + "\n")
    sys.exit(0 if failed==0 else 1)

if __name__ == '__main__':
    run()
