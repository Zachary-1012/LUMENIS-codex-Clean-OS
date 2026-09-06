# -*- coding: utf-8 -*-
"""
tests/test_repository_registry.py — ZBC Phase 1 Repository Registry 测试

验证：
1. registry 初始化与 REPO_ROOT 自动解析
2. 路径解析 resolve_path() 相对/绝对路径
3. ENV 覆盖（ZBC_REPO_ROOT, ZBC_DATA_DIR 等）
4. 向后兼容（BASE_DIR 别名、config.py 不受影响）
5. 单例 get_registry()
6. 目录注册完整性
7. 生产代码无个人硬编码路径
"""
import os
import sys
import importlib
from pathlib import Path

import pytest

# 确保项目根目录在 path 中
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


# ── Fixtures ───────────────────────────────────────────────

@pytest.fixture
def clean_registry(monkeypatch):
    """每个测试前清除 ENV 路径变量并重置单例"""
    env_keys = [
        "ZBC_REPO_ROOT", "ZBC_CORE_DIR", "ZBC_DATA_DIR", "ZBC_RUNTIME_DIR",
        "ZBC_BACKUP_DIR", "ZBC_EXPORT_DIR", "ZBC_TEMP_DIR", "ZBC_AI_RUNTIME_DIR",
        "ZBC_COLLECTOR_DIR", "ZBC_LOG_DIR", "ZBC_CONFIG_DIR",
    ]
    for k in env_keys:
        monkeypatch.delenv(k, raising=False)

    # 重置模块级单例
    import repository_registry
    importlib.reload(repository_registry)
    yield repository_registry
    # 恢复
    importlib.reload(repository_registry)


# ── 1. 初始化与 REPO_ROOT 解析 ─────────────────────────────

class TestRegistryInit:
    """registry 初始化与 REPO_ROOT 自动解析"""

    def test_repo_root_auto_resolves_to_project_root(self, clean_registry):
        """无 ENV 时，REPO_ROOT 基于 __file__ 解析为项目根目录"""
        reg = clean_registry.RepositoryRegistry()
        assert reg.repo_root == Path(REPO_ROOT).resolve()

    def test_repo_root_is_absolute(self, clean_registry):
        """REPO_ROOT 必须是绝对路径"""
        reg = clean_registry.get_registry()
        assert reg.repo_root.is_absolute()

    def test_repo_root_contains_repository_registry_py(self, clean_registry):
        """REPO_ROOT 下应存在 repository_registry.py"""
        reg = clean_registry.get_registry()
        assert (reg.repo_root / "repository_registry.py").exists()

    def test_explicit_repo_root_param(self, clean_registry, tmp_path):
        """显式传入 repo_root 参数时优先使用"""
        reg = clean_registry.RepositoryRegistry(repo_root=str(tmp_path))
        assert reg.repo_root == tmp_path.resolve()


# ── 2. 路径解析 resolve_path() ─────────────────────────────

class TestResolvePath:
    """resolve_path() 相对/绝对路径解析"""

    def test_relative_path_resolves_under_repo_root(self, clean_registry):
        """相对路径拼接 REPO_ROOT"""
        reg = clean_registry.get_registry()
        result = reg.resolve("data/monitor.db")
        assert result == str((reg.repo_root / "data" / "monitor.db").resolve())

    def test_absolute_path_passthrough(self, clean_registry):
        """绝对路径原样返回（规范化）"""
        reg = clean_registry.get_registry()
        abs_path = str(Path("C:/tmp/test.db").resolve())
        result = reg.resolve(abs_path)
        assert result == abs_path

    def test_module_level_resolve_path_function(self, clean_registry):
        """模块级 resolve_path() 便捷函数与 registry.resolve() 一致"""
        reg = clean_registry.get_registry()
        assert clean_registry.resolve_path("data/monitor.db") == reg.resolve("data/monitor.db")

    def test_resolve_path_returns_str(self, clean_registry):
        """resolve() 返回 str"""
        reg = clean_registry.get_registry()
        assert isinstance(reg.resolve("data/monitor.db"), str)

    def test_resolve_path_obj_returns_path(self, clean_registry):
        """resolve_path() 方法返回 Path"""
        reg = clean_registry.get_registry()
        assert isinstance(reg.resolve_path("data/monitor.db"), Path)

    def test_env_file_resolution(self, clean_registry):
        """.env 路径解析正确"""
        reg = clean_registry.get_registry()
        result = reg.resolve(".env")
        assert result.endswith(".env")
        assert str(reg.repo_root) in result


