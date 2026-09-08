"""Navigation Restructure Validation Script"""
import re
import json
import sys

# 1. Extract all url_for endpoints from base.html
with open('templates/base.html', 'r', encoding='utf-8') as f:
    content = f.read()

endpoints = re.findall(r"url_for\('([^']+)'\)", content)
unique_endpoints = sorted(set(endpoints))
print(f"=== Endpoints in template: {len(unique_endpoints)} ===")
for ep in unique_endpoints:
    print(f"  {ep}")

# 2. Extract all data-icon values and check against icon registry
icons_used = re.findall(r'data-icon="([^"]+)"', content)
unique_icons = sorted(set(icons_used))
print(f"\n=== Icons used in template: {len(unique_icons)} ===")

# Load icon registry
with open('static/js/lumenis-icons.js', 'r', encoding='utf-8') as f:
    js_content = f.read()
registered_icons = re.findall(r'^\s{4}(\w+):', js_content, re.MULTILINE)
print(f"Registered icons: {len(registered_icons)}")

missing_icons = [i for i in unique_icons if i not in registered_icons]
if missing_icons:
    print(f"MISSING ICONS ({len(missing_icons)}): {missing_icons}")
else:
    print("All icons exist in registry!")

# 3. Check for data-i18n keys
i18n_keys = re.findall(r'data-i18n="([^"]+)"', content)
unique_i18n = sorted(set(i18n_keys))
print(f"\n=== i18n keys in template: {len(unique_i18n)} ===")

# Load zh-CN locale
with open('static/locales/zh-CN.json', 'r', encoding='utf-8') as f:
    locale = json.load(f)

missing_i18n = [k for k in unique_i18n if k not in locale]
if missing_i18n:
    print(f"MISSING I18N KEYS ({len(missing_i18n)}):")
    for k in missing_i18n:
        print(f"  {k}")
else:
    print("All i18n keys exist in zh-CN locale!")

# 4. Check that "太古汇" is NOT an independent nav item
if '太古汇' in content and 'nav-item__label' in content:
    # Find context
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if '太古汇' in line:
            print(f"\nWARNING: '太古汇' found at line {i+1}: {line.strip()[:100]}")
else:
    print("\n'太古汇' not found as independent nav item - OK!")

# 5. Count nav sections (functional areas)
cth_sections = len(re.findall(r'data-nav-section', content.split('zbc-nav-group--cth')[1].split('zbc-nav-group--system')[0])) if 'zbc-nav-group--cth' in content else 0
zbmp_sections = len(re.findall(r'data-nav-section', content.split('zbc-nav-group--zbmp')[1].split('zbc-nav-group--cth')[0])) if 'zbc-nav-group--zbmp' in content else 0
print(f"\n=== Functional area count ===")
print(f"CTH nav-sections: {cth_sections} (expected ~11: 10 areas + system)")
print(f"ZBMP nav-sections: {zbmp_sections} (expected ~14: 13 areas + system)")

# 6. Check for PARTIAL badges
partial_count = content.count('zbc-badge--partial')
print(f"\nPARTIAL badges: {partial_count}")

print("\n=== VALIDATION COMPLETE ===")
