"""Isolated build-helper mechanics. Fake Flutter; no product build/app launch."""
from __future__ import annotations
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

import test_build_windows as build_fixtures

POWERSHELL = build_fixtures.POWERSHELL
REPO_ROOT = build_fixtures.REPO_ROOT


class OptionalStaticImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        build_fixtures.BuildWindowsHelperTests.setUpClass()

    def setUp(self):
        self.h = build_fixtures.BuildWindowsHelperTests('runTest')
        self.h.setUp()
        self.project = self.h.new_project('optional-imports')
        self.helpers = self.project.parent / 'scripts' / 'audit_tools'
        self.helpers.mkdir(parents=True)
        for name in ('dll_imports.py', 'binnexus_imports.py'):
            shutil.copyfile(REPO_ROOT / 'scripts/audit_tools' / name, self.helpers / name)

    def tearDown(self):
        self.h.tearDown()

    def invoke(self, mode, *extra):
        environment = os.environ.copy()
        environment['FAKE_FLUTTER_MODE'] = mode
        environment['FAKE_ALIAS'] = str(self.h.alias_for(self.project))
        return subprocess.run([
            POWERSHELL, '-NoLogo', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
            '-File', str(self.project / 'tool/build_windows.ps1'),
            '-FlutterSdk', str(self.h.sdk_dir), '-AliasRoot', str(self.h.alias_root),
            '-Mode', 'release', *extra], env=environment, cwd=self.h.fixture_root,
            capture_output=True, text=True, encoding='utf8', errors='replace', timeout=35)

    def test_default_never_runs_optional_diagnostics(self):
        result = self.invoke('build-success')
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = self.h.receipt(self.project)
        self.assertEqual(receipt['static_import_diagnostics']['status'], 'NOT_REQUESTED')
        self.assertEqual(receipt['product_acceptance'], 'NOT_VERIFIED')

    def test_missing_tools_do_not_turn_build_success_into_failure(self):
        result = self.invoke('build-success', '-StaticImportDiagnostics')
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = self.h.receipt(self.project)
        self.assertTrue(receipt['completed'])
        self.assertEqual(receipt['static_import_diagnostics']['status'], 'TOOL_NOT_AVAILABLE')
        self.assertFalse(receipt['static_import_diagnostics']['runtime_verified'])

    def test_failed_build_never_calls_diagnostic(self):
        result = self.invoke('exit23', '-StaticImportDiagnostics')
        self.assertEqual(result.returncode, 23)
        receipt = self.h.receipt(self.project)
        self.assertEqual(receipt['static_import_diagnostics']['status'], 'NOT_REQUESTED')
        self.assertFalse(receipt['completed'])

    def test_safe_result_reference_is_in_existing_build_receipt(self):
        # This explicitly synthetic helper tests receipt plumbing, not DUMPBIN.
        fake = self.helpers / 'dll_imports.py'
        fake.write_text('''import hashlib,json,sys
from pathlib import Path
binary=Path(sys.argv[sys.argv.index('--binary')+1])
print(json.dumps({'schema':'lumenis.static-import-observation.v1',
'status':'IMPORTS_OBSERVED','binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),
'runtime_verified':False,'dependency_resolution_verified':False,
'current_source_build_verified':False,'binary_unchanged':True,
'imports':['synthetic_fixture.dll']}))
''', encoding='utf8')
        result = self.invoke('build-success', '-StaticImportDiagnostics',
                             '-PythonExecutable', sys.executable, '-DumpbinPath', sys.executable)
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = self.h.receipt(self.project)
        diag = receipt['static_import_diagnostics']
        self.assertEqual(diag['status'], 'STATIC_IMPORTS_OBSERVED')
        reference = Path(diag['result_reference'])
        self.assertTrue(reference.is_file())
        self.assertEqual(reference.parent.name, 'static-imports')
        self.assertIn('synthetic_fixture.dll', json.loads(reference.read_text('utf8'))['imports'])
        self.assertEqual(receipt['product_acceptance'], 'NOT_VERIFIED')

    def test_invalid_output_cannot_promote_diagnostic_or_leak_stderr(self):
        (self.helpers/'dll_imports.py').write_text(
            "import sys; print('{}'); print('PRIVATE_SENTINEL',file=sys.stderr)", encoding='utf8')
        result = self.invoke('build-success', '-StaticImportDiagnostics',
                             '-PythonExecutable', sys.executable, '-DumpbinPath', sys.executable)
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = self.h.receipt(self.project)
        self.assertEqual(receipt['static_import_diagnostics']['status'], 'OUTPUT_NOT_VERIFIED')
        self.assertNotIn('PRIVATE_SENTINEL', json.dumps(receipt))
        self.assertNotIn('PRIVATE_SENTINEL', result.stdout+result.stderr)


if __name__ == '__main__':
    unittest.main(verbosity=2)