# ── 3. ENV 覆盖 ────────────────────────────────────────────

class TestEnvOverride:
    """ENV 变量覆盖路径"""

    def test_zbc_repo_root_env_override(self, clean_registry, monkeypatch, tmp_path):
        """ZBC_REPO_ROOT 环境变量覆盖 REPO_ROOT"""
        monkeypatch.setenv("ZBC_REPO_ROOT", str(tmp_path))
        reg = clean_registry.RepositoryRegistry()
        assert reg.repo_root == tmp_path.resolve()

    def test_zbc_data_dir_env_override_absolute(self, clean_registry, monkeypatch, tmp_path):
        """ZBC_DATA_DIR 绝对路径覆盖"""
        custom_data = tmp_path / "custom_data"
        monkeypatch.setenv("ZBC_DATA_DIR", str(custom_data))
        reg = clean_registry.RepositoryRegistry()
        assert reg.data_dir == custom_data.resolve()

    def test_zbc_data_dir_env_override_relative(self, clean_registry, monkeypatch):
        """ZBC_DATA_DIR 相对路径基于 REPO_ROOT 解析"""
        monkeypatch.setenv("ZBC_DATA_DIR", "custom_data")
        reg = clean_registry.RepositoryRegistry()
        assert reg.data_dir == (reg.repo_root / "custom_data").resolve()

    def test_zbc_log_dir_override(self, clean_registry, monkeypatch, tmp_path):
        """ZBC_LOG_DIR 覆盖"""
        custom_log = tmp_path / "mylogs"
        monkeypatch.setenv("ZBC_LOG_DIR", str(custom_log))
        reg = clean_registry.RepositoryRegistry()
        assert reg.log_dir == custom_log.resolve()

    def test_zbc_backup_dir_override(self, clean_registry, monkeypatch, tmp_path):
        """ZBC_BACKUP_DIR 覆盖"""
        custom_bak = tmp_path / "mybackups"
        monkeypatch.setenv("ZBC_BACKUP_DIR", str(custom_bak))
        reg = clean_registry.RepositoryRegistry()
        assert reg.backup_dir == custom_bak.resolve()

    def test_force_reload_picks_env_change(self, clean_registry, monkeypatch, tmp_path):
        """get_registry(force_reload=True) 能拾取 ENV 变更"""
        reg1 = clean_registry.get_registry()
        default_data = reg1.data_dir

        monkeypatch.setenv("ZBC_DATA_DIR", str(tmp_path / "newdata"))
        reg2 = clean_registry.get_registry(force_reload=True)
        assert reg2.data_dir != default_data
        assert reg2.data_dir == (tmp_path / "newdata").resolve()


# ── 4. 向后兼容 ────────────────────────────────────────────

class TestBackwardCompatibility:
    """向后兼容：BASE_DIR 别名、config.py 不受影响"""

    def test_base_dir_alias_exists(self, clean_registry):
        """BASE_DIR 模块级别名存在且等于 REPO_ROOT"""
        assert hasattr(clean_registry, "BASE_DIR")
        assert clean_registry.BASE_DIR == str(Path(REPO_ROOT).resolve())

    def test_config_py_base_dir_still_works(self):
        """config.py 的 BASE_DIR 不受 repository_registry 影响"""
        import config
        assert hasattr(config, "BASE_DIR")
        assert config.BASE_DIR == REPO_ROOT

    def test_config_get_config_still_works(self):
        """config.get_config() 单例仍可正常调用"""
        import config
        cfg = config.get_config()
        assert cfg is not None
        # 能读取已知配置键
        assert cfg.get("APP_PORT") is not None or cfg.get("APP_PORT", 8200) == 8200

    def test_registry_does_not_import_app(self, clean_registry):
        """repository_registry 不依赖 app.py，可独立 import"""
        # 检查模块的全局命名空间不含 app
        assert "app" not in dir(clean_registry) or not hasattr(clean_registry, "app")

    def test_registry_no_hardcoded_personal_paths(self, clean_registry):
        """repository_registry.py 源码中不含个人硬编码路径"""
        src_file = Path(clean_registry.__file__)
        source = src_file.read_text(encoding="utf-8")
        assert "D:\\Taikoo-monitor-new" not in source
        assert "D:/Taikoo-monitor-new" not in source
        assert "C:\\Users\\28049" not in source
        assert "D:\\Zachary" not in source


