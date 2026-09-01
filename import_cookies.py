"""
Cookie导入工具
将用户提供的微博和B站cookie导入系统

[Zachary-OS-AI T0-2 SEC-001 修复 v2]
  真实凭证不再硬编码。从 .env 读取两个 JSON 变量：
    ZBC_WEIBO_COOKIE_JSON = [{"name":"...","value":"...",...}, ...]
    ZBC_BILI_COOKIE_JSON  = [{"name":"...","value":"...",...}, ...]
  未配置时，脚本给出提示但不报错退出（保持导入入口可用，由用户手动复制）。
"""
import json
import os
import sys
from pathlib import Path
from datetime import datetime

# 加载 .env（优先使用 python-dotenv，无依赖时 fallback）
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / '.env')
except Exception:
    # fallback: 手动解析
    env_path = Path(__file__).resolve().parent / '.env'
    if env_path.exists():
        for line in env_path.read_text(encoding='utf-8', errors='ignore').splitlines():
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v

base_dir = Path(__file__).resolve().parent
data_dir = base_dir / 'data'
data_dir.mkdir(exist_ok=True)


def _load_cookie_env(env_key: str, platform_label: str):
    raw = os.environ.get(env_key, '').strip()
    if not raw:
        print(f'⚠️  未设置 .env 变量 {env_key}，跳过 {platform_label} Cookie 导入。')
        print(f'   复制真实 Cookie 列表到 .env 即可，示例:')
        print(f'   {env_key}=[{{"name":"PC_TOKEN","value":"xxx","domain":".{platform_label.lower()}.com","path":"/","httpOnly":false,"secure":false}}]')
        return []
    try:
        data = json.loads(raw)
        if not isinstance(data, list):
            raise ValueError('JSON 顶层必须是数组')
        return data
    except Exception as e:
        print(f'❌ 解析 .env 变量 {env_key} 失败: {e}')
        print(f'   请确认它是一段合法 JSON 数组字符串，并且没有换行。')
        return []


# ============================================
# 微博Cookie
# ============================================
weibo_cookies = _load_cookie_env('ZBC_WEIBO_COOKIE_JSON', 'Weibo')
if weibo_cookies:
    weibo_cookie_file = data_dir / 'weibo_cookies.json'
    with open(weibo_cookie_file, 'w', encoding='utf-8') as f:
        json.dump(weibo_cookies, f, ensure_ascii=False, indent=2)
    print(f'✅ 微博Cookie已保存: {weibo_cookie_file} ({len(weibo_cookies)}个)')

    weibo_status_file = data_dir / 'weibo_login_status.json'
    weibo_status = {
        'logged_in': True,
        'last_login': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'cookie_count': len(weibo_cookies),
        'login_method': 'cookie_import_from_env'
    }
    with open(weibo_status_file, 'w', encoding='utf-8') as f:
        json.dump(weibo_status, f, ensure_ascii=False, indent=2)
    print(f'✅ 微博登录状态已保存: {weibo_status_file}')

# ============================================
# B站Cookie
# ============================================
bilibili_cookies = _load_cookie_env('ZBC_BILI_COOKIE_JSON', 'Bilibili')
_user_id = ''
if bilibili_cookies:
    for c in bilibili_cookies:
        if c.get('name') == 'DedeUserID':
            _user_id = str(c.get('value', ''))
            break
    bilibili_cookie_file = data_dir / 'bilibili_cookies.json'
    with open(bilibili_cookie_file, 'w', encoding='utf-8') as f:
        json.dump(bilibili_cookies, f, ensure_ascii=False, indent=2)
    print(f'✅ B站Cookie已保存: {bilibili_cookie_file} ({len(bilibili_cookies)}个)')

    bilibili_status_file = data_dir / 'bilibili_login_status.json'
    bilibili_status = {
        'logged_in': True,
        'last_login': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'cookie_count': len(bilibili_cookies),
        'user_id': _user_id or 'unknown',
        'login_method': 'cookie_import_from_env'
    }
    with open(bilibili_status_file, 'w', encoding='utf-8') as f:
        json.dump(bilibili_status, f, ensure_ascii=False, indent=2)
    print(f'✅ B站登录状态已保存: {bilibili_status_file}')

print()
print('=' * 50)
print('  Cookie导入完成！')
print('=' * 50)
print(f'微博: {len(weibo_cookies)}个Cookie')
print(f'B站:  {len(bilibili_cookies)}个Cookie')
if _user_id:
    print(f'用户ID: {_user_id}')
if not weibo_cookies and not bilibili_cookies:
    print()
    print('👉 当前没有导入任何 Cookie。请在 .env 中配置：')
    print('     ZBC_WEIBO_COOKIE_JSON="[...]"')
    print('     ZBC_BILI_COOKIE_JSON="[...]"')
    print('   然后再次执行：python import_cookies.py')
    sys.exit(1)
print()
print('现在可以启用全网话题搜集（微博+B站）了！')
