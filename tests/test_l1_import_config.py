"""
L1: Import/Syntax/Dependency/Config Test
验证所有核心模块可导入、config 加载有效、依赖完整性
"""
import os
import sys
import json
import importlib
import traceback

# 确保项目根目录在 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 测试专用凭证（与 conftest 一致）
os.environ.setdefault('TAIKOO_AUTH_USER', 'Zachary')
os.environ.setdefault('TAIKOO_AUTH_PASSWORD', os.environ.get('LUMENIS_TEST_AUTH_PASS', 'test-only-pass'))

RESULT = {
    "level": "L1",
    "imports": {"passed": [], "failed": []},
    "config": {},
    "dependencies": {"passed": [], "failed": []},
    "summary": {"passed": 0, "failed": 0, "skipped": 0, "error": 0}
}

# 核心模块列表（20+）
CORE_MODULES = [
    "app",
    "database",
    "config",
    "collector",
    "runtime_guardian",
    "ai_analyzer",
    "risk_engine",
    "daily_report",
    "evidence_chain",
    "evidence_store",
    "canonical_data",
    "permission_gate",
    "subject_classifier",
    "repository_registry",
    "runtime_preflight",
    "collector_automation",
    "provider_registry",
    "ai_call_logger",
    "ai_governance",
    "database_migrations",
    "system_health_api",
    "report_engine",
    "alert_engine",
    "safety_boundary",
    "security_boundary",
    "logger",
    "models",
    "cache_manager",
    "data_quality_gate",
    "compliance_gate",
]

def test_imports():
    """测试所有核心模块可导入"""
    for mod_name in CORE_MODULES:
        try:
            importlib.import_module(mod_name)
            RESULT["imports"]["passed"].append(mod_name)
        except Exception as e:
            RESULT["imports"]["failed"].append({
                "module": mod_name,
                "error": str(e)[:500],
                "traceback": traceback.format_exc()[:1000]
            })

def test_config():
    """验证 config 加载有效，关键配置项有值（API key 脱敏）"""
    try:
        import config as cfg
        config_info = {}
        # 检查常见配置属性
        for attr in dir(cfg):
            if attr.startswith('_'):
                continue
            val = getattr(cfg, attr)
            if callable(val):
                continue
            # 脱敏处理
            if any(k in attr.upper() for k in ['KEY', 'SECRET', 'TOKEN', 'PASSWORD', 'COOKIE']):
                if val and isinstance(val, str) and len(val) > 8:
                    config_info[attr] = f"{val[:4]}***{val[-4:]}"
                elif val:
                    config_info[attr] = "***SET***"
                else:
                    config_info[attr] = "EMPTY"
            else:
                config_info[attr] = str(val)[:200] if val else "EMPTY"
        RESULT["config"] = config_info
        RESULT["config"]["_status"] = "loaded"
    except Exception as e:
        RESULT["config"] = {"_status": "failed", "error": str(e)[:500]}

def test_dependencies():
    """验证 requirements.txt 中关键包可导入"""
    key_packages = [
        ("flask", "flask"),
        ("requests", "requests"),
        ("sqlite3", "sqlite3"),
        ("pytest", "pytest"),
        ("dotenv", "dotenv"),
        ("apscheduler", "apscheduler"),
        ("playwright", "playwright"),
        ("numpy", "numpy"),
        ("pandas", "pandas"),
        ("openpyxl", "openpyxl"),
        ("jinja2", "jinja2"),
        ("werkzeug", "werkzeug"),
        ("dateutil", "dateutil"),
        ("bs4", "bs4"),
        ("lxml", "lxml"),
    ]
    for pkg_name, import_name in key_packages:
        try:
            importlib.import_module(import_name)
            RESULT["dependencies"]["passed"].append(pkg_name)
        except Exception as e:
            RESULT["dependencies"]["failed"].append({
                "package": pkg_name,
                "import_as": import_name,
                "error": str(e)[:200]
            })

if __name__ == "__main__":
    print("=" * 60)
    print("L1: Import/Syntax/Dependency/Config Test")
    print("=" * 60)

    print("\n[1/3] Testing core module imports...")
    test_imports()
    print(f"  Passed: {len(RESULT['imports']['passed'])}")
    print(f"  Failed: {len(RESULT['imports']['failed'])}")
    for f in RESULT["imports"]["failed"]:
        print(f"    FAIL: {f['module']} - {f['error'][:100]}")

    print("\n[2/3] Testing config loading...")
    test_config()
    print(f"  Config status: {RESULT['config'].get('_status', 'unknown')}")

    print("\n[3/3] Testing dependencies...")
    test_dependencies()
    print(f"  Passed: {len(RESULT['dependencies']['passed'])}")
    print(f"  Failed: {len(RESULT['dependencies']['failed'])}")
    for f in RESULT["dependencies"]["failed"]:
        print(f"    FAIL: {f['package']} - {f['error'][:100]}")

    # 汇总
    RESULT["summary"]["passed"] = (
        len(RESULT["imports"]["passed"]) +
        len(RESULT["dependencies"]["passed"]) +
        (1 if RESULT["config"].get("_status") == "loaded" else 0)
    )
    RESULT["summary"]["failed"] = (
        len(RESULT["imports"]["failed"]) +
        len(RESULT["dependencies"]["failed"]) +
        (0 if RESULT["config"].get("_status") == "loaded" else 1)
    )

    print("\n" + "=" * 60)
    print(f"L1 Summary: {RESULT['summary']['passed']} passed / {RESULT['summary']['failed']} failed")
    print("=" * 60)

    # 保存结果
    out_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "audit", "test_results_l1.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(RESULT, f, ensure_ascii=False, indent=2)
    print(f"\nResults saved to: {out_path}")
