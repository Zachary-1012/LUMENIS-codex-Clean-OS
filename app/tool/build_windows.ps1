#requires -Version 7.2
<#
.SYNOPSIS
Build the existing Windows app through a verified ASCII path to the same files.
.DESCRIPTION
Some Flutter gen_snapshot builds decode Windows narrow argv as UTF-8 although
the CRT supplies the system code page. A junction avoids non-ASCII arguments
without copying source, patching the SDK or changing persistent settings. When
plugin symlinks are nested below that junction, a temporary SUBST drive maps
the repository root and addresses the same app at `R:\app`, avoiding Windows
reparse traversal failures while keeping CMake's project path below the drive root.
The junction is kept for repeat builds. Never remove it with recursive deletion.
#>
[CmdletBinding()]
param(
    [string]$FlutterSdk = '',
    [ValidateSet('release', 'profile', 'debug')][string]$Mode = 'release',
    [string]$AliasRoot = (Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'Lumenis/build-paths'),
    [string]$ProjectAlias = '',
    [switch]$StaticImportDiagnostics,
    [string]$PythonExecutable = '',
    [string]$DumpbinPath = '',
    [switch]$BundleOnly,
    [switch]$BuildWeb,
    [string]$BundleOutput = '',
    [string[]]$PythonSitePackages = @(),
    [string]$MediaDirectory = '',
    [string[]]$MediaNotices = @(),
    [string]$CoreBaseUrl = '',
    [string]$AppCoreBaseUrl = '',
    [string]$VCRuntimeDirectory = '',
    [string[]]$VCRuntimeNotices = @()
)


# Optional, bounded post-build observation. It never changes build success or
# executes the inspected app; missing diagnostics remain explicitly unverified.
function Invoke-LumenisStaticImportObservation {
    param([string]$Binary, [string]$ExpectedHash, [string]$Helper,
          [string]$Python, [string]$Dumpbin, [string]$Output)
    $result = [ordered]@{ status = 'NOT_VERIFIED'; runtime_verified = $false;
        dependency_resolution_verified = $false; current_source_build_verified = $false;
        result_reference = $null; result_sha256 = $null }
    if ([string]::IsNullOrWhiteSpace($Python) -or
        [string]::IsNullOrWhiteSpace($Dumpbin) -or
        -not [IO.Path]::IsPathFullyQualified($Python) -or
        -not [IO.Path]::IsPathFullyQualified($Dumpbin) -or
        -not (Test-Path -LiteralPath $Python -PathType Leaf) -or
        -not (Test-Path -LiteralPath $Dumpbin -PathType Leaf) -or
        -not (Test-Path -LiteralPath $Helper -PathType Leaf)) {
        $result.status = 'TOOL_NOT_AVAILABLE'
        return $result
    }
    $process = $null
    try {
        $start = [Diagnostics.ProcessStartInfo]::new()
        $start.FileName = $Python
        $start.UseShellExecute = $false
        $start.RedirectStandardOutput = $true
        $start.RedirectStandardError = $true
        $start.CreateNoWindow = $true
        foreach ($arg in @('-B', '-X', 'utf8', $Helper, '--binary', $Binary,
                           '--dumpbin', $Dumpbin, '--timeout', '15')) {
            $start.ArgumentList.Add($arg)
        }
        $process = [Diagnostics.Process]::new()
        $process.StartInfo = $start
        if (-not $process.Start()) { throw 'DIAGNOSTIC_START_FAILED' }
        $stdout = $process.StandardOutput.ReadToEndAsync()
        $stderr = $process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit(20000)) {
            $process.Kill($true)
            $process.WaitForExit(3000) | Out-Null
            $result.status = 'TIMEOUT_NOT_VERIFIED'
            return $result
        }
        if (-not $stdout.Wait(3000) -or -not $stderr.Wait(3000)) {
            $result.status = 'OUTPUT_NOT_VERIFIED'
            return $result
        }
        $raw = $stdout.Result
        if ($process.ExitCode -ne 0 -or $raw.Length -gt 65536) {
            $result.status = 'DIAGNOSTIC_NOT_VERIFIED'
            return $result
        }
        $observation = $raw | ConvertFrom-Json -AsHashtable -ErrorAction Stop
        if ($observation.schema -ne 'lumenis.static-import-observation.v1' -or
            $observation.status -ne 'IMPORTS_OBSERVED' -or
            $observation.binary_sha256 -ne $ExpectedHash -or
            $observation.runtime_verified -ne $false -or
            $observation.dependency_resolution_verified -ne $false -or
            $observation.current_source_build_verified -ne $false -or
            $observation.binary_unchanged -ne $true) {
            $result.status = 'OUTPUT_NOT_VERIFIED'
            return $result
        }
        $currentHash = (Get-FileHash -LiteralPath $Binary -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($currentHash -ne $ExpectedHash) {
            $result.status = 'BINARY_CHANGED_NOT_VERIFIED'
            return $result
        }
        # Output is the bounded helper's safe schema, never raw dumpbin stderr.
        [IO.Directory]::CreateDirectory((Split-Path -Parent $Output)) | Out-Null
        [IO.File]::WriteAllText($Output, $raw, [Text.UTF8Encoding]::new($false))
        $result.status = 'STATIC_IMPORTS_OBSERVED'
        $result.result_reference = $Output
        $result.result_sha256 = (Get-FileHash -LiteralPath $Output -Algorithm SHA256).Hash.ToLowerInvariant()
        return $result
    } catch {
        $result.status = 'DIAGNOSTIC_NOT_VERIFIED'
        return $result
    } finally {
        if ($null -ne $process) {
            try { if (-not $process.HasExited) { $process.Kill($true); $process.WaitForExit(3000) | Out-Null } } catch {}
            $process.Dispose()
        }
    }
}

