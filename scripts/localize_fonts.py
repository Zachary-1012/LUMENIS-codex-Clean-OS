import os

# 1. 修改base.html
with open('templates/base.html', 'r', encoding='utf-8') as f:
    content = f.read()

old = """  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Noto+Sans+SC:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">"""

new = """  <!-- P0-R6: 字体本地化 — 本地woff2缓存，断网可用，font-display:swap -->
  <link rel="stylesheet" href="{{ url_for('static', filename='fonts/fonts.css') }}">"""

if old in content:
    content = content.replace(old, new, 1)
    with open('templates/base.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print('base.html: OK')
else:
    print('base.html: old string not found')

# 2. 修改cth/launch.html
with open('templates/cth/launch.html', 'r', encoding='utf-8') as f:
    content = f.read()

old2 = """  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Noto+Sans+SC:wght@300;400;500;600;700&display=swap" rel="stylesheet">"""

new2 = """  <!-- P0-R6: 字体本地化 -->
  <link rel="stylesheet" href="/static/fonts/fonts.css">"""

if old2 in content:
    content = content.replace(old2, new2, 1)
    with open('templates/cth/launch.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print('cth/launch.html: OK')
else:
    print('cth/launch.html: old string not found')

# 3. 修改zbmp/launch.html
with open('templates/zbmp/launch.html', 'r', encoding='utf-8') as f:
    content = f.read()

old3 = """  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Noto+Sans+SC:wght@300;400;500;600;700&display=swap" rel="stylesheet">"""

new3 = """  <!-- P0-R6: 字体本地化 -->
  <link rel="stylesheet" href="/static/fonts/fonts.css">"""

if old3 in content:
    content = content.replace(old3, new3, 1)
    with open('templates/zbmp/launch.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print('zbmp/launch.html: OK')
else:
    print('zbmp/launch.html: old string not found')

# 4. 修改zbc-design-v1.1.css - 移除@import Google Fonts
with open('static/css/zbc-design-v1.1.css', 'r', encoding='utf-8') as f:
    content = f.read()

old4 = """@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Noto+Sans+SC:wght@300;400;500;600;700&display=swap');"""

new4 = """/* P0-R6: 字体本地化 — Google Fonts @import已移除，改用static/fonts/fonts.css本地woff2 */"""

if old4 in content:
    content = content.replace(old4, new4, 1)
    with open('static/css/zbc-design-v1.1.css', 'w', encoding='utf-8') as f:
        f.write(content)
    print('zbc-design-v1.1.css: OK')
else:
    print('zbc-design-v1.1.css: old string not found')

print('\nAll font localization changes complete.')
