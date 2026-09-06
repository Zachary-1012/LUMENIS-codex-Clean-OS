import re

with open('static/js/ai-assistant.js', 'r', encoding='utf-8') as f:
    content = f.read()

old_line = "      '@media(max-width:600px){#zbc-ai-panel{right:12px;left:12px;width:auto;bottom:76px;height:calc(100vh - 100px)}#zbc-ai-fab{bottom:16px;right:16px;width:46px;height:46px}}'"

new_lines = [
    "      '/* P0-R6: A3浮球安全边距 — 主内容区右侧/底部留出安全区，避免浮球遮挡卡片内容/图例/横向叠层卡 */',",
    "      '.zbc-content{padding-right:88px!important;padding-bottom:88px!important}',",
    "      '/* 移动端：浮球上移至Tab Bar上方，避免遮挡底部导航 */',",
    "      '@media(max-width:768px){.zbc-content{padding-right:70px!important;padding-bottom:130px!important}#zbc-ai-fab{bottom:72px!important}}',",
    "      '@media(max-width:600px){#zbc-ai-panel{right:12px;left:12px;width:auto;bottom:130px;height:calc(100vh - 150px)}#zbc-ai-fab{bottom:72px!important;right:16px;width:46px;height:46px}}'",
]

if old_line in content:
    content = content.replace(old_line, '\n'.join(new_lines), 1)
    with open('static/js/ai-assistant.js', 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS: ai-assistant.js FAB safe zone added')
else:
    print('FAILED: old line not found')
    idx = content.find('max-width:600px')
    print(repr(content[idx-50:idx+200]))