# This is the existing build owner, not another Core implementation. The writer
# reads explicitly selected installed packages; it never runs pip or imports app.
# Path isolation: https://docs.python.org/3.13/using/windows.html#finding-modules
function Get-LumenisBundleWriter {
    return @'
# LUMENIS_BUNDLE_WRITER_BEGIN
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from importlib import metadata
from pathlib import Path, PurePosixPath


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def plain(path):
    path = Path(os.path.abspath(path))
    for ancestor in (path, *path.parents):
        try:
            attributes = ancestor.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(attributes.st_mode) or (
                getattr(attributes, 'st_file_attributes', 0) & 0x400):
            raise ValueError('Linked bundle inputs or destinations are not supported')
    return path


def within(path, root):
    return path == root or root in path.parents


def endpoint(url):
    match = re.fullmatch(r'http://127\.0\.0\.1:([0-9]{4,5})/?', url)
    if not match:
        raise ValueError('CoreBaseUrl must name an explicit HTTP IPv4 loopback port')
    port = int(match[1])
    if not 1024 <= port <= 65535 or port in {5000, 5001, 8200, 8201, 9222, 9223, 9224}:
        raise ValueError('The Core port is reserved or outside the manual Workspace range')
    return f'http://127.0.0.1:{port}', port


def inventory(root, excluded=()):
    root = plain(root)
    if not root.is_dir():
        raise ValueError('Build input/output directory is missing')
    result = []
    for current, directories, names in os.walk(root, followlinks=False):
        directories[:] = [name for name in directories
            if (Path(current) / name).relative_to(root).as_posix() not in excluded]
        for name in directories:
            plain(Path(current) / name)
        for name in sorted(names):
            source = plain(Path(current) / name)
            if not source.is_file():
                raise ValueError('Build inventories require plain files')
            result.append({'path': source.relative_to(root).as_posix(),
                           'sha256': sha(source), 'size': source.stat().st_size})
    return sorted(result, key=lambda item: item['path'])


def ui_sources(repo):
    # The same shared Flutter source snapshot is required for both targets.
    # Only hashes/relative names enter the receipt, never package-config paths
    # or developer environment contents. Platform runner sources are separate.
    app = plain(repo / 'app')
    result = []
    for name in ('lib', 'assets', 'web'):
        directory = app / name
        if directory.is_dir():
            result.extend({**entry, 'path': name + '/' + entry['path']}
                          for entry in inventory(directory))
    for name in ('pubspec.yaml', 'pubspec.lock', '.dart_tool/package_config.json'):
        path = plain(app / name)
        if not path.is_file():
            raise ValueError('Flutter source/locked dependency input is missing: ' + name)
        result.append({'path': name, 'sha256': sha(path), 'size': path.stat().st_size})
    if not any(entry['path'].startswith('lib/') for entry in result):
        raise ValueError('Flutter application sources are missing')
    return sorted(result, key=lambda item: item['path'])


def build_arguments(target, mode, core_url):
    core_url, _ = endpoint(core_url)
    if target not in {'web', 'windows'} or mode != 'release':
        raise ValueError('Portable build receipts require explicit release Web/Windows builds')
    return ['build', target, '--release', '--no-pub',
            '--dart-define=LUMENIS_CORE_BASE_URL=' + core_url]


def build_receipt_path(repo, target):
    return plain(repo / 'app/build/native-build-receipts' / ('verified-' + target + '.json'))


class _StandardMessageCodecReader:
    """Decode Flutter's generated StandardMessageCodec asset manifest."""
    def __init__(self, data):
        self.data = memoryview(data)
        self.offset = 0

    def _read(self, size):
        if size < 0 or self.offset + size > len(self.data):
            raise ValueError('Flutter AssetManifest.bin is truncated')
        start = self.offset
        self.offset += size
        return self.data[start:self.offset].tobytes()

    def _size(self):
        marker = self._read(1)[0]
        if marker < 254:
            return marker
        width = 2 if marker == 254 else 4
        return int.from_bytes(self._read(width), 'little')

    def _align(self, alignment):
        self.offset += (-self.offset) % alignment
        if self.offset > len(self.data):
            raise ValueError('Flutter AssetManifest.bin has invalid value alignment')

    def _value(self, depth=0):
        import struct
        if depth > 64:
            raise ValueError('Flutter AssetManifest.bin is nested too deeply')
        tag = self._read(1)[0]
        if tag == 0:
            return None
        if tag == 1:
            return True
        if tag == 2:
            return False
        if tag == 3:
            return int.from_bytes(self._read(4), 'little', signed=True)
        if tag == 4:
            return int.from_bytes(self._read(8), 'little', signed=True)
        if tag == 5:
            return self._read(self._size()).decode('utf-8')
        if tag == 6:
            self._align(8)
            return struct.unpack('<d', self._read(8))[0]
        if tag == 7:
            return self._read(self._size()).decode('utf-8')
        if tag == 8:
            return self._read(self._size())
        if tag in (9, 10, 11, 14):
            width = {9: 4, 10: 8, 11: 8, 14: 4}[tag]
            fmt = {9: '<i', 10: '<q', 11: '<d', 14: '<f'}[tag]
            self._align(width)
            count = self._size()
            return [struct.unpack(fmt, self._read(width))[0] for _ in range(count)]
        if tag == 12:
            count = self._size()
            if count > len(self.data) - self.offset:
                raise ValueError('Flutter AssetManifest.bin has an invalid list length')
            return [self._value(depth + 1) for _ in range(count)]
        if tag == 13:
            count = self._size()
            if count > (len(self.data) - self.offset) // 2:
                raise ValueError('Flutter AssetManifest.bin has an invalid map length')
            result = {}
            for _ in range(count):
                key = self._value(depth + 1)
                value = self._value(depth + 1)
                try:
                    if key in result:
                        raise ValueError('Flutter AssetManifest.bin contains a duplicate key')
                    result[key] = value
                except TypeError as exc:
                    raise ValueError('Flutter AssetManifest.bin contains an invalid map key') from exc
            return result
        raise ValueError('Flutter AssetManifest.bin contains an unsupported value tag')

    def decode(self):
        value = self._value()
        if self.offset != len(self.data):
            raise ValueError('Flutter AssetManifest.bin has trailing bytes')
        return value


def asset_manifest_paths(path):
    manifest = _StandardMessageCodecReader(path.read_bytes()).decode()
    if not isinstance(manifest, dict):
        raise ValueError('Flutter AssetManifest.bin must contain an asset map')
    paths = set()
    for key, variants in manifest.items():
        if not isinstance(key, str) or not isinstance(variants, list):
            raise ValueError('Flutter AssetManifest.bin contains an invalid asset entry')
        for variant in variants:
            if not isinstance(variant, dict) or not isinstance(variant.get('asset'), str):
                raise ValueError('Flutter AssetManifest.bin variant has no asset path')
            paths.add(variant['asset'])
    return sorted(paths)


def verify_flutter_assets(repo, target, root):
    import yaml  # Existing canonical PyYAML dependency; never parses executable YAML tags.
    spec = yaml.safe_load((repo / 'app/pubspec.yaml').read_text('utf-8'))
    flutter = spec.get('flutter', {})
    assets = plain(root / ('assets' if target == 'web' else 'data/flutter_assets'))

    def required(relative):
        rel = PurePosixPath(relative)
        if rel.is_absolute() or '..' in rel.parts or '\\' in relative:
            raise ValueError('Unsafe declared Flutter asset path')
        path = plain(assets.joinpath(*rel.parts))
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError('Required Flutter asset is missing/empty: ' + relative)
        return path

    asset_manifest = required('AssetManifest.bin')
    manifest_assets = asset_manifest_paths(asset_manifest)
    for name in manifest_assets:
        required(name)
    font_manifest = required('FontManifest.json')
    fonts = json.loads(font_manifest.read_text('utf-8'))
    if not isinstance(fonts, list):
        raise ValueError('Flutter FontManifest must contain a font family list')
    families = {}
    for entry in fonts:
        if not isinstance(entry, dict) or not isinstance(entry.get('family'), str) or not isinstance(entry.get('fonts'), list):
            raise ValueError('Flutter font manifest entry is invalid')
        entries = families.setdefault(entry['family'], set())
        for font in entry['fonts']:
            if not isinstance(font, dict) or not isinstance(font.get('asset'), str):
                raise ValueError('Flutter font asset identity is missing')
            required(font['asset'])
            entries.add(font['asset'])
    if flutter.get('uses-material-design') is True and 'fonts/MaterialIcons-Regular.otf' not in families.get('MaterialIcons', set()):
        raise ValueError('Required Flutter MaterialIcons font is missing')
    declared = set()
    for entry in flutter.get('assets', []):
        name = entry if isinstance(entry, str) else entry.get('path') if isinstance(entry, dict) else None
        if not isinstance(name, str):
            raise ValueError('Declared Flutter asset has no path')
        if name.endswith('/'):
            directory = plain(repo / 'app' / name)
            if not directory.is_dir():
                raise ValueError('Declared Flutter asset directory is missing')
            declared.update(path.relative_to(repo / 'app').as_posix()
                            for path in directory.iterdir() if path.is_file())
        else:
            declared.add(name)
    for family in flutter.get('fonts', []):
        name = family.get('family')
        for font in family.get('fonts', []):
            asset = font.get('asset')
            if asset not in families.get(name, set()):
                raise ValueError('Declared Flutter font family/asset is absent from FontManifest')
            declared.add(asset)
    checked = []
    for name in sorted(declared):
        built = required(name)
        original = plain(repo / 'app' / name)
        if not original.is_file() or sha(original) != sha(built):
            raise ValueError('Declared Flutter source asset differs from its bundled bytes: ' + name)
        checked.append({'path': name, 'sha256': sha(built), 'size': built.stat().st_size})
    return {'asset_manifest_sha256': sha(asset_manifest),
            'asset_manifest_asset_count': len(manifest_assets),
            'font_manifest_sha256': sha(font_manifest), 'declared_assets': checked,
            'font_families': sorted(families), 'runtime_acceptance': 'NOT_VERIFIED'}


def prepare_build(repo, target, mode, core_url, flutter, preparation):
    repo, flutter, preparation = map(plain, (repo, flutter, preparation))
    arguments = build_arguments(target, mode, core_url)
    if not flutter.is_file() or flutter.name.lower() != 'flutter.bat':
        raise ValueError('Build receipts require the actual selected Flutter entry')
    if preparation.parent != build_receipt_path(repo, target).parent:
        raise ValueError('Build proof must remain in the existing build receipt directory')
    sdk = flutter.parent.parent
    toolchain = []
    for name in ('bin/flutter.bat', 'bin/internal/engine.version', 'bin/cache/flutter.version.json'):
        path = plain(sdk / name)
        if not path.is_file():
            raise ValueError('Flutter toolchain identity is incomplete: ' + name)
        toolchain.append({'path': name, 'sha256': sha(path), 'size': path.stat().st_size})
    value = {'schema': 'lumenis.flutter-build-preparation/v1', 'target': target,
             'mode': mode, 'core_base_url': endpoint(core_url)[0], 'arguments': arguments,
             'sources': ui_sources(repo), 'toolchain': toolchain,
             'platform_sources': inventory(repo / 'app/windows', ('flutter/ephemeral',)) if target == 'windows' else []}
    preparation.parent.mkdir(parents=True, exist_ok=True)
    with preparation.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True)
    return value


def complete_build(repo, target, mode, core_url, flutter, preparation, exit_code):
    repo, flutter, preparation = map(plain, (repo, flutter, preparation))
    if exit_code != 0:
        raise ValueError('A failed Flutter invocation cannot publish a build receipt')
    expected_arguments = build_arguments(target, mode, core_url)
    before = json.loads(preparation.read_text('utf-8'))
    # Reuse the same snapshot implementation without writing a second record.
    if (before.get('schema') != 'lumenis.flutter-build-preparation/v1' or
            before.get('target') != target or before.get('mode') != mode or
            before.get('core_base_url') != endpoint(core_url)[0] or
            before.get('arguments') != expected_arguments or before.get('sources') != ui_sources(repo)):
        raise ValueError('Flutter build configuration/source changed during compilation')
    sdk = flutter.parent.parent
    for entry in before['toolchain']:
        if sha(plain(sdk / entry['path'])) != entry['sha256']:
            raise ValueError('Flutter toolchain changed during compilation')
    platform = inventory(repo / 'app/windows', ('flutter/ephemeral',)) if target == 'windows' else []
    if before['platform_sources'] != platform:
        raise ValueError('Flutter native source changed during compilation')
    root = repo / ('app/build/web' if target == 'web' else 'app/build/windows/x64/runner/Release')
    asset_contract = verify_flutter_assets(repo, target, root)
    outputs = inventory(root)
    required = {'index.html', 'flutter_bootstrap.js', 'main.dart.js', 'version.json'} if target == 'web' else {
        'lumenis_app.exe', 'flutter_windows.dll', 'data/icudtl.dat', 'data/app.so'}
    if not required.issubset({entry['path'] for entry in outputs}):
        raise ValueError('Flutter invocation did not produce the expected complete target')
    receipt = {**before, 'schema': 'lumenis.flutter-build-receipt/v1', 'flutter_exit_code': 0,
               'completed': True, 'outputs': outputs, 'asset_contract': asset_contract,
               'runtime_acceptance': 'NOT_VERIFIED'}
    receipt_path = build_receipt_path(repo, target)
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2), encoding='utf-8')
    return receipt


def verified_build(repo, target, core_url, sources):
    path = build_receipt_path(repo, target)
    if not path.is_file():
        raise ValueError('Verified ' + target + ' build receipt is missing; rebuild with this existing helper')
    receipt = json.loads(path.read_text('utf-8'))
    root = repo / ('app/build/web' if target == 'web' else 'app/build/windows/x64/runner/Release')
    if (receipt.get('schema') != 'lumenis.flutter-build-receipt/v1' or
            receipt.get('target') != target or receipt.get('mode') != 'release' or
            receipt.get('core_base_url') != core_url or receipt.get('arguments') != build_arguments(target, 'release', core_url) or
            receipt.get('completed') is not True or receipt.get('flutter_exit_code') != 0 or
            receipt.get('sources') != sources or receipt.get('outputs') != inventory(root) or
            receipt.get('asset_contract') != verify_flutter_assets(repo, target, root)):
        raise ValueError('Verified ' + target + ' build configuration/source/output does not match this bundle')
    platform = inventory(repo / 'app/windows', ('flutter/ephemeral',)) if target == 'windows' else []
    if receipt.get('platform_sources') != platform:
        raise ValueError('Verified Windows native source differs from this bundle')
    return receipt


