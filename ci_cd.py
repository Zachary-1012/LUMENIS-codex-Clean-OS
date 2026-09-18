"""
广州太古汇舆情监测系统 - CI/CD 自动化脚本
自动化测试、构建、部署、发布

使用方法：
    python ci_cd.py test          # 运行所有测试
    python ci_cd.py build         # 构建发布包
    python ci_cd.py deploy        # 部署到本地
    python ci_cd.py release       # 完整发布流程（测试→构建→部署）
    python ci_cd.py status        # 查看系统状态
"""

import os
import sys
import json
import shutil
import subprocess
from datetime import datetime
from typing import Dict, Any, List, Optional

# 项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 发布目录
RELEASE_DIR = os.path.join(BASE_DIR, 'releases')
BUILD_DIR = os.path.join(BASE_DIR, 'build')

# 版本信息
VERSION_FILE = os.path.join(BASE_DIR, 'VERSION')
CHANGELOG_FILE = os.path.join(BASE_DIR, 'CHANGELOG.md')


def get_version() -> str:
    """获取当前版本号"""
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE, 'r', encoding='utf-8') as f:
            return f.read().strip()
    return '5.7.0'


def bump_version(part: str = 'patch') -> str:
    """
    升级版本号
    
    Args:
        part: major/minor/patch
    
    Returns:
        新版本号
    """
    version = get_version()
    parts = version.split('.')
    
    if len(parts) != 3:
        parts = ['5', '7', '0']
    
    major, minor, patch = map(int, parts)
    
    if part == 'major':
        major += 1
        minor = 0
        patch = 0
    elif part == 'minor':
        minor += 1
        patch = 0
    else:
        patch += 1
    
    new_version = f'{major}.{minor}.{patch}'
    
    with open(VERSION_FILE, 'w', encoding='utf-8') as f:
        f.write(new_version)
    
    print(f"✅ 版本升级: {version} → {new_version}")
    return new_version


def run_command(cmd: List[str], cwd: Optional[str] = None, timeout: int = 300) -> Dict[str, Any]:
    """
    运行命令
    
    Args:
        cmd: 命令列表
        cwd: 工作目录
        timeout: 超时时间（秒）
    
    Returns:
        命令结果字典
    """
    result = {
        'cmd': ' '.join(cmd),
        'returncode': -1,
        'stdout': '',
        'stderr': '',
        'success': False
    }
    
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd or BASE_DIR,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding='utf-8',
            errors='replace'
        )
        result['returncode'] = proc.returncode
        result['stdout'] = proc.stdout
        result['stderr'] = proc.stderr
        result['success'] = proc.returncode == 0
    except subprocess.TimeoutExpired:
        result['stderr'] = f'命令超时（{timeout}秒）'
    except Exception as e:
        result['stderr'] = str(e)
    
    return result


def run_tests() -> bool:
    """
    运行所有测试
    
    Returns:
        是否全部通过
    """
    print("=" * 60)
    print("🧪 运行测试")
    print("=" * 60)
    
    python_exe = os.path.join(BASE_DIR, '.venv', 'Scripts', 'python.exe')
    if not os.path.exists(python_exe):
        python_exe = 'python'
    
    all_passed = True
    
    # 1. 语法检查
    print("\n📝 1. Python语法检查")
    py_files = [f for f in os.listdir(BASE_DIR) if f.endswith('.py')]
    syntax_errors = []
    
    for py_file in py_files:
        result = run_command([python_exe, '-m', 'py_compile', py_file])
        if not result['success']:
            syntax_errors.append(py_file)
            print(f"  ❌ {py_file}: 语法错误")
        else:
            print(f"  ✅ {py_file}")
    
    if syntax_errors:
        print(f"\n❌ 语法检查失败: {len(syntax_errors)}个文件有错误")
        all_passed = False
    else:
        print("\n✅ 语法检查全部通过")
    
    # 2. 端到端测试
    print("\n🔍 2. 端到端测试")
    result = run_command([python_exe, 'test_e2e.py', '--quick'])
    
    if result['success']:
        print("  ✅ 端到端测试通过")
        # 提取通过率
        for line in result['stdout'].split('\n'):
            if '通过率' in line:
                print(f"  {line.strip()}")
    else:
        print("  ❌ 端到端测试失败")
        print(result['stdout'][-500:] if result['stdout'] else '')
        all_passed = False
    
    # 3. 数据库迁移检查
    print("\n💾 3. 数据库迁移检查")
    result = run_command([python_exe, 'database_migrations.py', 'status'])
    if result['success']:
        print("  ✅ 数据库迁移状态正常")
        for line in result['stdout'].split('\n'):
            if '当前版本' in line or '最新版本' in line:
                print(f"  {line.strip()}")
    else:
        print("  ❌ 数据库迁移检查失败")
        all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 所有测试通过！")
    else:
        print("❌ 部分测试失败，请修复后重试")
    print("=" * 60)
    
    return all_passed


