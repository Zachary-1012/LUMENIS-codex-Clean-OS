"""
Cookie导入工具
将用户提供的微博和B站cookie导入系统
"""
import json
import os
from pathlib import Path
from datetime import datetime

base_dir = Path(__file__).resolve().parent
data_dir = base_dir / 'data'
data_dir.mkdir(exist_ok=True)

# ============================================
# 微博Cookie
# ============================================
weibo_cookies = [
    {
        "name": "PC_TOKEN",
        "value": "b0bec63259",
        "domain": ".weibo.com",
        "path": "/",
        "expires": "2026-08-28T03:59:26.918Z",
        "httpOnly": False,
        "secure": True,
        "sameSite": "Medium"
    },
    {
        "name": "SCF",
        "value": "AnD7qyEAUAUYwf8za1k-oBtzbokaxKtU1ZQoQPasHKttLo9_RufOa93qbjWzKdXREKW_PeXbFGrW6W6QgduIlsY..",
        "domain": ".weibo.com",
        "path": "/",
        "expires": "2027-10-02T03:29:55.603Z",
        "httpOnly": True,
        "secure": True,
        "sameSite": "None"
    },
    {
        "name": "SUB",
        "value": "_2A25HlXDkDeRhGeBP4lQR-CjLzzSIHXVk64wsrDV8PUNbmtAYLWLGkW9NRCculg-E9WOSBR30A-oxrqvflQGe4_Fz",
        "domain": ".weibo.com",
        "path": "/",
        "expires": "2027-08-28T03:29:55.603Z",
        "httpOnly": True,
        "secure": True,
        "sameSite": "None"
    },
    {
        "name": "SUBP",
        "value": "0033WrSXqPxfM725Ws9jqgMF55529P9D9WhHTOvxEPVroiRswQmVfnCW5JpX5KzhUgL.Foqp1Kq71hqNShn2dJLoIp7LxKML1KBLBKnLxKqL1hnLBoMceK.cehncS0BR",
        "domain": ".weibo.com",
        "path": "/",
        "expires": "2027-08-28T03:29:55.603Z",
        "httpOnly": True,
        "secure": False,
        "sameSite": "Medium"
    },
    {
        "name": "WBPSESS",
        "value": "A7UESSvGuxW8YB5Om8BVaL0FD3NoncpEdXLiC3UtqeG0BXtSx19USynOUFYFCUCUMnuw6MNXD9RFsYmL2CVjkYNfVBoOoAVD4uC070GXp3aRF7RaWAq06LFN6PSDJQuieR-b0qply6Hqoj6XtBBWug==",
        "domain": ".weibo.com",
        "path": "/",
        "expires": "2026-08-29T03:29:56.495Z",
        "httpOnly": True,
        "secure": True,
        "sameSite": "Medium"
    },
    {
        "name": "XSRF-TOKEN",
        "value": "Tr8WI26ce7udUETBZ1SeqtmF",
        "domain": "weibo.com",
        "path": "/",
        "expires": "Session",
        "httpOnly": True,
        "secure": False,
        "sameSite": "Medium"
    }
]

# 保存微博cookie
weibo_cookie_file = data_dir / 'weibo_cookies.json'
with open(weibo_cookie_file, 'w', encoding='utf-8') as f:
    json.dump(weibo_cookies, f, ensure_ascii=False, indent=2)
print(f'✅ 微博Cookie已保存: {weibo_cookie_file} ({len(weibo_cookies)}个)')

# 保存微博登录状态
weibo_status_file = data_dir / 'weibo_login_status.json'
weibo_status = {
    'logged_in': True,
    'last_login': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'cookie_count': len(weibo_cookies),
    'login_method': 'cookie_import'
}
with open(weibo_status_file, 'w', encoding='utf-8') as f:
    json.dump(weibo_status, f, ensure_ascii=False, indent=2)
print(f'✅ 微博登录状态已保存: {weibo_status_file}')