SUPPLEMENTAL_LICENSES = {
    ('flask-cors', '6.0.5'): ('MIT', '134a20d852c0cf9e0f3c228767921b76f4bfc4af4a2fc7c4cc90f6b4fd407b5c',
        'https://raw.githubusercontent.com/corydolphin/flask-cors/91ebc49c25aaf76b0e53e925feef1e3f19617c87/LICENSE'),
    ('flatbuffers', '25.12.19'): ('Apache-2.0', 'cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30',
        'https://raw.githubusercontent.com/google/flatbuffers/7e163021e59cca4f8e1e35a7c828b5c6b7915953/LICENSE'),
    ('magika', '0.6.3'): ('Apache-2.0', '58d1e17ffe5109a7ae296caafcadfdbe6a7d176f0bc4ab01e12a689b0499d8bd',
        'https://raw.githubusercontent.com/google/magika/a04562a9bb5d52c809a4424911ca8d07c0265767/LICENSE'),
    ('markitdown', '0.1.8'): ('MIT', 'c2cfccb812fe482101a8f04597dfc5a9991a6b2748266c47ac91b6a5aae15383',
        'https://raw.githubusercontent.com/microsoft/markitdown/b8f79c57ebc0044be41323d89b2a45d3fda8460e/LICENSE'),
    ('ordered-set', '4.1.0'): ('MIT', '0cf8f55f36dc1306b3fe89bf29e29a0c742f279f038d149244319e593ab16ca4',
        'https://raw.githubusercontent.com/rspeer/ordered-set/d921651b2737f5cfe711868fab558a8ef79e26ca/MIT-LICENSE'),
}


def is_notice(relative):
    if relative.suffix.lower() in {'.py', '.pyc', '.pyo'}:
        return False
    if relative.name.lower().startswith(('license', 'licence', 'copying', 'notice', 'thirdpartynotice', 'mit-license')):
        return True
    return (relative.suffix.lower() in {'.txt', '.md', '.rst'} and
            any(part.lower() in {'licenses', 'licences', 'build_licenses'}
                for part in relative.parts[:-1]))


def dependency_license(name, dist, repo, media, media_notices=None):
    root = plain(dist.locate_file(''))
    notices, extra_files, source_files, primary_texts = [], [], [], []
    for entry in dist.files or ():
        rel = PurePosixPath(str(entry).replace('\\', '/'))
        if rel.is_absolute() or '..' in rel.parts:
            continue
        source = plain(root.joinpath(*rel.parts))
        target = str(PurePosixPath('runtime/python/Lib/site-packages') / rel)
        if is_notice(rel):
            notices.append({'path': target, 'sha256': sha(source), 'source': 'installed_distribution_file'})
            if rel.name.lower().startswith(('license', 'licence', 'mit-license')):
                primary_texts.append(source.read_text('utf-8', errors='replace'))
        if rel.suffix == '.py':
            source_files.append((source, target))
    declared = dist.metadata.get('License-Expression') or dist.metadata.get('License') or 'UNKNOWN'
    expression = declared
    supplement = SUPPLEMENTAL_LICENSES.get((name, dist.version))
    if supplement:
        expression, expected, url = supplement
        filename = f'{name}-{dist.version}.LICENSE.txt'
        source = plain(repo / 'vendor/lumenis-reuse-notices/windows-python' / filename)
        if not source.is_file() or sha(source) != expected:
            raise ValueError(f'Pinned supplemental license missing or changed: {name}')
        target = f'notices/python/{filename}'
        notices.append({'path': target, 'sha256': expected, 'source': url})
        extra_files.append((source, target))
    elif declared == 'UNKNOWN':
        text = '\n'.join(primary_texts)
        if 'GNU LESSER GENERAL PUBLIC LICENSE' in text and 'Version 3, 29 June 2007' in text:
            expression = 'LGPL-3.0'
        elif 'Permission is hereby granted, free of charge' in text:
            expression = 'MIT'
        elif 'Apache License' in text and 'Version 2.0' in text:
            expression = 'Apache-2.0'
        elif 'Redistribution and use in source and binary forms' in text:
            expression = 'BSD (see included original terms)'
    result = {'name': name, 'version': dist.version, 'license': expression,
              'license_declared': declared, 'license_notices': notices,
              'license_review': 'TEXTS_IDENTIFIED' if notices else 'LICENSE_TEXT_MISSING',
              'local_use': 'SUBJECT_TO_INCLUDED_TERMS' if notices else 'LICENSE_TEXT_MISSING',
              'redistribution_clearance': 'SUBJECT_TO_INCLUDED_TERMS' if notices else 'BLOCKED_MISSING_LICENSE_TEXT'}
    if 'LGPL' in expression:
        gpl = next((p for p in [*(media_notices or []), *media.iterdir()] if p.is_file() and is_notice(PurePosixPath(p.name))
                    and 'GNU GENERAL PUBLIC LICENSE' in p.read_text('utf-8', errors='replace')[:400]), None)
        if gpl is not None:
            target = f'notices/python/{name}-{dist.version}/GPL-3.0.txt'
            notices.append({'path': target, 'sha256': sha(gpl), 'source': 'existing_GPL_license_text'})
            extra_files.append((gpl, target))
        result.update(library_source_files=[{'path': target, 'sha256': sha(source)} for source, target in source_files],
                      library_modified_by_bundle=False,
                      library_source_identity='INSTALLED_SOURCE_COPIED_BYTE_FOR_BYTE',
                      library_replacement='PLAIN_PYTHON_SOURCE_REPLACEABLE' if source_files else 'LIBRARY_SOURCE_UNAVAILABLE',
                      redistribution_clearance='LGPL_SOURCE_AND_USER_RIGHTS_REQUIRED',
                      redistribution_requirements=['Preserve LGPL and incorporated GPL terms and attribution',
                          'Keep library source available and permit user replacement',
                          'Do not prohibit modification or reverse engineering for debugging library modifications'],
                      gpl_license_text_included=gpl is not None)
    return result, extra_files


def requirements_closure(requirements, sites):
    # No whole user-site copy, .pth hooks, console launchers or model caches.
    for site in reversed(sites):
        sys.path.insert(0, str(site))
    from packaging.requirements import Requirement
    from packaging.utils import canonicalize_name
    available = {}
    for site in sites:
        for dist in metadata.distributions(path=[str(site)]):
            available.setdefault(canonicalize_name(dist.metadata['Name']), dist)
    pending = [Requirement(line.split('#', 1)[0].strip())
               for line in requirements.read_text('utf-8-sig').splitlines()
               if line.split('#', 1)[0].strip()]
    selected, evaluated = {}, set()
    while pending:
        req = pending.pop()
        if req.marker and not any(req.marker.evaluate({'extra': extra})
                                  for extra in ('', *req.extras)):
            continue
        name = canonicalize_name(req.name)
        dist = available.get(name)
        if dist is None:
            raise ValueError(f'Required installed distribution is missing: {name}')
        if req.specifier and dist.version not in req.specifier:
            raise ValueError(f'Installed version does not satisfy requirements: {name}')
        selected[name] = dist
        for extra in ('', *sorted(req.extras)):
            if (name, extra) in evaluated:
                continue
            evaluated.add((name, extra))
            for dependency in dist.requires or ():
                child = Requirement(dependency)
                if child.marker is None or child.marker.evaluate({'extra': extra}):
                    child.marker = None
                    pending.append(child)
    return selected


def source_paths(repo):
    result = subprocess.run(['git', '-C', str(repo), 'ls-files', '-z',
                             '--cached', '--others', '--exclude-standard'],
                            check=True, capture_output=True, timeout=20)
    excluded = {'app', 'website', 'work', 'data', 'logs', 'tests', 'research',
                'docs', 'intelligence_library', 'deployment', '00-GOVERNANCE',
                '.codex', '.agents', '.github', 'vendor', 'tools', 'node_modules'}
    selected = []
    for raw in sorted(set(result.stdout.decode('utf-8').split('\0'))):
        if not raw:
            continue
        rel = PurePosixPath(raw)
        if rel.is_absolute() or '..' in rel.parts:
            raise ValueError('Invalid source inventory')
        root = rel.parts[0]
        # Preserve the notices for already adopted helper code shipped below;
        # this does not bring the rest of vendor/research into the product.
        if rel.parts[:2] == ('vendor', 'lumenis-reuse-notices') and (
                rel.suffix in {'.md', '.txt'} or rel.name.upper().startswith(('LICENSE', 'NOTICE', 'COPYING'))):
            selected.append(rel)
            continue
        if root in excluded or any(part.startswith('.') for part in rel.parts):
            continue
        if any(part in {'__pycache__', 'tests', 'test', 'fixtures', 'weights'}
               for part in rel.parts[:-1]):
            continue
        if rel.name in {'system_config.json', 'config.json'} or rel.name.startswith('test_'):
            continue
        production_root = len(rel.parts) == 1 or root in {'scripts', 'migrations', 'alembic'} or (repo / root / '__init__.py').is_file()
        code = production_root and rel.suffix in {'.py', '.cjs', '.js'}
        package_resource = len(rel.parts) > 1 and (repo / root / '__init__.py').is_file()
        resource = (package_resource or root in {'config', 'contracts', 'migrations', 'alembic', 'assets'}) and rel.suffix in {'.json', '.yaml', '.yml', '.sql', '.md', '.txt', '.ttf', '.otf', '.svg', '.png', '.jpg', '.jpeg'}
        if code or resource or str(rel) in {'VERSION', 'LICENSE', 'requirements.txt'}:
            selected.append(rel)
    for required in ('app.py', 'run_supervised.py', 'runtime_preflight.py',
                     'scripts/start_production.ps1', 'requirements.txt', 'LICENSE'):
        rel = PurePosixPath(required)
        if rel not in selected:
            selected.append(rel)
    return selected


