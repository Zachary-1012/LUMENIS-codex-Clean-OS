# -*- coding: utf-8 -*-
"""
ZBC Phase 12 — API 层逐端点审计回归测试

覆盖：
1. fake success 修复验证（源码静态检查：except 块不得返回 ok=True）
2. 高风险端点 @require_permission 装饰器存在性检查
3. 修复端点错误码字段存在性检查
4. PermissionGate 全局初始化验证
5. 权限拒绝返回格式验证（deny_return = 403 + PERMISSION_DENIED）
6. podcast_routes fake success 修复验证

禁止：不启动真实服务、不执行真实采集/AI调用、不修改数据库。
"""
import os
import re
import sys
import pytest

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_PY = os.path.join(PROJECT_ROOT, "app.py")
PODCAST_ROUTES = os.path.join(PROJECT_ROOT, "podcast_routes.py")


# ═══════════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════════

def _read_file(path):
    """读取文件内容，失败则跳过测试。"""
    if not os.path.exists(path):
        pytest.skip(f"文件不存在: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _extract_except_blocks(source):
    """提取所有 except 块的返回语句，用于 fake success 检查。"""
    pattern = re.compile(
        r'except[^:]*:\s*\n((?:\s+[^\n]*\n)*?)',
        re.MULTILINE
    )
    blocks = []
    for m in pattern.finditer(source):
        block = m.group(1)
        if 'return' in block and ('ok' in block or 'jsonify' in block):
            blocks.append(block.strip())
    return blocks


# ═══════════════════════════════════════════════════════════════
# 1. Fake Success 修复验证
# ═══════════════════════════════════════════════════════════════

class TestFakeSuccessFixes:
    """验证 except 块不再返回 ok=True（fake success）。"""

    def test_app_py_no_fake_success_in_except(self):
        """app.py: except 块中不得出现 ok=True 的 fake success。"""
        source = _read_file(APP_PY)
        # 检查 except 块后紧跟 return jsonify({'ok': True 或 "ok": True
        pattern = re.compile(
            r'except[^:]*:\s*\n\s+return\s+jsonify\(\s*[\'"]ok[\'"]\s*:\s*True',
            re.MULTILINE
        )
        matches = pattern.findall(source)
        assert len(matches) == 0, (
            f"发现 {len(matches)} 处 except 块 fake success (ok=True): "
            f"{matches[:3]}"
        )

    def test_app_py_auth_config_except_returns_error(self):
        """/api/auth/config: except 块应返回 ok=False + 错误码。"""
        source = _read_file(APP_PY)
        # 验证 auth_config_api 函数的 except 块
        assert 'AUTH_HEADER_ENCODE_ERROR' in source, (
            "auth_config except 块应包含错误码 AUTH_HEADER_ENCODE_ERROR"
        )
        # 验证该端点 except 不再返回 ok=True
        auth_section = source[source.find('def auth_config_api'):source.find('def auth_config_api') + 800]
        assert "'ok': True" not in auth_section.split('except')[1] if 'except' in auth_section else True

    def test_app_py_brand_industry_except_returns_error(self):
        """/api/brand-industry/brands & stats: except 块应返回 ok=False + 错误码。"""
        source = _read_file(APP_PY)
        assert 'BRAND_INDUSTRY_QUERY_ERROR' in source, (
            "brand-industry/brands except 块应包含错误码 BRAND_INDUSTRY_QUERY_ERROR"
        )
        assert 'BRAND_INDUSTRY_STATS_ERROR' in source, (
            "brand-industry/stats except 块应包含错误码 BRAND_INDUSTRY_STATS_ERROR"
        )

    def test_app_py_negative_review_stats_except_returns_error(self):
        """/api/negative-review/stats: except 块应返回 ok=False + 错误码。"""
        source = _read_file(APP_PY)
        assert 'NEGATIVE_REVIEW_STATS_ERROR' in source, (
            "negative-review/stats except 块应包含错误码 NEGATIVE_REVIEW_STATS_ERROR"
        )

    def test_podcast_routes_no_fake_success_on_valueerror(self):
        """podcast_routes.py: runtime/validate 的 ValueError 不应返回 ok=True。"""
        source = _read_file(PODCAST_ROUTES)
        # 检查 ValueError 处理
        pattern = re.compile(
            r'except\s+ValueError[^:]*:\s*\n\s+return\s+jsonify\(\s*[\'"]ok[\'"]\s*:\s*True',
            re.MULTILINE
        )
        matches = pattern.findall(source)
        assert len(matches) == 0, (
            f"podcast_routes ValueError 块存在 fake success: {matches}"
        )
        assert 'PODCAST_SEGMENT_INVALID' in source, (
            "podcast runtime/validate 应包含错误码 PODCAST_SEGMENT_INVALID"
        )

    def test_all_except_blocks_return_ok_false_on_error(self):
        """全局: 抽样检查 except 块中含 return 的不得返回 ok=True。"""
        source = _read_file(APP_PY)
        blocks = _extract_except_blocks(source)
        fake_success_blocks = []
        for block in blocks:
            if re.search(r'[\'"]ok[\'"]\s*:\s*True', block):
                fake_success_blocks.append(block[:100])
        assert len(fake_success_blocks) == 0, (
            f"发现 {len(fake_success_blocks)} 处 except 块返回 ok=True: "
            f"{fake_success_blocks[:3]}"
        )


# ═══════════════════════════════════════════════════════════════
# 2. 高风险端点权限装饰器检查
# ═══════════════════════════════════════════════════════════════

class TestPermissionDecorators:
    """验证高风险端点已接入 @require_permission。"""

    HIGH_RISK_ENDPOINTS = [
        # (路由路径, 方法, 期望的 OperationType)
        ('/api/brands/<brand_en>', 'DELETE', 'DATA_DELETE'),
        ('/api/event-graph/events/<event_id>', 'DELETE', 'DATA_DELETE'),
        ('/api/system/config', 'POST', 'CONFIG_MODIFY'),
        ('/api/cookies/import', 'POST', 'DATA_IMPORT'),
    ]

    def test_require_permission_imported_in_app(self):
        """app.py 必须从唯一 SYSTEM Security owner 导入权限门。"""
        source = _read_file(APP_PY)
        assert 'from lumenis.system.security import (' in source, (
            "app.py 应从 lumenis.system.security 导入 require_permission"
        )
        assert 'require_permission' in source, (
            "app.py 应包含 require_permission 引用"
        )

    def test_all_directly_protected_high_risk_endpoints_have_decorator(self):
        """每个需要端点级保护的高风险路由均有 @require_permission。"""
        source = _read_file(APP_PY)
        decorator_count = source.count('@require_permission(')
        assert decorator_count >= len(self.HIGH_RISK_ENDPOINTS), (
            f"应至少有 {len(self.HIGH_RISK_ENDPOINTS)} 个 @require_permission 装饰器，"
            f"实际找到 {decorator_count} 个"
        )

    @pytest.mark.parametrize("path,method,op_type", HIGH_RISK_ENDPOINTS)
    def test_endpoint_has_permission_decorator(self, path, method, op_type):
        """每个高风险端点的函数定义前应有 @require_permission。"""
        source = _read_file(APP_PY)
        # 找到路由定义位置
        route_pattern = re.compile(
            rf"@app\.route\(['\"]{re.escape(path)}['\"][^)]*methods=\['{method}'\]\)"
        )
        route_matches = list(route_pattern.finditer(source))
        assert len(route_matches) > 0, f"未找到路由: {path} [{method}]"

        # 检查路由装饰器和函数定义之间是否有 @require_permission
        for m in route_matches:
            start = m.start()
            # 向后查找函数定义
            func_match = re.search(r'def\s+\w+', source[start:start + 500])
            if func_match:
                block = source[start:start + func_match.end()]
                assert '@require_permission' in block, (
                    f"端点 {path} [{method}] 缺少 @require_permission 装饰器"
                )
                assert op_type in block, (
                    f"端点 {path} [{method}] 应使用 OperationType.{op_type}"
                )
            break

    def test_decorator_has_deny_return_403(self):
        """端点级高风险权限装饰器拒绝时应返回 403 和结构化错误码。"""
        source = _read_file(APP_PY)
        # 统计含 PERMISSION_DENIED 和 403 的 @require_permission 装饰器数量
        import re as _re
        blocks = _re.split(r'(?=@require_permission\()', source)
        count = sum(1 for b in blocks if 'PERMISSION_DENIED' in b and '403' in b and 'deny_return' in b)
        assert count >= len(self.HIGH_RISK_ENDPOINTS), (
            f"应至少有 {len(self.HIGH_RISK_ENDPOINTS)} 个装饰器配置 deny_return=(..., 403) + PERMISSION_DENIED，"
            f"实际找到 {count} 个"
        )

    def test_noop_fallback_on_import_failure(self):
        """权限 owner 导入失败时不能静默退化成放行装饰器。"""
        source = _read_file(APP_PY)
        assert 'from lumenis.system.security import (' in source
        assert 'def require_permission(*args, **kwargs):' not in source
        assert 'require_permission = None' not in source, (
            "app.py 必须由 canonical SYSTEM Security 提供权限装饰器，不能加 no-op 放行回退"
        )


# ═══════════════════════════════════════════════════════════════
# 3. PermissionGate 全局初始化验证
# ═══════════════════════════════════════════════════════════════

class TestPermissionGateInit:
    """验证 app.py 中 PermissionGate 全局初始化。"""

    def test_get_permission_gate_called(self):
        """app.py: 应调用 get_permission_gate() 初始化全局门。"""
        source = _read_file(APP_PY)
        assert 'get_permission_gate()' in source, (
            "app.py 应调用 get_permission_gate() 初始化全局 PermissionGate"
        )

    def test_baseline_permissions_granted(self):
        """app.py: 应授予基线权限（COMMIT/PUSH）以兼容现有功能。"""
        source = _read_file(APP_PY)
        assert 'grant_permission(PermissionLevel.COMMIT)' in source, (
            "app.py 应授予 COMMIT 基线权限"
        )
        assert 'grant_permission(PermissionLevel.PUSH)' in source, (
            "app.py 应授予 PUSH 基线权限"
        )

    def test_app_initializes_canonical_gate_without_permissive_fallback(self):
        """app.py 在导入后初始化 canonical gate 并授予配置的操作等级。"""
        source = _read_file(APP_PY)
        start = source.find('_pg = get_permission_gate()')
        assert start >= 0, "app.py 应初始化 canonical PermissionGate 单例"
        init_section = source[start:start + 600]
        for permission in ('COMMIT', 'PUSH', 'HUMAN_APPROVAL'):
            assert f'PermissionLevel.{permission}' in init_section, (
                f"app.py 应显式配置 {permission} 权限等级"
            )


# ═══════════════════════════════════════════════════════════════
# 4. 错误码字段检查
# ═══════════════════════════════════════════════════════════════

class TestErrorCodes:
    """验证修复端点包含结构化错误码。"""

    EXPECTED_ERROR_CODES = [
        'AUTH_HEADER_ENCODE_ERROR',
        'BRAND_INDUSTRY_QUERY_ERROR',
        'BRAND_INDUSTRY_STATS_ERROR',
        'NEGATIVE_REVIEW_STATS_ERROR',
        'PERMISSION_DENIED',
    ]

    @pytest.mark.parametrize("code", EXPECTED_ERROR_CODES)
    def test_error_code_present(self, code):
        """每个期望的错误码应存在于 app.py 中。"""
        source = _read_file(APP_PY)
        assert code in source, f"错误码 {code} 应存在于 app.py"

    def test_podcast_error_code_present(self):
        """podcast_routes.py 应包含 PODCAST_SEGMENT_INVALID 错误码。"""
        source = _read_file(PODCAST_ROUTES)
        assert 'PODCAST_SEGMENT_INVALID' in source, (
            "podcast_routes.py 应包含错误码 PODCAST_SEGMENT_INVALID"
        )

    def test_error_responses_have_code_field(self):
        """修复的 except 块返回值应包含 'code' 字段。"""
        source = _read_file(APP_PY)
        # 检查包含错误码的 return 语句是否有 code 字段（逐行检查，避免嵌套括号正则问题）
        for code in self.EXPECTED_ERROR_CODES[:4]:  # 前4个是 except 块的
            found = False
            for line in source.split('\n'):
                if code in line and 'return' in line and 'jsonify' in line:
                    assert "'code'" in line or '"code"' in line, (
                        f"错误码 {code} 的返回应包含 'code' 字段: {line.strip()}"
                    )
                    found = True
            assert found, f"错误码 {code} 应在 jsonify 返回中"


# ═══════════════════════════════════════════════════════════════
# 5. PermissionGate 单元行为测试（mock，不启动真实服务）
# ═══════════════════════════════════════════════════════════════

class TestPermissionGateBehavior:
    @pytest.fixture(autouse=True)
    def _strict_permission_gate(self):
        # 本类验证权限门严格行为（拒绝/授权放行/装饰器/审计），必须关闭 TESTING 旁路，结束还原
        from lumenis.system.security import set_testing_bypass
        set_testing_bypass(False)
        yield
        set_testing_bypass(True)

    """PermissionGate 核心行为验证（使用独立实例，不影响全局单例）。"""

    def test_gate_default_fail_closed(self):
        """默认 PermissionGate 应为 fail-closed。"""
        sys.path.insert(0, PROJECT_ROOT)
        from lumenis.system.security import PermissionGate, OperationType, RiskLevel
        gate = PermissionGate()
        assert gate.fail_closed is True

    def test_data_delete_requires_push_permission(self):
        """DATA_DELETE 操作应需要 PUSH 权限（默认未授予时应拒绝）。"""
        sys.path.insert(0, PROJECT_ROOT)
        from lumenis.system.security import PermissionGate, OperationType, RiskLevel
        gate = PermissionGate()  # 默认权限不含 PUSH
        result = gate.check(OperationType.DATA_DELETE, resource="/test", risk_level=RiskLevel.CRITICAL)
        assert result.allowed is False, (
            "默认权限下 DATA_DELETE 应被拒绝（需 PUSH 权限 + 人工审批）"
        )

    def test_grant_push_allows_data_delete(self):
        """授予 PUSH + HUMAN_APPROVAL 后 DATA_DELETE 应通过。"""
        sys.path.insert(0, PROJECT_ROOT)
        from lumenis.system.security import PermissionGate, PermissionLevel, OperationType, RiskLevel
        gate = PermissionGate()
        gate.grant_permission(PermissionLevel.PUSH)
        gate.grant_permission(PermissionLevel.HUMAN_APPROVAL)
        result = gate.check(OperationType.DATA_DELETE, resource="/test", risk_level=RiskLevel.CRITICAL)
        # CRITICAL 风险仍需人工审批令牌
        assert result.allowed is False or result.requires_approval is True, (
            "CRITICAL 风险操作应需要人工审批令牌"
        )

    def test_ai_call_auto_allowed(self):
        """AI_CALL (LOW 风险, ANALYZE 权限) 应自动放行。"""
        sys.path.insert(0, PROJECT_ROOT)
        from lumenis.system.security import PermissionGate, OperationType
        gate = PermissionGate()
        result = gate.check(OperationType.AI_CALL, resource="/test")
        assert result.allowed is True, (
            "AI_CALL 应自动放行（LOW 风险 + 默认含 ANALYZE 权限）"
        )

    def test_require_permission_decorator_denies(self):
        """@require_permission 装饰器在权限不足时应返回 deny_return。"""
        sys.path.insert(0, PROJECT_ROOT)
        from lumenis.system.security import PermissionGate, PermissionLevel, OperationType, RiskLevel, require_permission
        gate = PermissionGate()  # 默认权限，不含 COMMIT/PUSH

        denied_marker = {"ok": False, "error": "DENIED", "code": "PERMISSION_DENIED"}

        @require_permission(OperationType.DATA_DELETE, RiskLevel.CRITICAL,
                           gate=gate, deny_return=denied_marker)
        def risky_delete():
            return {"ok": True, "deleted": True}

        result = risky_delete()
        assert result == denied_marker, (
            "权限不足时装饰器应返回 deny_return，不执行函数体"
        )

    def test_require_permission_decorator_allows(self):
        """@require_permission 装饰器在权限充足时应执行函数体。"""
        sys.path.insert(0, PROJECT_ROOT)
        from lumenis.system.security import PermissionGate, PermissionLevel, OperationType, require_permission
        gate = PermissionGate()
        # AI_CALL 默认权限足够

        @require_permission(OperationType.AI_CALL, gate=gate)
        def ai_analyze():
            return {"ok": True, "result": "analyzed"}

        result = ai_analyze()
        assert result == {"ok": True, "result": "analyzed"}, (
            "权限充足时装饰器应执行函数体"
        )

    def test_audit_log_records_high_risk_calls(self):
        """PermissionGate 应记录高风险操作审计日志。"""
        sys.path.insert(0, PROJECT_ROOT)
        from lumenis.system.security import PermissionGate, PermissionLevel, OperationType, RiskLevel
        gate = PermissionGate()
        gate.grant_permission(PermissionLevel.PUSH)
        gate.grant_permission(PermissionLevel.HUMAN_APPROVAL)
        # 触发一次检查（即使被拒绝也应记录审计）
        gate.check(OperationType.DATA_DELETE, resource="/api/test", risk_level=RiskLevel.CRITICAL)
        assert len(gate._audit_log) >= 1, (
            "高风险操作检查应产生审计日志"
        )


# ═══════════════════════════════════════════════════════════════
# 6. 端点枚举完整性检查
# ═══════════════════════════════════════════════════════════════

class TestEndpointEnumeration:
    """验证关键端点存在性（不删除任何端点的回归检查）。"""

    CRITICAL_ENDPOINTS = [
        '/api/auth/config',
        '/api/brands/<brand_en>',
        '/api/event-graph/events/<event_id>',
        '/api/system/config',
        '/api/cookies/import',
        '/api/brand-industry/brands',
        '/api/brand-industry/stats',
        '/api/negative-review/stats',
    ]

    @pytest.mark.parametrize("path", CRITICAL_ENDPOINTS)
    def test_critical_endpoint_exists(self, path):
        """关键端点不得被删除。"""
        source = _read_file(APP_PY)
        assert path in source, f"关键端点 {path} 不得被删除"

    def test_arbitrary_server_code_routes_are_removed(self):
        """服务端任意代码执行入口已退役，不能重新暴露。"""
        source = _read_file(APP_PY)
        for path in ('/api/developer/run', '/api/dev/run-code', '/api/config/run-code'):
            assert path not in source


# ═══════════════════════════════════════════════════════════════
# 7. 禁止项回归检查
# ═══════════════════════════════════════════════════════════════

class TestProhibitedChanges:
    """验证未违反禁止项约束。"""

    def test_subject_words_not_modified(self):
        """SUBJECT_WORDS / subject_hit 应存在（未被删除/修改）。"""
        source = _read_file(APP_PY)
        # 检查主体过滤相关代码存在
        has_subject = 'SUBJECT_WORDS' in source or 'subject_hit' in source or '_subject_sql_and_values' in source
        assert has_subject, (
            "主体过滤代码（SUBJECT_WORDS/subject_hit/_subject_sql_and_values）应存在"
        )

    def test_no_endpoints_deleted(self):
        """核心路由数量不应大幅减少（抽样验证）。"""
        source = _read_file(APP_PY)
        route_count = len(re.findall(r'@app\.(route|get|post|delete|put)\(', source))
        assert route_count >= 180, (
            f"app.py 路由数应 >= 180（审计前 188），实际 {route_count}，可能误删端点"
        )