def build_release(version: Optional[str] = None) -> Optional[str]:
    """
    构建发布包
    
    Args:
        version: 版本号
    
    Returns:
        发布包路径
    """
    print("\n" + "=" * 60)
    print("📦 构建发布包")
    print("=" * 60)
    
    if version is None:
        version = get_version()
    
    os.makedirs(RELEASE_DIR, exist_ok=True)
    
    # 发布包名称
    release_name = f'TaikooMonitor_v{version}_SOURCE'
    release_path = os.path.join(RELEASE_DIR, f'{release_name}.zip')
    
    # 需要包含的文件/目录
    include_items = [
        'app.py', 'database.py', 'models.py', 'collector.py',
        'ai_analyzer.py', 'intelligence.py', 'ai_filter.py',
        'risk_engine.py', 'report_engine.py', 'daily_report.py',
        'reprocess.py', 'web_discovery.py', 'monitor_pipeline.py',
        'function_registry.py', 'subject_rules.py', 'config.py',
        'logger.py', 'database_migrations.py', 'ci_cd.py',
        'monitoring.py',
        'requirements.txt', 'package.json', 'package-lock.json',
        'test_system.py', 'test_e2e.py',
        'events_config.json', 'brand_directory.json', 'brand_websites.json',
        'case_library.json', 'function_map.json', 'system_config.json',
        '.env.example', 'VERSION', 'CHANGELOG.md', 'README.md',
        'static', 'templates', 'deployment',
        'report_export',
    ]
    
    # 需要排除的文件/目录
    exclude_patterns = [
        '__pycache__', '.pyc', '.venv', 'node_modules',
        '.env', 'data/monitor.db', 'data/backups',
        'data/screenshots', 'logs', 'releases', 'build',
        '.git', '.vscode', '.idea',
        'cloudflared.exe', 'OllamaSetup',
    ]
    
    print(f"\n📋 版本: v{version}")
    print(f"📁 发布包: {release_path}")
    
    # 创建临时构建目录
    temp_dir = os.path.join(BUILD_DIR, release_name)
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir, exist_ok=True)
    
    # 复制文件
    copied_count = 0
    for item in include_items:
        src = os.path.join(BASE_DIR, item)
        dst = os.path.join(temp_dir, item)
        
        if not os.path.exists(src):
            print(f"  ⚠️  跳过不存在: {item}")
            continue
        
        if os.path.isdir(src):
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns(*exclude_patterns))
        else:
            shutil.copy2(src, dst)
        
        copied_count += 1
        print(f"  ✅ {item}")
    
    # 创建ZIP包
    print(f"\n🗜️  打包中...")
    shutil.make_archive(
        os.path.join(RELEASE_DIR, release_name),
        'zip',
        BUILD_DIR,
        release_name
    )
    
    # 清理临时目录
    shutil.rmtree(temp_dir, ignore_errors=True)
    
    file_size = os.path.getsize(release_path) / 1024 / 1024
    print(f"\n✅ 发布包构建完成！")
    print(f"   路径: {release_path}")
    print(f"   大小: {file_size:.2f} MB")
    print(f"   包含: {copied_count} 个项目")
    
    return release_path


def deploy_local() -> bool:
    """
    部署到本地（重启服务）
    
    Returns:
        是否成功
    """
    print("\n" + "=" * 60)
    print("🚀 本地部署")
    print("=" * 60)
    
    python_exe = os.path.join(BASE_DIR, '.venv', 'Scripts', 'python.exe')
    if not os.path.exists(python_exe):
        python_exe = 'python'
    
    # 1. 停止现有服务
    print("\n🛑 1. 停止现有服务")
    result = run_command(['taskkill', '/f', '/im', 'python.exe'])
    print("  ✅ 已停止Python进程")
    
    # 2. 数据库迁移
    print("\n💾 2. 数据库迁移")
    result = run_command([python_exe, 'database_migrations.py', 'migrate'])
    if result['success']:
        print("  ✅ 数据库迁移完成")
    else:
        print("  ❌ 数据库迁移失败")
        return False
    
    # 3. 启动服务
    print("\n▶️  3. 启动服务")
    print(f"   命令: {python_exe} app.py --host 0.0.0.0 --port 8200")
    print("   ⚠️  请手动启动服务（避免脚本阻塞）")
    
    print("\n✅ 本地部署准备完成！")
    print("   请手动执行以下命令启动服务：")
    print(f"   cd {BASE_DIR}")
    print(f"   {python_exe} app.py --host 0.0.0.0 --port 8200")
    
    return True