def assemble(repo, output, runner, sites, media, core_url, app_url, vc_runtime, vc_notices, media_notices=None):
    repo, output, runner, media = map(plain, (repo, output, runner, media))
    sites = [plain(site) for site in sites]
    vc_runtime = plain(vc_runtime)
    vc_notices = [plain(path) for path in vc_notices]
    web = plain(repo / 'app/build/web')
    core_url, port = endpoint(core_url)
    if endpoint(app_url)[0] != core_url:
        raise ValueError('AppCoreBaseUrl must equal the compiled Dart define and CoreBaseUrl')
    base = plain(sys.base_prefix)
    if within(output, repo):
        allowed = repo / 'app/build/distribution'
        ignored = subprocess.run(['git', '-C', str(repo), 'check-ignore', '--quiet', '--', str(output)],
                                 check=False, capture_output=True, timeout=10)
        if (output.parent != allowed or not re.fullmatch(r'OEVIRA-[A-Za-z0-9][A-Za-z0-9._-]{0,80}', output.name)
                or ignored.returncode != 0):
            raise ValueError('In-project bundles require a new ignored app/build/distribution/OEVIRA-<version> directory')
    if output.exists() or any(within(output, root) for root in [runner, web, media, base, vc_runtime, *sites]):
        raise ValueError('BundleOutput must be a new directory outside source/runtime inputs')
    if any(within(path, output) for path in [runner, web, media, base, vc_runtime, *sites]):
        raise ValueError('BundleOutput must not contain a source/runtime input')
    if not sites or any(not site.is_dir() for site in sites):
        raise ValueError('Explicit existing PythonSitePackages are required')
    # Flutter requires these next to the executable. Use the installed toolset's
    # release redistributable directory, never arbitrary System32 DLL copies.
    # https://docs.flutter.dev/platform-integration/windows/building
    if not vc_runtime.name.startswith('Microsoft.VC') or not vc_runtime.name.endswith('.CRT') or 'debug_nonredist' in vc_runtime.parts:
        raise ValueError('VCRuntimeDirectory must be the installed release Microsoft.VC*.CRT directory')
    for name in ('msvcp140.dll', 'vcruntime140.dll', 'vcruntime140_1.dll'):
        if not (vc_runtime / name).is_file():
            raise ValueError(f'Required Visual C++ redistributable missing: {name}')
    if not vc_notices or any(not path.is_file() for path in vc_notices):
        raise ValueError('Existing Visual C++ redistributable notices must be supplied')
    vc_files = sorted(vc_runtime.glob('*.dll'))
    vc_names = {path.name.lower() for path in vc_files}
    if not all((runner / name).is_file() for name in ('lumenis_app.exe', 'flutter_windows.dll', 'data/icudtl.dat')):
        raise ValueError('The existing Flutter runner is incomplete')
    snapshot = runner / 'data/app.so'
    if not snapshot.is_file():
        raise ValueError('The compiled Windows Dart snapshot is missing')
    compiled_urls = {value.decode('ascii') for value in
                     re.findall(rb'http://127\.0\.0\.1:[0-9]{4,5}', snapshot.read_bytes())}
    if compiled_urls != {core_url}:
        raise ValueError('The compiled Windows snapshot does not match the declared Core endpoint')
    for name in ('ffmpeg.exe', 'ffprobe.exe'):
        if not (media / name).is_file():
            raise ValueError(f'Existing media runtime missing: {name}')
    if not all((web / name).is_file() for name in ('index.html', 'flutter_bootstrap.js', 'main.dart.js', 'version.json')):
        raise ValueError('The existing Flutter Web Workspace build is incomplete')
    web_version = json.loads((web / 'version.json').read_text('utf-8'))
    web_version_sha256 = sha(web / 'version.json')
    pubspec = (repo / 'app/pubspec.yaml').read_text('utf-8')
    declared_version = re.search(r'(?m)^version:\s*([^\s#]+)', pubspec)
    if not declared_version or declared_version[1] != f"{web_version.get('version')}+{web_version.get('build_number')}":
        raise ValueError('Flutter Web build version differs from the selected app source')
    sources = ui_sources(repo)
    web_receipt = verified_build(repo, 'web', core_url, sources)
    windows_receipt = verified_build(repo, 'windows', core_url, sources)
    if web_receipt['toolchain'] != windows_receipt['toolchain']:
        raise ValueError('Web and Windows builds used different Flutter toolchains')
    media_notices = ([plain(p) for p in media_notices] if media_notices else
                     [p for p in media.iterdir() if p.is_file() and
                      p.name.lower().startswith(('license', 'copying', 'readme', 'notice'))])
    if any(not p.is_file() for p in media_notices):
        raise ValueError('Explicit media notices must name existing original files')
    if not media_notices:
        raise ValueError('The supplied FFmpeg directory has no redistribution notices')
    media_hashes = tuple(sha(media / name) for name in ('ffmpeg.exe', 'ffprobe.exe'))
    known_media = {
        ('3256173f3f8bffd7df12227c68adf68025edb1832273a9530688a7bb1ed8edec',
         'f0d36ecbbdd3bcfac3efa078c96c7271c2e68b3810595552ac3b7f17e9a65c52'): '9.0.2-essentials_build-www.gyan.dev',
        ('589e50b766d251afdf181dd664d40bd94407e200b019989fd7468c7d118a28d0',
         '02264dfa4f56baaa31e443ece8aa16d397f6b008200e7fd184d22b9009e75fd3'): '9.0.2-full_build-www.gyan.dev',
    }
    media_build = known_media.get(media_hashes)
    for path in media_notices:
        if path.name.lower().startswith('readme'):
            declared = re.search(r'(?m)^Version:\s*(\S+)', path.read_text('utf-8', errors='replace'))
            if declared and media_build and declared[1] != media_build:
                raise ValueError('FFmpeg original README describes a different binary build')
    if len({p.name.lower() for p in media_notices}) != len(media_notices):
        raise ValueError('Media notice filenames overlap')
    distributions = requirements_closure(repo / 'requirements.txt', sites)
    if not all((base / name).is_file() for name in ('python.exe', 'LICENSE.txt', 'Lib/os.py')):
        raise ValueError('A complete installed base CPython runtime is required')
    abi = f'python{sys.version_info.major}{sys.version_info.minor}'
    if not (base / f'{abi}.dll').is_file():
        raise ValueError('The base Python ABI DLL is missing')
    files = []
    output.mkdir(parents=True, exist_ok=False)

    def copy(source, relative):
        source = plain(source)
        if not source.is_file():
            raise ValueError(f'Bundle source file missing: {relative}')
        relative = PurePosixPath(relative)
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Unsafe bundle relative path')
        destination = output.joinpath(*relative.parts)
        before = sha(source)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        if sha(destination) != before or sha(source) != before:
            raise ValueError('Source changed during assembly; preserve this partial bundle')
        files.append({'path': str(relative), 'sha256': before, 'size': destination.stat().st_size})

    def tree(source, target, excluded=()):
        jobs = []
        for current, dirs, names in os.walk(source, followlinks=False):
            dirs[:] = sorted(d for d in dirs if d not in excluded and d != '__pycache__')
            for name in sorted(names):
                if name.endswith(('.pyc', '.pyo', '.pth')) or name in {'sitecustomize.py', 'usercustomize.py'}:
                    continue
                if target == 'app' and Path(current) == source and name.lower() in vc_names:
                    continue
                path = Path(current) / name
                jobs.append((path, str(PurePosixPath(target) / path.relative_to(source).as_posix())))
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(lambda pair: copy(*pair), jobs))

    tree(runner, 'app')
    tree(web, 'core/app/build/web')
    for rel in source_paths(repo):
        copy(repo.joinpath(*rel.parts), str(PurePosixPath('core') / rel))
    copy(repo / '00-GOVERNANCE/THIRD-PARTY-COMPONENT-REGISTER.md', 'notices/THIRD-PARTY-COMPONENT-REGISTER.md')
    for path in base.iterdir():
        if path.name.lower() not in vc_names and (path.name in {'python.exe', 'pythonw.exe', 'LICENSE.txt'} or path.suffix.lower() == '.dll'):
            copy(path, f'runtime/python/{path.name}')
    for path in vc_files:
        copy(path, f'app/{path.name}')
        copy(path, f'runtime/python/{path.name}')
    for path in vc_notices:
        copy(path, f'notices/visual-cpp/{path.name}')
    tree(base / 'DLLs', 'runtime/python/DLLs')
    tree(base / 'Lib', 'runtime/python/Lib', ('site-packages', 'test', 'tests', 'idlelib', 'turtledemo', 'ensurepip'))
    dependency_inventory = []
    dependency_files = []
    for name, dist in sorted(distributions.items()):
        root = plain(dist.locate_file(''))
        if root not in sites or not dist.files:
            raise ValueError('Distribution files do not belong to the supplied sites')
        for entry in dist.files:
            rel = PurePosixPath(str(entry).replace('\\', '/'))
            if rel.is_absolute() or '..' in rel.parts or rel.suffix in {'.pyc', '.pyo', '.pth'} or '__pycache__' in rel.parts:
                continue
            dependency_files.append((root.joinpath(*rel.parts), str(PurePosixPath('runtime/python/Lib/site-packages') / rel)))
        license_record, extra_notices = dependency_license(name, dist, repo, media, media_notices)
        dependency_inventory.append(license_record)
        dependency_files.extend(extra_notices)
    # A bounded IO pool avoids serial antivirus/filesystem latency on large
    # installed scientific wheels. Every file retains its own before/after hash.
    if len({relative for _, relative in dependency_files}) != len(dependency_files):
        raise ValueError('Installed distributions overlap; resolve the runtime before bundling')
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda pair: copy(*pair), dependency_files))
    copied = {entry['path']: entry['sha256'] for entry in files}
    for dependency in dependency_inventory:
        for entry in dependency['license_notices'] + dependency.get('library_source_files', []):
            if copied.get(entry['path']) != entry['sha256']:
                raise ValueError(
                    f"Dependency license/source identity changed: {dependency['name']} "
                    f"at {entry['path']} (expected {entry['sha256']}, copied {copied.get(entry['path'])})"
                )
    python_paths = '.\nDLLs\nLib\nLib/site-packages\n../../core\n'
    (output / f'runtime/python/{abi}._pth').write_text(python_paths, encoding='ascii')
    for path in media.iterdir():
        if path.name in {'ffmpeg.exe', 'ffprobe.exe'} or path.suffix.lower() == '.dll':
            copy(path, f'runtime/media/{path.name}')
    for path in media_notices:
        copy(path, 'notices/ffmpeg/' + path.name)
    if tuple(sha(output / 'runtime/media' / name) for name in ('ffmpeg.exe', 'ffprobe.exe')) != media_hashes:
        raise ValueError('Media binary identity changed after notice selection')
    if sha(output / 'core/app/build/web/version.json') != web_version_sha256:
        raise ValueError('Flutter Web build identity changed during assembly')
    copied = {entry['path']: entry['sha256'] for entry in files}
    for receipt, prefix in ((web_receipt, 'core/app/build/web/'), (windows_receipt, 'app/')):
        for entry in receipt['outputs']:
            if prefix == 'app/' and '/' not in entry['path'] and entry['path'].lower() in vc_names:
                continue  # Replaced only by the separately inventoried approved release CRT.
            if copied.get(prefix + entry['path']) != entry['sha256']:
                raise ValueError('Compiled target changed after its verified build receipt')
    for target in ('web', 'windows'):
        copy(build_receipt_path(repo, target), 'notices/build/' + target + '.json')
    # Limit module-path reset to this cmd/PS5 child; never change user/machine settings.
    # https://learn.microsoft.com/powershell/module/microsoft.powershell.core/about/about_psmodulepath
    (output / 'Start-OEVIRA.cmd').write_text('@echo off\r\nsetlocal\r\nset "PSModulePath="\r\n"%SystemRoot%\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -NoLogo -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0core\\scripts\\start_production.ps1" -DesktopBundle\r\n', encoding='ascii', newline='')
    head = subprocess.run(['git', '-C', str(repo), 'rev-parse', 'HEAD'], capture_output=True,
                          check=True, text=True, timeout=10).stdout.strip()
    redistribution_blockers = ['FFMPEG_CORRESPONDING_SOURCE_AND_BUILD_DEPENDENCIES_REQUIRED',
                               'VISUAL_STUDIO_REDISTRIBUTION_ENTITLEMENT_REQUIRED']
    for dependency in dependency_inventory:
        if not dependency['license_notices'] or dependency['license'] == 'UNKNOWN':
            redistribution_blockers.append('DEPENDENCY_LICENSE_UNRESOLVED:' + dependency['name'])
        if 'LGPL' in dependency['license'] and not dependency.get('gpl_license_text_included'):
            redistribution_blockers.append('LGPL_INCORPORATED_GPL_TEXT_MISSING:' + dependency['name'])
        if 'LGPL' in dependency['license'] and not dependency.get('library_source_files'):
            redistribution_blockers.append('LGPL_LIBRARY_SOURCE_UNAVAILABLE:' + dependency['name'])
    magika_dependency = next((dependency for dependency in dependency_inventory
                              if dependency['name'] == 'magika'), None)
    onnxruntime_dependency = next((dependency for dependency in dependency_inventory
                                   if dependency['name'] == 'onnxruntime'), None)
    model_resources = []
    for entry in files:
        relative = PurePosixPath(entry['path'])
        if relative.suffix.lower() not in {'.onnx', '.tflite'}:
            continue
        path = relative.as_posix()
        resource = dict(entry)
        if path.endswith('/magika/models/standard_v3_3/model.onnx'):
            if (magika_dependency is None or magika_dependency['version'] != '0.6.3' or
                    magika_dependency['license'] != 'Apache-2.0' or
                    not magika_dependency['license_notices']):
                raise ValueError('Pinned Magika detector model lacks matching version/license evidence')
            resource.update({
                'resource_kind': 'third_party_content_type_detection_model',
                'component': 'magika',
                'component_version': magika_dependency['version'],
                'model_id': 'standard_v3_3',
                'purpose': 'Local document content-type identification used by MarkItDown; not business-answer inference',
                'license': magika_dependency['license'],
                'license_notices': magika_dependency['license_notices'],
                'upstream_source_commit': 'a04562a9bb5d52c809a4424911ca8d07c0265767',
                'upstream_windows_wheel_sha256': 'e57f75674447b20cab4db928ae58ab264d7d8582b55183a0b876711c2b2787f3',
                'training_data_included': False,
                'learning_or_training_performed': False,
            })
        elif '/onnxruntime/datasets/' in path:
            resource.update({
                'resource_kind': 'dependency_sample_graph',
                'component': 'onnxruntime',
                'component_version': (onnxruntime_dependency['version']
                                      if onnxruntime_dependency else None),
                'purpose': 'Small distribution sample graph; not a selected product inference model',
                'license': (onnxruntime_dependency['license']
                            if onnxruntime_dependency else 'UNKNOWN'),
                'license_notices': (onnxruntime_dependency['license_notices']
                                    if onnxruntime_dependency else []),
            })
        else:
            resource.update({
                'resource_kind': 'unclassified_model_resource',
                'purpose': 'Requires explicit component and license classification',
            })
        model_resources.append(resource)
    detection_resources = [resource for resource in model_resources
                           if resource['resource_kind'] == 'third_party_content_type_detection_model']
    if magika_dependency is not None and len(detection_resources) != 1:
        raise ValueError('Expected exactly one pinned Magika standard_v3_3 detection model resource')
    manifest = {'schema': 'lumenis.windows-portable-bundle/v1', 'product': 'OEVIRA',
                'source_commit': head, 'source_entry_sha256': sha(output / 'core/app.py'),
                'core_base_url': core_url, 'core_port': port, 'app_core_base_url': core_url,
                'app_endpoint_binding': 'DECLARED_ARGUMENT_AND_STATIC_SNAPSHOT_LITERAL',
                'flutter_build_receipts': {'web': 'notices/build/web.json', 'windows': 'notices/build/windows.json',
                                          'binding': 'ACTUAL_BUILD_ARGUMENTS_SOURCE_AND_OUTPUT_HASHES'},
                'python_version': sys.version.split()[0], 'python_abi': abi,
                'python_base': 'runtime/python', 'python_paths': python_paths.splitlines(),
                'workspace_web': {'root': 'core/app/build/web', 'version': web_version,
                                  'index_sha256': sha(output / 'core/app/build/web/index.html'),
                                  'main_sha256': sha(output / 'core/app/build/web/main.dart.js'),
                                  'runtime_acceptance': 'NOT_VERIFIED'},
                'visual_cpp_runtime': {'source_directory': vc_runtime.name,
                                       'files': [p.name for p in vc_files],
                                       'license_reference': 'https://learn.microsoft.com/en-us/visualstudio/releases/2026/redistribution',
                                       'runtime_terms': 'https://visualstudio.microsoft.com/license-terms/vs2026-ga-visualcpp-v14-redist-runtime/',
                                       'license_notices': [f for f in files if f['path'].startswith('notices/visual-cpp/')],
                                       'local_use': 'PERMITTED_SUBJECT_TO_MICROSOFT_RUNTIME_TERMS',
                                       'redistribution_clearance': 'VALID_VISUAL_STUDIO_LICENSE_AND_REDIST_TERMS_REQUIRED',
                                       'signature_does_not_grant_redistribution': True},
                'ffmpeg': {'build': media_build or 'BINARY_BUILD_UNRECONCILED',
                           'binary_sha256': dict(zip(('ffmpeg.exe', 'ffprobe.exe'), media_hashes)),
                           'license': 'GPL-3.0-or-later' if media_build else 'UNRECONCILED',
                           'license_notices': [f for f in files if f['path'].startswith('notices/ffmpeg/')],
                           'upstream_source': 'https://github.com/FFmpeg/FFmpeg/commit/946fcce07b' if media_build else None,
                           'build_provider': 'https://www.gyan.dev/ffmpeg/builds/' if media_build else None,
                           'local_use': 'PERMITTED_UNDER_GPL_WITHOUT_CONVEYING' if media_build else 'UNRECONCILED',
                           'redistribution_clearance': 'CORRESPONDING_SOURCE_AND_BUILD_DEPENDENCIES_REQUIRED',
                           'license_reference': 'https://www.gnu.org/licenses/gpl-3.0.html#section6'},
                'dependencies': dependency_inventory, 'files': sorted(files, key=lambda f: f['path']),
                'data_included': False, 'credentials_included': False,
                'embedded_model_resources': model_resources,
                'embedded_detection_resources': detection_resources,
                'independent_model_weights_included': True,
                'independent_model_weights_scope': 'THIRD_PARTY_FILE_TYPE_DETECTION_ONLY',
                'lumenis_owned_or_domain_model_weights_included': False,
                'installer': False,
                'runtime_acceptance': 'NOT_VERIFIED', 'local_use': 'SUBJECT_TO_RECORDED_COMPONENT_TERMS',
                'redistribution_clearance': 'BLOCKED', 'redistribution_blockers': redistribution_blockers}
    (output / 'bundle-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'bundle': str(output), 'files': len(files),
                      'dependencies': len(distributions), 'runtime_acceptance': 'NOT_VERIFIED'}))
    return manifest


