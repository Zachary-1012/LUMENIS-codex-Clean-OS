"""Online display migration only; runtime and installed-app identities stay compatible."""
import json
import plistlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TAGLINE = 'An Open Space for Thought and Creation.'

def read(path):
    return (ROOT / path).read_text(encoding='utf-8')

def test_canonical_display_profile_keeps_technical_schema():
    profile = json.loads(read('contracts/experience/i18n/naming-profile.json'))
    assert profile['product_name'] == '寰意 OEVIRA'
    assert profile['wordmark'] == profile['korean_name'] == 'OEVIRA'
    assert profile['tagline'] == TAGLINE
    assert profile['domain'] == 'oevira.com'
    assert profile['$schema'] == 'lumenis.design/naming-profile-v2.5'

def test_three_locale_sources_have_matching_keys_and_new_display_names():
    translations = [json.loads(read(f'contracts/experience/i18n/{x}.delta.json'))['delta'] for x in ('zh-CN', 'en', 'ko')]
    assert set(translations[0]) == set(translations[1]) == set(translations[2])
    assert [t['product.name'] for t in translations] == ['寰意 OEVIRA', 'OEVIRA', 'OEVIRA']
    for table in translations:
        assert table['product.tagline'] == TAGLINE
        assert all(not any(old in value for old in ('序境', 'LUMENIS', '서경')) for value in table.values())

def test_generated_copy_has_new_display_values_but_compatible_symbol():
    generated = read('app/lib/l10n/lumenis_copy.g.dart')
    assert 'GENERATED FILE. Do not edit directly.' in generated
    assert 'lumenisCopy' in generated
    assert '寰意 OEVIRA' in generated and TAGLINE in generated
    assert '序境' not in generated and '서경' not in generated and 'LUMENIS' not in generated

def test_web_identity_uses_new_name_without_enabling_deployment():
    copy = read('website/src/i18n.ts')
    assert TAGLINE in copy and '寰意 OEVIRA' in copy
    assert '序境' not in copy and 'LUMENIS' not in copy and '서경' not in copy
    config = read('website/astro.config.mjs')
    assert 'process.env.LUMENIS_PUBLIC_SITE_ORIGIN' in config
    assert 'if (!value) return undefined' in config
    assert 'oevira.com' not in config  # identity does not turn on a deployment/indexing config
    assert '发展愿景' in copy and 'not a claim' in copy

def test_native_display_and_package_identity_are_separate():
    for platform in ('ios', 'macos'):
        info = plistlib.loads((ROOT / f'app/{platform}/Runner/Info.plist').read_bytes())
        assert info['CFBundleDisplayName'] == info['CFBundleName'] == '寰意'
        assert info['CFBundleIdentifier'] == '$(PRODUCT_BUNDLE_IDENTIFIER)'
        assert info['CFBundleExecutable'] == '$(EXECUTABLE_NAME)'
    rc = read('app/windows/runner/Runner.rc')
    assert 'VALUE "ProductName", "OEVIRA"' in rc
    assert 'VALUE "FileDescription", "OEVIRA"' in rc
    assert 'VALUE "OriginalFilename", "lumenis_app.exe"' in rc
    assert 'VALUE "InternalName", "lumenis_app"' in rc
    assert 'name: lumenis_app\n' in read('app/pubspec.yaml')
    assert 'PRODUCT_BUNDLE_IDENTIFIER = com.lumenis.lumenisApp' in read('app/macos/Runner/Configs/AppInfo.xcconfig')

def test_app_wire_and_environment_contracts_remain_compatible():
    client = read('app/lib/core/lumenis_core_client.dart')
    assert "'LUMENIS_CORE_BASE_URL'" in client
    assert "'LUMENIS_CORE_URL'" in client
    assert "'X-LUMENIS-Human-Control-Lease'" in client
    assert "response['product'] != 'LUMENIS'" in read('app/lib/features/shared/sh01/sh01_snapshot.dart')
    assert "title: '寰意 · OEVIRA'" in read('app/lib/product/lumenis_app.dart')
    assert '寰意 / OEVIRA' in read('app/lib/shell/lumenis_workspace_shell.dart')
