"""
小红书 Cookie 导入工具（脱敏版，凭证不入库、不写死源码）

用法：
  1. 把浏览器导出的小红书 Cookie（标准 JSON 数组，元素含 name/value/domain 等）
     保存到本仓库之外或被 .gitignore 忽略的本地文件：data/xhs_cookies.source.json
     —— data/ 已被 .gitignore 整体忽略，不会提交；
  2. 运行本脚本：python import_xhs_cookies.py
  3. 脚本会生成 data/xhs_cookies.json、data/xhs_cookie_string.txt、
     data/xhs_login_status.json 供采集器使用（这些产物同样不入库）。

安全约定：真实 Cookie / web_session / user_id 一律只允许出现在本地 data 源文件或 .env，
严禁回填到本源码。仓库版本只保留处理逻辑与空占位。
"""
import json
import os
from pathlib import Path
from datetime import datetime

base_dir = Path(__file__).resolve().parent
data_dir = base_dir / 'data'
data_dir.mkdir(exist_ok=True)

# 仅从本地外部源读取凭证；源码内保持空列表占位。
SOURCE_FILE = data_dir / 'xhs_cookies.source.json'


def load_source_cookies():
    if not SOURCE_FILE.exists():
        return None
    with open(SOURCE_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if isinstance(data, dict):
        # 兼容 {"cookies": [...]} 包裹格式
        data = data.get('cookies', [])
    return data


xhs_cookies = load_source_cookies()

if not xhs_cookies:
    print('[跳过] 未找到本地 Cookie 源文件 data/xhs_cookies.source.json（或内容为空）。')
    print('       请把浏览器导出的小红书 Cookie JSON 数组放到该文件后再运行；本脚本不会内嵌任何凭证。')
    raise SystemExit(0)

# 保存小红书Cookie
xhs_cookie_file = data_dir / 'xhs_cookies.json'
with open(xhs_cookie_file, 'w', encoding='utf-8') as f:
    json.dump(xhs_cookies, f, ensure_ascii=False, indent=2)
print(f'✅ 小红书Cookie已保存: {xhs_cookie_file} ({len(xhs_cookies)}个)')

# 生成Cookie字符串（用于HTTP请求）
cookie_parts = []
for cookie in xhs_cookies:
    if cookie.get('domain', '').endswith('xiaohongshu.com') or cookie.get('domain') == '.xiaohongshu.com':
        name = cookie.get('name', '')
        value = cookie.get('value', '')
        if name and value and not name.startswith('x-user-id-'):
            cookie_parts.append(f'{name}={value}')

cookie_string = '; '.join(cookie_parts)

# 保存Cookie字符串
xhs_cookie_string_file = data_dir / 'xhs_cookie_string.txt'
with open(xhs_cookie_string_file, 'w', encoding='utf-8') as f:
    f.write(cookie_string)
print(f'✅ 小红书Cookie字符串已保存: {xhs_cookie_string_file}')
print(f'   Cookie字符串长度: {len(cookie_string)}')

# 保存小红书登录状态（user_id / web_session 均从源 Cookie 现取，不写死）
def _cookie_value(wanted):
    for c in xhs_cookies:
        if c.get('name') == wanted:
            return c.get('value', '')
    return ''

user_id = _cookie_value('x-user-id-creator.xiaohongshu.com') or _cookie_value('a1')
web_session = _cookie_value('web_session')
xhs_status_file = data_dir / 'xhs_login_status.json'
xhs_status = {
    'logged_in': bool(web_session),
    'last_login': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'cookie_count': len(xhs_cookies),
    'user_id': user_id,
    'web_session': web_session,
    'login_method': 'cookie_import',
    'platform': 'xiaohongshu'
}
with open(xhs_status_file, 'w', encoding='utf-8') as f:
    json.dump(xhs_status, f, ensure_ascii=False, indent=2)
print(f'✅ 小红书登录状态已保存: {xhs_status_file}')

# 更新.env配置（如果存在）
env_file = base_dir / '.env'
if env_file.exists():
    with open(env_file, 'r', encoding='utf-8') as f:
        env_content = f.read()
    snippet = f'XHS_COOKIE={cookie_string[:100]}...'
    if 'XHS_COOKIE=' in env_content:
        import re
        env_content = re.sub(r'XHS_COOKIE=.*', snippet, env_content)
    else:
        env_content += f'\n# 小红书Cookie\nXHS_COOKIE={snippet}\n'
    with open(env_file, 'w', encoding='utf-8') as f:
        f.write(env_content)
    print('✅ .env配置已更新')

print()
print('=' * 50)
print('  小红书Cookie导入完成！')
print('=' * 50)
print(f'Cookie数量: {len(xhs_cookies)}')
print(f'是否含 web_session: {bool(web_session)}')
print()
print('现在采集器可以使用这些Cookie进行小红书数据采集了！')