if __name__ == '__main__':
    if len(sys.argv) == 8 and sys.argv[1] == '--prepare-build':
        prepare_build(Path(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5], Path(sys.argv[6]), Path(sys.argv[7]))
    elif len(sys.argv) == 9 and sys.argv[1] == '--complete-build':
        complete_build(Path(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5], Path(sys.argv[6]), Path(sys.argv[7]), int(sys.argv[8]))
    elif len(sys.argv) not in {10, 11}:
        raise SystemExit('Expected repository, output, runner, sites JSON, media, Core URL, App URL, VC runtime and notices JSON')
    else:
        assemble(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]),
                 [Path(p) for p in json.loads(sys.argv[4])], Path(sys.argv[5]), sys.argv[6], sys.argv[7],
                 Path(sys.argv[8]), [Path(p) for p in json.loads(sys.argv[9])],
                 [Path(p) for p in json.loads(sys.argv[10])] if len(sys.argv) == 11 else None)
# LUMENIS_BUNDLE_WRITER_END
'@
}

function Invoke-LumenisBuildProof {
    param([string]$Action, [string]$Repository, [string]$Target,
          [string]$BuildMode, [string]$Endpoint, [string]$Flutter,
          [string]$Python, [string]$Preparation, [int]$ActualExit = 0)
    if (-not [IO.Path]::IsPathFullyQualified($Python) -or
        -not (Test-Path -LiteralPath $Python -PathType Leaf)) {
        throw 'Verified portable builds require an explicit installed PythonExecutable.'
    }
    $proofArguments = @('-I', '-', ('--' + $Action + '-build'), $Repository,
                         $Target, $BuildMode, $Endpoint, $Flutter, $Preparation)
    if ($Action -eq 'complete') { $proofArguments += [string]$ActualExit }
    Get-LumenisBundleWriter | & $Python @proofArguments
    if ($LASTEXITCODE -ne 0) { throw 'Flutter build identity verification failed; no new verified receipt was published.' }
}