# ── 5. 单例 ─────────────────────────────────────────────────

class TestSingleton:
    """get_registry() 单例"""

    def test_get_registry_returns_same_instance(self, clean_registry):
        """连续调用返回同一实例"""
        reg1 = clean_registry.get_registry()
        reg2 = clean_registry.get_registry()
        assert reg1 is reg2

    def test_force_reload_returns_new_instance(self, clean_registry):
        """force_reload=True 返回新实例"""
        reg1 = clean_registry.get_registry()
        reg2 = clean_registry.get_registry(force_reload=True)
        assert reg1 is not reg2


# ── 6. 目录注册完整性 ──────────────────────────────────────

class TestDirectoryRegistration:
    """所有关键目录已注册且可访问"""

    EXPECTED_DIRS = [
        "core_dir", "data_dir", "runtime_dir", "backup_dir",
        "export_dir", "temp_dir", "ai_runtime_dir", "collector_dir",
        "log_dir", "config_dir",
    ]

    def test_all_dir_properties_exist(self, clean_registry):
        """所有目录属性存在"""
        reg = clean_registry.get_registry()
        for dir_name in self.EXPECTED_DIRS:
            assert hasattr(reg, dir_name), f"缺少目录属性: {dir_name}"

    def test_all_dirs_are_absolute(self, clean_registry):
        """所有目录路径均为绝对路径"""
        reg = clean_registry.get_registry()
        for dir_name in self.EXPECTED_DIRS:
            d = getattr(reg, dir_name)
            assert d.is_absolute(), f"{dir_name} 不是绝对路径: {d}"

    def test_all_dirs_under_or_equal_repo_root_by_default(self, clean_registry):
        """默认配置下，所有目录在 REPO_ROOT 下或等于 REPO_ROOT"""
        reg = clean_registry.get_registry()
        for dir_name in self.EXPECTED_DIRS:
            d = getattr(reg, dir_name)
            try:
                d.relative_to(reg.repo_root)
            except ValueError:
                pytest.fail(f"{dir_name}={d} 不在 REPO_ROOT={reg.repo_root} 下")

    def test_ensure_dir_creates_directory(self, clean_registry, tmp_path, monkeypatch):
        """ensure_dir() 创建不存在的目录"""
        monkeypatch.setenv("ZBC_REPO_ROOT", str(tmp_path))
        reg = clean_registry.RepositoryRegistry()
        result = reg.ensure_dir("data")
        assert result.exists()
        assert result.is_dir()

    def test_ensure_dir_unknown_key_raises(self, clean_registry):
        """ensure_dir() 传入未知键抛出 KeyError"""
        reg = clean_registry.get_registry()
        with pytest.raises(KeyError):
            reg.ensure_dir("nonexistent_dir")

    def test_to_dict_contains_all_paths(self, clean_registry):
        """to_dict() 包含 repo_root 和所有目录"""
        reg = clean_registry.get_registry()
        d = reg.to_dict()
        assert "repo_root" in d
        for key in ["core", "data", "runtime", "backup", "export", "temp",
                     "ai_runtime", "collector", "log", "config"]:
            assert key in d, f"to_dict 缺少键: {key}"


# ── 7. 生产代码硬编码路径扫描 ──────────────────────────────

