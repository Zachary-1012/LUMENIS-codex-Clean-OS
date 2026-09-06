import json

# 读取三个locale文件
with open('static/locales/zh-CN.json', 'r', encoding='utf-8') as f:
    zh = json.load(f)
with open('static/locales/en.json', 'r', encoding='utf-8') as f:
    en = json.load(f)
with open('static/locales/ko.json', 'r', encoding='utf-8') as f:
    ko = json.load(f)

# 需要补齐的全局key（非页面级内联字典的key）
# nav.browser: 用户报告的控制台missing key
# common.*: 全局通用词条
# status.connecting: 全局状态词条
updates = {
    'nav': {
        'browser': {'zh': '浏览器', 'en': 'Browser', 'ko': '브라우저'},
    },
    'common': {
        'detail': {'zh': '详情', 'en': 'Detail', 'ko': '__missing__'},
        'source': {'zh': '来源', 'en': 'Source', 'ko': '__missing__'},
        'status': {'zh': '状态', 'en': 'Status', 'ko': '__missing__'},
        'time': {'zh': '时间', 'en': 'Time', 'ko': '__missing__'},
        'type': {'zh': '类型', 'en': 'Type', 'ko': '__missing__'},
    },
    'status': {
        'connecting': {'zh': '连接中', 'en': 'Connecting', 'ko': '__missing__'},
    },
}

def update_locale(locale_dict, lang):
    added = []
    for section, keys in updates.items():
        if section not in locale_dict:
            locale_dict[section] = {}
        for key, translations in keys.items():
            if key not in locale_dict[section]:
                locale_dict[section][key] = translations[lang]
                added.append('{}.{} = {}'.format(section, key, translations[lang]))
    return added

zh_added = update_locale(zh, 'zh')
en_added = update_locale(en, 'en')
ko_added = update_locale(ko, 'ko')

# 写回文件
with open('static/locales/zh-CN.json', 'w', encoding='utf-8') as f:
    json.dump(zh, f, ensure_ascii=False, indent=2)
    f.write('\n')
with open('static/locales/en.json', 'w', encoding='utf-8') as f:
    json.dump(en, f, ensure_ascii=False, indent=2)
    f.write('\n')
with open('static/locales/ko.json', 'w', encoding='utf-8') as f:
    json.dump(ko, f, ensure_ascii=False, indent=2)
    f.write('\n')

print('=== zh-CN added ({}) ==='.format(len(zh_added)))
for a in zh_added:
    print('  ' + a)
print('\n=== en added ({}) ==='.format(len(en_added)))
for a in en_added:
    print('  ' + a)
print('\n=== ko added ({}) ==='.format(len(ko_added)))
for a in ko_added:
    print('  ' + a)

# 验证nav.browser存在
print('\n=== Verification ===')
print('zh-CN nav.browser:', zh['nav'].get('browser'))
print('en nav.browser:', en['nav'].get('browser'))
print('ko nav.browser:', ko['nav'].get('browser'))