function Get-LumenisPhysicalDirectory {
    param([string]$Path)
    if (-not ('LumenisBuildPathIdentity' -as [type])) {
        Add-Type -TypeDefinition @'
using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Text;
using Microsoft.Win32.SafeHandles;
public static class LumenisBuildPathIdentity {
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    private static extern SafeFileHandle CreateFileW(string path, uint access, uint share,
        IntPtr security, uint creation, uint flags, IntPtr template);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    private static extern uint GetFinalPathNameByHandleW(SafeFileHandle handle,
        StringBuilder path, uint length, uint flags);
    public static string Resolve(string path) {
        using (var handle = CreateFileW(path, 0, 7, IntPtr.Zero, 3, 0x02000000, IntPtr.Zero)) {
            if (handle.IsInvalid) throw new Win32Exception(Marshal.GetLastWin32Error());
            var result = new StringBuilder(1024);
            uint count = GetFinalPathNameByHandleW(handle, result, (uint)result.Capacity, 0);
            if (count == 0) throw new Win32Exception(Marshal.GetLastWin32Error());
            if (count >= result.Capacity) {
                result = new StringBuilder(checked((int)count + 1));
                count = GetFinalPathNameByHandleW(handle, result, (uint)result.Capacity, 0);
                if (count == 0 || count >= result.Capacity)
                    throw new Win32Exception(Marshal.GetLastWin32Error());
            }
            return result.ToString().TrimEnd('\\');
        }
    }
}
'@
    }
    return [LumenisBuildPathIdentity]::Resolve($Path)
}

function Invoke-LumenisSubst {
    param([string[]]$Arguments)
    $executable = Join-Path ([Environment]::GetFolderPath('System')) 'subst.exe'
    $start = [Diagnostics.ProcessStartInfo]::new()
    $start.FileName = $executable
    $start.UseShellExecute = $false
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    $start.CreateNoWindow = $true
    foreach ($argument in $Arguments) { $start.ArgumentList.Add($argument) }
    $process = [Diagnostics.Process]::new()
    try {
        $process.StartInfo = $start
        if (-not $process.Start()) { throw 'SUBST_START_FAILED' }
        $stdout = $process.StandardOutput.ReadToEndAsync()
        $stderr = $process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit(10000)) {
            $process.Kill($true)
            $process.WaitForExit(3000) | Out-Null
            throw 'SUBST_TIMEOUT'
        }
        if (-not $stdout.Wait(3000) -or -not $stderr.Wait(3000)) {
            throw 'SUBST_OUTPUT_TIMEOUT'
        }
        return [pscustomobject]@{
            ExitCode = $process.ExitCode
            StandardOutput = $stdout.Result
            StandardError = $stderr.Result
        }
    } finally {
        if (-not $process.HasExited) {
            try { $process.Kill($true); $process.WaitForExit(3000) | Out-Null } catch {}
        }
        $process.Dispose()
    }
}