# ============================================
# B站Cookie
# ============================================
bilibili_cookies = [
    {"name": "b_lsid", "value": "747B24E0_1A04678E6", "domain": ".bilibili.com", "path": "/", "expires": "Session", "httpOnly": False, "secure": False, "sameSite": "Medium"},
    {"name": "b_nut", "value": "1787887847", "domain": ".bilibili.com", "path": "/", "expires": "2027-08-28T03:30:46.508Z", "httpOnly": False, "secure": False, "sameSite": "Medium"},
    {"name": "bili_jct", "value": "cfec3f2006af1cde16fa31a3448a0b9", "domain": ".bilibili.com", "path": "/", "expires": "2027-02-24T03:31:34.807Z", "httpOnly": True, "secure": False, "sameSite": "None"},
    {"name": "bili_ticket", "value": "eyJhbGciOiJIUzI1NiIsImtpZCI6InMwMyIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3ODgxNDcwNTksImlhdCI6MTc4Nzg4Nzc5OSwicGx0IjotMX0.mN9jzTQHtoGa__IyEENQONPj5bZVGjkE7m2TcdGdYCs", "domain": ".bilibili.com", "path": "/", "expires": "2026-08-31T03:30:58.000Z", "httpOnly": False, "secure": False, "sameSite": "Medium"},
    {"name": "bili_ticket_expires", "value": "1788146999", "domain": ".bilibili.com", "path": "/", "expires": "2026-08-31T03:30:58.000Z", "httpOnly": False, "secure": False, "sameSite": "Medium"},
    {"name": "browser_resolution", "value": "311-740", "domain": ".bilibili.com", "path": "/", "expires": "2027-08-28T03:45:26.000Z", "httpOnly": False, "secure": False, "sameSite": "Medium"},
    {"name": "bsource", "value": "search_bing", "domain": ".bilibili.com", "path": "/", "expires": "Session", "httpOnly": False, "secure": False, "sameSite": "Medium"},
    {"name": "buvid_fp", "value": "991ebb84692067f12825060c365823b", "domain": ".bilibili.com", "path": "/", "expires": "2027-10-02T03:30:49.804Z", "httpOnly": False, "secure": False, "sameSite": "Medium"},
    {"name": "buvid3", "value": "A1288504-37D8-D84B-20E7-13C26BF49124", "domain": ".bilibili.com", "path": "/", "expires": "2027-08-28T03:30:46.507Z", "httpOnly": False, "secure": False, "sameSite": "Medium"},
    {"name": "buvid4", "value": "5A44FEB1-DB21-66AF-AB32-45602AB0183D", "domain": ".bilibili.com", "path": "/", "expires": "2027-10-02T03:45:23.789Z", "httpOnly": False, "secure": False, "sameSite": "Medium"},
    {"name": "CURRENT_FNVAL", "value": "2000", "domain": ".bilibili.com", "path": "/", "expires": "2027-08-28T03:45:19.000Z", "httpOnly": False, "secure": False, "sameSite": "Medium"},
    {"name": "DedeUserID", "value": "288610300", "domain": ".bilibili.com", "path": "/", "expires": "2027-02-24T03:31:34.807Z", "httpOnly": True, "secure": False, "sameSite": "None"},
    {"name": "DedeUserID__ckMd5", "value": "835c855b1c86ddb3", "domain": ".bilibili.com", "path": "/", "expires": "2027-02-24T03:31:34.807Z", "httpOnly": True, "secure": False, "sameSite": "None"},
    {"name": "home_feed_column", "value": "4", "domain": ".bilibili.com", "path": "/", "expires": "2027-08-28T03:45:24.000Z", "httpOnly": False, "secure": False, "sameSite": "Medium"},
    {"name": "SESSDATA", "value": "3d445c48%2C1803439895%2C0b7ef%2A82CjA2NRee1EC_GW3bnwgPNFuNZtNp4NhTRx1dgZt0chMLjN8tVMfvqlA0niF4eS4MmkwSVlJyNmR3aFZMTHk4eVladndmQVBTb3BEOWtZM0luX2p6MzFPV3Q5MzlZakZKMm5UeXkzbm01NHlRX1hFa3NPNHJoWlU4amtXa3BkLWxqbHpwMGplUFBBIIEC", "domain": ".bilibili.com", "path": "/", "expires": "2027-02-24T03:31:34.807Z", "httpOnly": True, "secure": True, "sameSite": "None"},
    {"name": "sid", "value": "72577na9", "domain": ".bilibili.com", "path": "/", "expires": "Session", "httpOnly": False, "secure": False, "sameSite": "Medium"},
    {"name": "theme-tip-show", "value": "SHOWED", "domain": ".bilibili.com", "path": "/", "expires": "2027-08-28T03:31:36.000Z", "httpOnly": False, "secure": False, "sameSite": "Medium"}
]

# 保存B站cookie
bilibili_cookie_file = data_dir / 'bilibili_cookies.json'
with open(bilibili_cookie_file, 'w', encoding='utf-8') as f:
    json.dump(bilibili_cookies, f, ensure_ascii=False, indent=2)
print(f'✅ B站Cookie已保存: {bilibili_cookie_file} ({len(bilibili_cookies)}个)')

# 保存B站登录状态
bilibili_status_file = data_dir / 'bilibili_login_status.json'
bilibili_status = {
    'logged_in': True,
    'last_login': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'cookie_count': len(bilibili_cookies),
    'user_id': '288610300',
    'login_method': 'cookie_import'
}
with open(bilibili_status_file, 'w', encoding='utf-8') as f:
    json.dump(bilibili_status, f, ensure_ascii=False, indent=2)
print(f'✅ B站登录状态已保存: {bilibili_status_file}')

print()
print('=' * 50)
print('  Cookie导入完成！')
print('=' * 50)
print(f'微博: {len(weibo_cookies)}个Cookie')
print(f'B站: {len(bilibili_cookies)}个Cookie')
print(f'用户ID: 288610300')
print()
print('现在可以启用全网话题搜集（微博+B站）了！')