def release(part: str = 'patch') -> bool:
    """
    完整发布流程：测试→构建→部署
    
    Args:
        part: 版本升级类型 major/minor/patch
    
    Returns:
        是否成功
    """
    print("\n" + "=" * 60)
    print("🎉 完整发布流程")
    print("=" * 60)
    
    # 1. 运行测试
    if not run_tests():
        print("\n❌ 测试未通过，发布中止")
        return False
    
    # 2. 升级版本
    new_version = bump_version(part)
    
    # 3. 构建发布包
    release_path = build_release(new_version)
    if not release_path:
        print("\n❌ 构建失败，发布中止")
        return False
    
    # 4. 部署
    if not deploy_local():
        print("\n❌ 部署失败")
        return False
    
    print("\n" + "=" * 60)
    print(f"✅ 发布完成！版本 v{new_version}")
    print(f"   发布包: {release_path}")
    print("=" * 60)
    
    return True


def show_status():
    """显示系统状态"""
    print("=" * 60)
    print("📊 系统状态")
    print("=" * 60)
    
    # 版本
    print(f"\n📌 版本: v{get_version()}")
    
    # Python进程
    print("\n🐍 Python进程:")
    result = run_command(['tasklist', '/fi', 'imagename eq python.exe', '/fo', 'csv'])
    if result['success'] and 'python.exe' in result['stdout']:
        for line in result['stdout'].split('\n'):
            if 'python.exe' in line:
                print(f"  {line.strip()}")
    else:
        print("  无运行中的Python进程")
    
    # cloudflared进程
    print("\n🌐 Cloudflare Tunnel:")
    result = run_command(['tasklist', '/fi', 'imagename eq cloudflared.exe', '/fo', 'csv'])
    if result['success'] and 'cloudflared.exe' in result['stdout']:
        print("  ✅ 运行中")
    else:
        print("  ❌ 未运行")
    
    # 数据库
    print("\n💾 数据库:")
    db_path = os.path.join(BASE_DIR, 'data', 'monitor.db')
    if os.path.exists(db_path):
        size_mb = os.path.getsize(db_path) / 1024 / 1024
        print(f"  ✅ 存在 ({size_mb:.2f} MB)")
    else:
        print("  ❌ 不存在")
    
    # 测试状态
    print("\n🧪 最近测试:")
    test_log = os.path.join(BASE_DIR, 'logs', 'test_e2e.log')
    if os.path.exists(test_log):
        mtime = datetime.fromtimestamp(os.path.getmtime(test_log))
        print(f"  📅 {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print("  无测试记录")
    
    print("\n" + "=" * 60)


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python ci_cd.py test          # 运行所有测试")
        print("  python ci_cd.py build         # 构建发布包")
        print("  python ci_cd.py deploy        # 部署到本地")
        print("  python ci_cd.py release       # 完整发布流程")
        print("  python ci_cd.py status        # 查看系统状态")
        print("  python ci_cd.py version       # 查看版本号")
        print("  python ci_cd.py bump [patch|minor|major]  # 升级版本号")
        return
    
    command = sys.argv[1].lower()
    
    if command == 'test':
        success = run_tests()
        sys.exit(0 if success else 1)
    elif command == 'build':
        build_release()
    elif command == 'deploy':
        deploy_local()
    elif command == 'release':
        part = sys.argv[2] if len(sys.argv) > 2 else 'patch'
        success = release(part)
        sys.exit(0 if success else 1)
    elif command == 'status':
        show_status()
    elif command == 'version':
        print(f"v{get_version()}")
    elif command == 'bump':
        part = sys.argv[2] if len(sys.argv) > 2 else 'patch'
        bump_version(part)
    else:
        print(f"未知命令: {command}")


if __name__ == '__main__':
    main()