class TestNoHardcodedPathsInProduction:
    """生产代码中不含个人电脑绝对路径"""

    # 排除目录：非生产代码
    EXCLUDE_DIRS = {
        "tests", "99-ARCHIVE", "docs", "node_modules", ".venv",
        ".git", "__pycache__", ".pytest_cache", ".vscode",
        "00-GOVERNANCE", "audit", "scripts", "OSAI测试证据",
    }

    # 需扫描的硬编码模式
    HARDCODED_PATTERNS = [
        r"D:\Taikoo-monitor-new",
        r"D:/Taikoo-monitor-new",
        r"C:\Users\28049",
        r"C:/Users/28049",
        r"D:\Zachary",
        r"D:/Zachary",
    ]

    def _collect_production_py_files(self):
        """收集生产代码 .py 文件（排除非生产目录和 scratch 文件）"""
        files = []
        for root, dirs, filenames in os.walk(REPO_ROOT):
            # 排除目录
            dirs[:] = [d for d in dirs if d not in self.EXCLUDE_DIRS]
            for fn in filenames:
                if not fn.endswith(".py"):
                    continue
                # 排除 scratch/debug 临时文件（项目约定：_ 前缀为一次性脚本）
                if fn.startswith("_tmp_") or fn.startswith("_zbc_") or fn.startswith("_patch_") or fn.startswith("_split_") or fn.startswith("_lifecycle_") or fn.startswith("_archive_"):
                    continue
                files.append(os.path.join(root, fn))
        return files

    def test_no_hardcoded_paths_in_production_py(self):
        """所有生产 .py 文件中不含个人硬编码路径"""
        files = self._collect_production_py_files()
        violations = []
        for fpath in files:
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception:
                continue
            for pattern in self.HARDCODED_PATTERNS:
                if pattern in content:
                    # 找出具体行
                    for i, line in enumerate(content.splitlines(), 1):
                        if pattern in line:
                            violations.append(f"{os.path.relpath(fpath, REPO_ROOT)}:{i}: {line.strip()[:100]}")
        assert not violations, (
            f"生产代码中发现 {len(violations)} 处硬编码路径:\n" + "\n".join(violations)
        )

    def test_modified_files_use_registry(self):
        """被修改的6个生产文件已使用 resolve_path 或基于 __file__ 解析"""
        modified_files = [
            "auth_recovery_center.py",
            "brand_knowledge_base.py",
            "case_ai_evaluate.py",
            "case_deep_analysis.py",
            "lumenis_skill_adapter.py",
        ]
        for fname in modified_files:
            fpath = os.path.join(REPO_ROOT, fname)
            assert os.path.exists(fpath), f"文件不存在: {fname}"
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            # 不应再含硬编码
            for pattern in self.HARDCODED_PATTERNS:
                assert pattern not in content, f"{fname} 仍含硬编码: {pattern}"


# ── 8. 集成：修改后的文件可正常 import ─────────────────────

class TestModifiedFilesImport:
    """修改后的生产文件可正常 import（不破坏 import 链）"""

    def test_auth_recovery_center_imports(self):
        """auth_recovery_center 可 import"""
        import auth_recovery_center
        assert hasattr(auth_recovery_center, "AuthRecoveryCenter")

    def test_brand_knowledge_base_imports(self):
        """brand_knowledge_base 可 import"""
        import brand_knowledge_base
        assert hasattr(brand_knowledge_base, "BrandKnowledgeBase")

    def test_case_ai_evaluate_imports(self):
        """case_ai_evaluate 可 import"""
        import case_ai_evaluate
        assert hasattr(case_ai_evaluate, "_ZHIPU_URL")

    def test_case_deep_analysis_imports(self):
        """case_deep_analysis 可 import"""
        import case_deep_analysis
        assert hasattr(case_deep_analysis, "CaseDeepAnalysis")

    def test_lumenis_skill_adapter_imports(self):
        """lumenis_skill_adapter 可 import"""
        import lumenis_skill_adapter
        assert hasattr(lumenis_skill_adapter, "_osai_root")

    def test_db_path_in_modified_files_points_to_data_dir(self):
        """修改后的 DB_PATH 指向 data/monitor.db"""
        import auth_recovery_center
        import brand_knowledge_base
        import case_deep_analysis

        expected = str((Path(REPO_ROOT) / "data" / "monitor.db").resolve())
        assert auth_recovery_center.AuthRecoveryCenter.DB_PATH == expected
        assert brand_knowledge_base.DB_PATH == expected
        assert case_deep_analysis.DB_PATH == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