function Find-LumenisFreeDriveLetter {
    $occupied = [Collections.Generic.HashSet[string]]::new(
        [StringComparer]::OrdinalIgnoreCase
    )
    foreach ($drive in [IO.DriveInfo]::GetDrives()) {
        if ($drive.Name.Length -gt 1) { [void]$occupied.Add($drive.Name.Substring(0, 1)) }
    }
    foreach ($drive in Get-PSDrive -PSProvider FileSystem) {
        if ($drive.Name.Length -eq 1) { [void]$occupied.Add($drive.Name) }
    }
    foreach ($letter in @('R','S','T','U','V','W','X','Y','Z','Q','P','O','N','M','L','K','J','I','H','G','F')) {
        if ($occupied.Contains($letter) -or (Test-Path -LiteralPath ($letter + ':\'))) { continue }
        return $letter
    }
    return $null
}

function Find-LumenisDriveForSameDirectory {
    param([string]$Path)
    $expected = Get-LumenisPhysicalDirectory $Path
    foreach ($letter in @('R','S','T','U','V','W','X','Y','Z','Q','P','O','N','M','L','K','J','I','H','G','F','E','D','C','B','A')) {
        $root = $letter + ':\'
        if (-not (Test-Path -LiteralPath $root -PathType Container)) { continue }
        try {
            if ((Get-LumenisPhysicalDirectory $root).Equals(
                    $expected, [StringComparison]::OrdinalIgnoreCase)) {
                return $letter
            }
        } catch {
            # An inaccessible drive is not a reusable mapping.
        }
    }
    return $null
}

$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false
if (-not $IsWindows) { throw 'This build entry requires Windows.' }
if ($BuildWeb -and $BundleOnly) { throw 'BuildWeb and BundleOnly are separate explicit operations.' }
$processEnvironmentOverrides = @()
$programFilesX86 = [Environment]::GetEnvironmentVariable('ProgramFiles(x86)', 'Process')
$canonicalProgramFilesX86 = 'C:\Program Files (x86)'
$canonicalVsWhere = Join-Path $canonicalProgramFilesX86 'Microsoft Visual Studio/Installer/vswhere.exe'
$currentVsWhere = if ([string]::IsNullOrWhiteSpace($programFilesX86)) {
    ''
} else {
    Join-Path $programFilesX86 'Microsoft Visual Studio/Installer/vswhere.exe'
}
if ((Test-Path -LiteralPath $canonicalVsWhere -PathType Leaf) -and
    -not (Test-Path -LiteralPath $currentVsWhere -PathType Leaf)) {
    [Environment]::SetEnvironmentVariable('ProgramFiles(x86)', $canonicalProgramFilesX86, 'Process')
    $processEnvironmentOverrides += [ordered]@{
        name = 'ProgramFiles(x86)'
        scope = 'PROCESS_ONLY'
        value = $canonicalProgramFilesX86
        verified_tool = $canonicalVsWhere
    }
}
function Invoke-LumenisWebBuild {
    if ($Mode -ne 'release' -or -not $CoreBaseUrl) {
        throw 'BuildWeb requires release mode and an explicit CoreBaseUrl.'
    }
    $webRepo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
    $webFlutter = Join-Path ([IO.Path]::GetFullPath($FlutterSdk)) 'bin/flutter.bat'
    if (-not (Test-Path -LiteralPath $webFlutter -PathType Leaf)) { throw 'The selected Flutter SDK entry is missing.' }
    $webMarker = [IO.Path]::GetFullPath((Join-Path $webRepo 'app/build/web/.last_build_id'))
    if (Test-Path -LiteralPath $webMarker) {
        $markerItem = Get-Item -LiteralPath $webMarker -Force
        if ($markerItem.LinkType -or $markerItem.PSIsContainer) { throw 'Refusing a linked Web build marker.' }
        $webLastId = (Get-Content -LiteralPath $webMarker -Raw).Trim()
        if ($webLastId -notmatch '^[a-fA-F0-9]{32}$') { throw 'Refusing an invalid Web build identifier.' }
        $webOldOutputs = Join-Path $webRepo "app/.dart_tool/flutter_build/$webLastId/outputs.json"
        if (Test-Path -LiteralPath $webOldOutputs -PathType Leaf) {
            if ((Get-Item -LiteralPath $webOldOutputs -Force).LinkType) { throw 'Refusing a linked Web outputs manifest.' }
            $webPathChanged = $false
            foreach ($oldOutput in @(Get-Content -LiteralPath $webOldOutputs -Raw | ConvertFrom-Json)) {
                if ($oldOutput -isnot [string]) { throw 'Invalid Flutter Web outputs manifest.' }
                $normal = $oldOutput.Replace('\', '/')
                $boundary = $normal.IndexOf('/build/web/', [StringComparison]::OrdinalIgnoreCase)
                if ($boundary -gt 0 -and -not $normal.Substring(0, $boundary).Equals(
                        $alias.Replace('\', '/'), [StringComparison]::OrdinalIgnoreCase)) {
                    $webPathChanged = $true
                }
            }
            if ($webPathChanged) {
                # Flutter compares output spellings before deleting old files.
                # Archive only its local generated marker, never the assets.
                $webArchive = [IO.Path]::GetFullPath((Join-Path $webRepo ('app/build/native-build-receipts/web-cache-' + [Guid]::NewGuid().ToString('N'))))
                [IO.Directory]::CreateDirectory($webArchive) | Out-Null
                Move-Item -LiteralPath $webMarker -Destination (Join-Path $webArchive 'flutter-last-build-id')
                Write-Output "Archived stale Web path marker: $webArchive"
            }
        }
    }
    $webProof = Join-Path $webRepo ('app/build/native-build-receipts/web-' + [Guid]::NewGuid().ToString('N') + '.source.json')
    Invoke-LumenisBuildProof -Action prepare -Repository $webRepo -Target web -BuildMode $Mode `
        -Endpoint $CoreBaseUrl -Flutter $webFlutter -Python $PythonExecutable -Preparation $webProof
    $webExit = 1
    Push-Location -LiteralPath $alias
    try {
        $webArguments = @('build', 'web', '--release', '--no-pub',
            ('--dart-define=LUMENIS_CORE_BASE_URL=' + $CoreBaseUrl.TrimEnd('/')))
        & $webFlutter @webArguments
        $webExit = $LASTEXITCODE
        Invoke-LumenisBuildProof -Action complete -Repository $webRepo -Target web -BuildMode $Mode `
            -Endpoint $CoreBaseUrl -Flutter $webFlutter -Python $PythonExecutable -Preparation $webProof -ActualExit $webExit
    } finally { Pop-Location }
    Write-Output ('Verified Web build receipt: ' + (Join-Path $webRepo 'app/build/native-build-receipts/verified-web.json'))
    exit $webExit
}
if ($BundleOnly) {
    if (-not $BundleOutput -or -not $PythonExecutable -or -not $MediaDirectory -or
        -not $CoreBaseUrl -or -not $AppCoreBaseUrl -or -not $VCRuntimeDirectory) {
        throw 'BundleOnly requires BundleOutput, PythonExecutable, PythonSitePackages, MediaDirectory, CoreBaseUrl, AppCoreBaseUrl, VCRuntimeDirectory and VCRuntimeNotices.'
    }
    if (-not [IO.Path]::IsPathFullyQualified($PythonExecutable) -or
        -not (Test-Path -LiteralPath $PythonExecutable -PathType Leaf)) {
        throw 'PythonExecutable must be an explicit installed Python executable.'
    }
    $bundleRepo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
    $configuration = $Mode.Substring(0, 1).ToUpperInvariant() + $Mode.Substring(1)
    $bundleRunner = Join-Path $bundleRepo "app/build/windows/x64/runner/$configuration"
    $siteJson = ConvertTo-Json -InputObject @($PythonSitePackages) -Compress
    $vcNoticeJson = ConvertTo-Json -InputObject @($VCRuntimeNotices) -Compress
    $mediaNoticeJson = ConvertTo-Json -InputObject @($MediaNotices) -Compress
    Get-LumenisBundleWriter | & $PythonExecutable -I - $bundleRepo $BundleOutput $bundleRunner $siteJson $MediaDirectory $CoreBaseUrl $AppCoreBaseUrl $VCRuntimeDirectory $vcNoticeJson $mediaNoticeJson
    if ($LASTEXITCODE -ne 0) { throw 'Windows bundle assembly failed; no app/Core was launched. Partial output is retained.' }
    exit 0
}
$project = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..')).TrimEnd('\')
$flutter = Join-Path ([IO.Path]::GetFullPath($FlutterSdk)) 'bin/flutter.bat'
if (-not (Test-Path -LiteralPath $flutter -PathType Leaf)) {
    throw "Flutter SDK entry does not exist: $flutter"
}
if ($ProjectAlias) {
    if ($ProjectAlias -notmatch '^[A-Za-z]:[\\/]' -or $ProjectAlias -match '[^\x20-\x7e]' -or
        $flutter -match '[^\x20-\x7e]') {
        throw 'ProjectAlias must be an existing absolute ASCII local drive path.'
    }
    $alias = [IO.Path]::GetFullPath($ProjectAlias).TrimEnd('\')
    if (-not (Test-Path -LiteralPath $alias -PathType Container) -or
        -not (Get-LumenisPhysicalDirectory $alias).Equals(
            (Get-LumenisPhysicalDirectory $project), [StringComparison]::OrdinalIgnoreCase)) {
        throw 'ProjectAlias must resolve to this exact existing app directory; copies are refused.'
    }
} else {
$aliasBase = [IO.Path]::GetFullPath($AliasRoot).TrimEnd('\')
if ($aliasBase -match '[^\x20-\x7e]' -or $flutter -match '[^\x20-\x7e]') {
    throw 'Use an ASCII AliasRoot and FlutterSdk; no global path settings are changed.'
}
if ($aliasBase.StartsWith($project + '\', [StringComparison]::OrdinalIgnoreCase) -or
    $aliasBase.Equals($project, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'AliasRoot must be outside the app so the junction cannot loop.'
}
# Reject linked ancestors too: a lexically external root could otherwise point
# back inside the app. The app junction itself is validated separately below.
$ancestor = [IO.DirectoryInfo]::new($aliasBase)
while ($null -ne $ancestor) {
    if ($ancestor.Exists -and ($ancestor.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw 'AliasRoot must not contain a directory junction or symbolic link.'
    }
    $ancestor = $ancestor.Parent
}
$idBytes = [Security.Cryptography.SHA256]::HashData(
    [Text.Encoding]::UTF8.GetBytes($project.ToLowerInvariant()))
$projectId = [Convert]::ToHexString($idBytes).Substring(0, 16).ToLowerInvariant()
$alias = Join-Path $aliasBase $projectId
[IO.Directory]::CreateDirectory($aliasBase) | Out-Null
$aliasItem = Get-Item -LiteralPath $alias -Force -ErrorAction SilentlyContinue
if ($null -eq $aliasItem) {
    New-Item -ItemType Junction -Path $alias -Target $project | Out-Null
    $aliasItem = Get-Item -LiteralPath $alias -Force
}
if ($aliasItem.LinkType -ne 'Junction' -or
    -not $aliasItem.ResolveLinkTarget($true).FullName.TrimEnd('\').Equals(
        $project, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing an existing alias that does not point to this app: $alias"
}
}
if ($BuildWeb) { Invoke-LumenisWebBuild }

# Flutter's CMake project reaches package CMakeLists.txt through nested plugin
# symlinks. On this workstation, those paths fail through the persistent app
# junction even though the same files are readable from their real target.
# A direct SUBST root keeps source bytes unchanged and gives CMake a stable,
# short path for this build. Keep the app below the drive root: CMake/Flutter
# can otherwise emit PROJECT_DIR as a drive-relative path such as `R:`.
$buildRoot = $alias
$buildRootSelection = 'VERIFIED_JUNCTION'
$repositoryRoot = Split-Path -Parent $project
$substDrive = $null
$substTarget = $null
$substCreated = $false
$substCleanupStatus = 'NOT_REQUIRED'
$pluginLinks = Join-Path $project 'windows/flutter/ephemeral/.plugin_symlinks'
$pluginLinksHaveNestedReparsePoints = $false
if (Test-Path -LiteralPath $pluginLinks -PathType Container) {
    $pluginLinksHaveNestedReparsePoints = @(
        Get-ChildItem -LiteralPath $pluginLinks -Force -ErrorAction Stop |
            Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint }
    ).Count -gt 0
}
if ($pluginLinksHaveNestedReparsePoints) {
    $existingDrive = Find-LumenisDriveForSameDirectory $repositoryRoot
    if ($existingDrive) {
        $substDrive = $existingDrive + ':'
        $buildRoot = $existingDrive + ':\app'
        $substTarget = $repositoryRoot
        if (-not (Get-LumenisPhysicalDirectory $buildRoot).Equals(
                (Get-LumenisPhysicalDirectory $project), [StringComparison]::OrdinalIgnoreCase)) {
            throw 'The existing drive does not resolve its app child to the canonical app directory.'
        }
        $buildRootSelection = 'REUSED_EXISTING_DRIVE_REPOSITORY_ROOT_APP_SUBDIR'
        $substCleanupStatus = 'REUSED_NOT_OWNED'
    } else {
        $freeDrive = Find-LumenisFreeDriveLetter
        if (-not $freeDrive) { throw 'No free drive letter is available for a temporary repository-root build mapping.' }
        $substDrive = $freeDrive + ':'
        $buildRoot = $freeDrive + ':\app'
        $substTarget = $repositoryRoot
        $buildRootSelection = 'PROCESS_TEMP_SUBST_REPOSITORY_ROOT_APP_SUBDIR'
        $substCleanupStatus = 'PENDING_CREATION'
    }
}

# CMake caches absolute source locations. Archive just that generated state
# before changing the spelling of the same source path; never clean the app.
$build = [IO.Path]::GetFullPath((Join-Path $project 'build/windows/x64'))
$cache = Join-Path $build 'CMakeCache.txt'
$stamp = [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss-ffff')
$recordDirectory = Join-Path $project 'build/native-build-receipts'
[IO.Directory]::CreateDirectory($recordDirectory) | Out-Null
$archived = @()
$movePlan = @()
$pathChanged = $false
if (Test-Path -LiteralPath $cache -PathType Leaf) {
    if ((Get-Item -LiteralPath $cache -Force).LinkType) {
        throw 'Refusing a linked CMake cache.'
    }
    $sourceLine = Get-Content -LiteralPath $cache |
        Where-Object { $_.StartsWith('CMAKE_HOME_DIRECTORY:INTERNAL=') } |
        Select-Object -First 1
    $expectedSource = ($buildRoot.Replace('\', '/').TrimEnd('/') + '/windows')
    $actualSource = if ($sourceLine) { $sourceLine.Replace('\', '/') } else { '' }
    if ($actualSource -ne ('CMAKE_HOME_DIRECTORY:INTERNAL=' + $expectedSource)) {
        $pathChanged = $true
        foreach ($name in @('CMakeCache.txt', 'CMakeFiles')) {
            $target = Join-Path $build $name
            if (Test-Path -LiteralPath $target) {
                $resolved = (Get-Item -LiteralPath $target -Force).FullName
                if (-not $resolved.StartsWith($build + '\', [StringComparison]::OrdinalIgnoreCase) -or
                    (Get-Item -LiteralPath $target -Force).LinkType) {
                    throw "Refusing to move a generated cache outside this build: $target"
                }
                $movePlan += @{ source = $target; name = $name }
            }
        }
    }
}
# This marker is independent of CMake. Inspect it even when CMake's cache was
# removed, and finish every preflight before moving any generated metadata.
$lastBuild = [IO.Path]::GetFullPath((Join-Path $project 'build/.last_build_id'))
if (Test-Path -LiteralPath $lastBuild) {
    $lastBuildItem = Get-Item -LiteralPath $lastBuild -Force
    if ($lastBuildItem.LinkType -or $lastBuildItem.PSIsContainer -or $lastBuildItem.FullName -ne $lastBuild) {
        throw 'Refusing an unexpected Flutter build marker.'
    }
    $lastId = (Get-Content -LiteralPath $lastBuild -Raw).Trim()
    if ($lastId -notmatch '^[a-fA-F0-9]{32}$') {
        throw 'Refusing an invalid Flutter build identifier.'
    }
    $oldOutputs = Join-Path $project ".dart_tool/flutter_build/$lastId/outputs.json"
    if (Test-Path -LiteralPath $oldOutputs -PathType Leaf) {
        if ((Get-Item -LiteralPath $oldOutputs -Force).LinkType) {
            throw 'Refusing a linked Flutter outputs manifest.'
        }
        foreach ($output in @(Get-Content -LiteralPath $oldOutputs -Raw | ConvertFrom-Json)) {
            if ($output -isnot [string]) { throw 'Invalid Flutter outputs manifest.' }
            $normal = $output.Replace('\', '/')
            # Native wrapper outputs identify the Windows path transition.
            # Other targets may retain canonical paths for unrelated cached
            # assets; those must not force marker archival on every build.
            foreach ($suffix in @('/windows/flutter/ephemeral/')) {
                $boundary = $normal.IndexOf($suffix, [StringComparison]::OrdinalIgnoreCase)
                if ($boundary -gt 0 -and -not $normal.Substring(0, $boundary).Equals(
                    $buildRoot.TrimEnd('\').Replace('\', '/'), [StringComparison]::OrdinalIgnoreCase)) {
                    $pathChanged = $true
                }
            }
        }
    }
    if ($pathChanged) {
        # Flutter compares path strings, so an old spelling of this same source
        # would delete newly copied files. Archive its marker, not its outputs.
        $movePlan += @{ source = $lastBuild; name = 'flutter-last-build-id' }
    }
}

$record = [ordered]@{
    started_utc = [DateTime]::UtcNow.ToString('o')
    canonical_project = $project
    alias = $alias
    alias_selection = $(if ($ProjectAlias) { 'EXPLICIT_EXISTING_SAME_DIRECTORY' } else { 'VERIFIED_JUNCTION' })
    build_root = $buildRoot
    build_root_selection = $buildRootSelection
    subst_drive = $substDrive
    subst_target = $substTarget
    subst_created_by_process = $false
    subst_cleanup_status = $substCleanupStatus
    process_environment_overrides = $processEnvironmentOverrides
    flutter = $flutter
    arguments = @('build', 'windows', ('--' + $Mode), '--no-pub')
    archived_cache = $archived
    flutter_exit_code = $null
    exit_code = $null
    completed = $false
    output_exe = $null
    output_sha256 = $null
    product_acceptance = 'NOT_VERIFIED'
    static_import_diagnostics = @{ status = 'NOT_REQUESTED'; runtime_verified = $false }
}
if ($CoreBaseUrl) {
    if ($CoreBaseUrl -cnotmatch '^http://127\.0\.0\.1:([0-9]{4,5})/?$' -or
        ($AppCoreBaseUrl -and $AppCoreBaseUrl.TrimEnd('/') -cne $CoreBaseUrl.TrimEnd('/'))) {
        throw 'The Windows build requires matching explicit loopback Core endpoints.'
    }
    $record.arguments += '--dart-define=LUMENIS_CORE_BASE_URL=' + $CoreBaseUrl.TrimEnd('/')
}
$recordPath = Join-Path $recordDirectory ($stamp + '.json')
$logPath = Join-Path $recordDirectory ($stamp + '.log')
$nativeProof = $null
if ($CoreBaseUrl) {
    $nativeProof = Join-Path $recordDirectory ($stamp + '.source.json')
    Invoke-LumenisBuildProof -Action prepare -Repository (Split-Path -Parent $project) -Target windows `
        -BuildMode $Mode -Endpoint $CoreBaseUrl -Flutter $flutter -Python $PythonExecutable -Preparation $nativeProof
}
$record | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $recordPath -Encoding utf8
$buildExit = 1
$locationPushed = $false
try {
    if ($movePlan.Count) {
        $backup = Join-Path $recordDirectory ('cache-' + $stamp)
        [IO.Directory]::CreateDirectory($backup) | Out-Null
        foreach ($move in $movePlan) {
            $destination = Join-Path $backup $move.name
            Move-Item -LiteralPath $move.source -Destination $destination
            $archived += $destination
            $record.archived_cache = $archived
            $record | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $recordPath -Encoding utf8
        }
    }
    if ($buildRootSelection -eq 'PROCESS_TEMP_SUBST_REPOSITORY_ROOT_APP_SUBDIR') {
        $driveRoot = $substDrive + '\'
        if (Test-Path -LiteralPath $driveRoot) {
            throw "Refusing to replace a drive mapping created by another process: $substDrive"
        }
        $substResult = Invoke-LumenisSubst @($substDrive, $repositoryRoot)
        if ($substResult.ExitCode -ne 0) {
            throw "SUBST creation failed for $substDrive (exit $($substResult.ExitCode))."
        }
        $substCreated = $true
        $record.subst_created_by_process = $true
        $record.subst_cleanup_status = 'PENDING_VERIFIED_CLEANUP'
        $record | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $recordPath -Encoding utf8
        $physicalTarget = Get-LumenisPhysicalDirectory $buildRoot
        $physicalProject = Get-LumenisPhysicalDirectory $project
        if (-not $physicalTarget.Equals($physicalProject, [StringComparison]::OrdinalIgnoreCase)) {
            throw "The temporary drive app subdirectory does not resolve to the canonical app directory: $substDrive"
        }
    }
    Push-Location -LiteralPath $buildRoot
    $locationPushed = $true
    Write-Output "Building existing app through $buildRoot (canonical source: $project)"
    $buildArguments = $record.arguments
    & $flutter @buildArguments 2>&1 | Tee-Object -FilePath $logPath
    $buildExit = $LASTEXITCODE
    $record.flutter_exit_code = $buildExit
    $configuration = $Mode.Substring(0, 1).ToUpperInvariant() + $Mode.Substring(1)
    $exe = Join-Path $project "build/windows/x64/runner/$configuration/lumenis_app.exe"
    if ($buildExit -eq 0) {
        if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) {
            throw 'Flutter returned success without the expected Windows executable.'
        }
        $record.output_exe = $exe
        $record.output_sha256 = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($nativeProof) {
            Invoke-LumenisBuildProof -Action complete -Repository (Split-Path -Parent $project) -Target windows `
                -BuildMode $Mode -Endpoint $CoreBaseUrl -Flutter $flutter -Python $PythonExecutable -Preparation $nativeProof -ActualExit $buildExit
            $record['verified_build_receipt'] = Join-Path $recordDirectory 'verified-windows.json'
        }
        $record.completed = $true
        if ($StaticImportDiagnostics) {
            $diagnosticHelper = Join-Path (Split-Path -Parent $project) 'scripts/audit_tools/dll_imports.py'
            $diagnosticOutput = Join-Path $recordDirectory ('static-imports/' + $stamp + '.json')
            $record.static_import_diagnostics = Invoke-LumenisStaticImportObservation `
                -Binary $exe -ExpectedHash $record.output_sha256 -Helper $diagnosticHelper `
                -Python $PythonExecutable -Dumpbin $DumpbinPath -Output $diagnosticOutput
        }
    }
} catch {
    $buildExit = 1
    $record['error'] = $_.Exception.Message
    [Console]::Error.WriteLine($_.Exception.Message)
} finally {
    if ($locationPushed) { Pop-Location }
    if ($substCreated) {
        try {
            $driveRoot = $substDrive + '\'
            $currentTarget = Get-LumenisPhysicalDirectory $driveRoot
            $expectedTarget = Get-LumenisPhysicalDirectory $substTarget
            if ($currentTarget.Equals($expectedTarget, [StringComparison]::OrdinalIgnoreCase)) {
                $removeResult = Invoke-LumenisSubst @($substDrive, '/d')
                if ($removeResult.ExitCode -eq 0 -and -not (Test-Path -LiteralPath $driveRoot)) {
                    $substCleanupStatus = 'REMOVED_AFTER_TARGET_MATCH'
                } elseif ($removeResult.ExitCode -eq 0) {
                    $substCleanupStatus = 'REMOVAL_REPORTED_SUCCESS_PATH_STILL_PRESENT'
                } else {
                    $substCleanupStatus = 'REMOVAL_FAILED_EXIT_' + $removeResult.ExitCode
                }
            } else {
                $substCleanupStatus = 'PRESERVED_TARGET_CHANGED'
            }
        } catch {
            $substCleanupStatus = 'PRESERVED_TARGET_UNVERIFIABLE'
        }
        $record.subst_cleanup_status = $substCleanupStatus
    }
    $record.exit_code = $buildExit
    $record['finished_utc'] = [DateTime]::UtcNow.ToString('o')
    $record | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $recordPath -Encoding utf8
    Write-Output "Build receipt: $recordPath"
}
exit $buildExit
