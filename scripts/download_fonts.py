import re, os, urllib.request, hashlib

# 读取Google Fonts CSS
with open('static/fonts/google-fonts.css', 'r', encoding='utf-8') as f:
    css = f.read()

# 解析所有@font-face块
font_face_pattern = re.compile(
    r'/\*\s*([^*]+?)\s*\*/\s*@font-face\s*\{([^}]+)\}',
    re.DOTALL
)

# 提取每个@font-face的信息
fonts = []
for match in font_face_pattern.finditer(css):
    unicode_range_comment = match.group(1).strip()
    block = match.group(2)

    font_family = re.search(r"font-family:\s*'([^']+)'", block)
    font_weight = re.search(r'font-weight:\s*(\d+)', block)
    src_url = re.search(r"src:\s*url\(([^)]+)\)", block)
    unicode_range = re.search(r'unicode-range:\s*([^;]+);', block)

    if font_family and src_url:
        fonts.append({
            'family': font_family.group(1),
            'weight': font_weight.group(1) if font_weight else '400',
            'url': src_url.group(1),
            'unicode_range': unicode_range.group(1).strip() if unicode_range else '',
            'range_name': unicode_range_comment,
        })

print('Found {} @font-face declarations'.format(len(fonts)))
for fam in set(f['family'] for f in fonts):
    count = sum(1 for f in fonts if f['family'] == fam)
    weights = set(f['weight'] for f in fonts if f['family'] == fam)
    print('  {}: {} files, weights: {}'.format(fam, count, sorted(weights)))

# 下载字体文件
os.makedirs('static/fonts', exist_ok=True)
downloaded = 0
failed = 0
total_size = 0

for font in fonts:
    # 生成本地文件名: family-weight-rangehash.woff2
    url = font['url']
    range_hash = hashlib.md5(font['unicode_range'].encode()).hexdigest()[:8]
    family_safe = font['family'].replace(' ', '-').lower()
    local_name = '{}-{}-{}.woff2'.format(family_safe, font['weight'], range_hash)
    local_path = os.path.join('static/fonts', local_name)

    font['local_file'] = local_name

    if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
        total_size += os.path.getsize(local_path)
        downloaded += 1
        continue

    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
            with open(local_path, 'wb') as f:
                f.write(data)
            total_size += len(data)
            downloaded += 1
    except Exception as e:
        print('  FAILED: {} - {}'.format(local_name, e))
        failed += 1

print('\nDownloaded: {} files, {} failed, total size: {:.1f} MB'.format(
    downloaded, failed, total_size / (1024 * 1024)))

# 生成本地化CSS
local_css_parts = []
for font in fonts:
    if 'local_file' not in font:
        continue
    local_css_parts.append("/* {} */\n@font-face {{\n  font-family: '{}';\n  font-style: normal;\n  font-weight: {};\n  font-display: swap;\n  src: url('{}') format('woff2');\n  unicode-range: {};\n}}".format(
        font['range_name'], font['family'], font['weight'], font['local_file'], font['unicode_range']
    ))

local_css = '\n\n'.join(local_css_parts)
with open('static/fonts/fonts.css', 'w', encoding='utf-8') as f:
    f.write('/* LUMENIS 字体本地化 — Inter / Noto Sans SC / JetBrains Mono */\n')
    f.write('/* 来源: Google Fonts, 本地woff2缓存, font-display:swap 断网可用 */\n')
    f.write('/* 生成时间: 2026-09-07 */\n\n')
    f.write(local_css)

print('\nLocal fonts.css generated: {} @font-face rules'.format(len(local_css_parts)))
