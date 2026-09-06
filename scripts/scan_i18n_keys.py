import os, re, json

# 1. 扫描所有templates/*.html中的data-i18n属性
template_keys = set()
for root, dirs, files in os.walk('templates'):
    for f in files:
        if f.endswith('.html'):
            path = os.path.join(root, f)
            with open(path, 'r', encoding='utf-8') as fh:
                content = fh.read()
            for m in re.finditer(r'''data-i18n=["']([^"']+)["']''', content):
                template_keys.add(m.group(1))
            for m in re.finditer(r'''data-i18n-placeholder=["']([^"']+)["']''', content):
                template_keys.add(m.group(1))
            for m in re.finditer(r'''data-i18n-aria=["']([^"']+)["']''', content):
                template_keys.add(m.group(1))

print('=== Template data-i18n keys ({}) ==='.format(len(template_keys)))
for k in sorted(template_keys):
    print('  ' + k)

# 2. 扫描static/js/*.js中的t()调用
js_keys = set()
for root, dirs, files in os.walk('static/js'):
    for f in files:
        if f.endswith('.js'):
            path = os.path.join(root, f)
            with open(path, 'r', encoding='utf-8') as fh:
                content = fh.read()
            for m in re.finditer(r'''(?:LUMENIS\.i18n\.|i18n\.)?t\(["']([a-zA-Z0-9_.\-]+)["']''', content):
                key = m.group(1)
                if '.' in key and len(key) > 2:
                    js_keys.add(key)

print('\n=== JS t() keys ({}) ==='.format(len(js_keys)))
for k in sorted(js_keys):
    print('  ' + k)

all_keys = template_keys | js_keys
print('\n=== Total unique keys: {} ==='.format(len(all_keys)))

# 3. 加载现有locale文件
def load_locale(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print('Error loading {}: {}'.format(path, e))
        return {}

zh = load_locale('static/locales/zh-CN.json')
en = load_locale('static/locales/en.json')
ko = load_locale('static/locales/ko.json')

def flatten(obj, prefix=''):
    keys = set()
    for k, v in obj.items():
        full = prefix + '.' + k if prefix else k
        if isinstance(v, dict):
            keys.update(flatten(v, full))
        else:
            keys.add(full)
    return keys

zh_keys = flatten(zh)
en_keys = flatten(en)
ko_keys = flatten(ko)

print('\n=== Locale file key counts ===')
print('  zh-CN: {}'.format(len(zh_keys)))
print('  en: {}'.format(len(en_keys)))
print('  ko: {}'.format(len(ko_keys)))

# 4. 找出missing key
missing_zh = all_keys - zh_keys
missing_en = all_keys - en_keys
missing_ko = all_keys - ko_keys

print('\n=== Missing in zh-CN ({}) ==='.format(len(missing_zh)))
for k in sorted(missing_zh):
    print('  ' + k)
print('\n=== Missing in en ({}) ==='.format(len(missing_en)))
for k in sorted(missing_en):
    print('  ' + k)
print('\n=== Missing in ko ({}) ==='.format(len(missing_ko)))
for k in sorted(missing_ko):
    print('  ' + k)
