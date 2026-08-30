# -*- coding: utf-8 -*-
"""修改base.py增加QR_REQUIRED状态"""
path = r'D:\Taikoo-monitor-new\platform_adapters\base.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old = '    NEED_VERIFY = "NEED_VERIFY"\n    BLOCKED = "BLOCKED"'
new = '    NEED_VERIFY = "NEED_VERIFY"\n    QR_REQUIRED = "QR_REQUIRED"  # V3.0 P0: 需要扫码恢复\n    BLOCKED = "BLOCKED"'

if old in content:
    content = content.replace(old, new)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('base.py已更新，增加QR_REQUIRED状态')
else:
    print('未找到匹配字符串')
    for i, line in enumerate(content.split('\n')):
        if 'NEED_VERIFY' in line or 'BLOCKED' in line:
            print(f'  行{i}: {repr(line)}')
