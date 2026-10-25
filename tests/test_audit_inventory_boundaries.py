"""Audit inventories distinguish local artifacts without hiding runtime violations."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.audit_tools import verify_codex_takeover_governance as governance
from scripts.audit_tools import verify_database_authority as database
from scripts.audit_tools import verify_lumenis_single_product as product


class AuditInventoryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="lumenis-audit-inventory-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def write(self, name, body=""):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        return path

    def test_local_trees_are_pruned_before_they_are_opened(self):
        included = self.write("lumenis/new_runtime.py", "import sqlite3\nsqlite3.connect('x')")
        for name in ("work", ".venv", "venv", "vendor"):
            self.write(f"{name}/candidate/runtime.py", "not valid Python")
        real_scandir = database.os.scandir

        def scoped_scandir(path):
            relative = Path(path).relative_to(self.root)
            if relative.parts and relative.parts[0] in {"work", ".venv", "venv", "vendor"}:
                self.fail("excluded local tree was traversed")
            return real_scandir(path)

        with patch.object(database.os, "scandir", scoped_scandir):
            self.assertEqual(database.production_python_files(self.root), [included])
            self.assertEqual(product.production_python_files(self.root), [included])
            canonical = self.write("00-GOVERNANCE/" + governance.CONTRACT_BASENAME, "{}")
            with patch.object(governance, "ROOT", self.root), patch.dict(
                governance.PATHS, contract=canonical
            ):
                governance._assert_single_machine_contract()

    def test_new_untracked_and_nested_work_runtime_sources_stay_in_scope(self):
        paths = [self.write(name, "import sqlite3\nsqlite3.connect('x')") for name in (
            "new_owner.py", "lumenis/subpkg/work/runtime.py", "work.py",
        )]
        for scanner in (database.production_python_files, product.production_python_files):
            self.assertEqual(set(scanner(self.root)), set(paths))
        for path in paths:
            self.assertTrue(database.find_direct_sqlite_calls(path.read_text(), str(path)))

    def test_only_root_flutter_build_output_is_pruned_before_descent(self):
        generated = self.root / "app/build"
        self.write("app/build/native-bundle-runtime-deps/third_party/runtime.py", "not Python")
        self.write("app/build/distribution/runtime.py", "not Python")
        included = [self.write(name) for name in (
            "app/tool/package_runtime.py", "app/tool/build/runtime.py",
            "lumenis/build/runtime.py", "build/runtime.py",
            "nested/app/build/runtime.py", "app/building/runtime.py",
        )]
        real_scandir = product.os.scandir

        def scoped_scandir(path):
            if Path(path) == generated or generated in Path(path).parents:
                self.fail("generated Flutter output was traversed")
            return real_scandir(path)

        with patch.object(product.os, "scandir", scoped_scandir):
            self.assertEqual(set(product.production_python_files(self.root)), set(included))

    def test_tracked_python_cannot_hide_in_generated_flutter_output(self):
        for path in ("app/build/owner.py", "app\\build\\distribution\\owner.py"):
            with self.subTest(path=path):
                self.assertTrue(any(
                    "tracked Python source in generated app/build" in error
                    for error in product.tracked_path_errors([path])
                ))
        self.assertEqual(product.tracked_path_errors([
            "app/tool/build/owner.py", "lumenis/build/owner.py",
            "nested/app/build/owner.py", "app/building/owner.py",
        ]), [])

    def test_flutter_tool_and_nested_build_access_errors_stay_blocking(self):
        included_dirs = (self.root / "app/tool", self.root / "lumenis/build")
        for directory in included_dirs:
            self.write(f"{directory.relative_to(self.root).as_posix()}/runtime.py")
        real_scandir = product.os.scandir
        for denied in included_dirs:
            def denied_scandir(path, denied=denied):
                if Path(path) == denied:
                    raise PermissionError("included path unreadable")
                return real_scandir(path)

            with self.subTest(path=denied), patch.object(
                product.os, "scandir", denied_scandir
            ), self.assertRaises(PermissionError):
                product.production_python_files(self.root)

    def test_real_duplicate_contract_remains_blocking_even_under_nested_work(self):
        canonical = self.write("00-GOVERNANCE/" + governance.CONTRACT_BASENAME, "{}")
        self.write("work/candidate/00-GOVERNANCE/" + governance.CONTRACT_BASENAME, "{}")
        with patch.object(governance, "ROOT", self.root), patch.dict(
            governance.PATHS, contract=canonical
        ):
            governance._assert_single_machine_contract()
            self.write("lumenis/work/" + governance.CONTRACT_BASENAME, "{}")
            with self.assertRaisesRegex(AssertionError, "duplicate live machine contract"):
                governance._assert_single_machine_contract()

    def test_included_directory_access_error_is_blocking(self):
        self.write("lumenis/runtime.py")
        real_scandir = database.os.scandir

        def denied_scandir(path):
            if Path(path) == self.root / "lumenis":
                raise PermissionError("included path unreadable")
            return real_scandir(path)

        canonical = self.write("00-GOVERNANCE/" + governance.CONTRACT_BASENAME, "{}")
        with patch.object(database.os, "scandir", denied_scandir):
            for scanner in (database.production_python_files, product.production_python_files):
                with self.assertRaises(PermissionError):
                    scanner(self.root)
            with patch.object(governance, "ROOT", self.root), patch.dict(
                governance.PATHS, contract=canonical
            ), self.assertRaises(PermissionError):
                governance._assert_single_machine_contract()


if __name__ == "__main__":
    unittest.main()


def test_pinned_history_does_not_reintroduce_active_legacy_paths():
    inventory = governance._recovered_evidence_inventory()
    paths = list(inventory) + [governance.RECOVERED_EVIDENCE_RECEIPT]
    assert product.tracked_path_errors(paths) == []
    for unapproved in (
        'research/frontend/arbitrary.py',
        'research/engineering/documentation-evidence/reports/frontend/unlisted.md',
        'app/lib/frontend/runtime.dart', 'lumenis/legacy/runtime.py',
        next(path for path in inventory if 'frontend_' in path) + '.neighbor',
    ):
        errors = product.tracked_path_errors(paths + [unapproved])
        assert any('obsolete product/archive path token' in error and unapproved in error for error in errors)
    missing = paths[1:]
    assert any('invalid recovered evidence inventory' in error for error in product.tracked_path_errors(missing))


def test_history_exception_rejects_forged_or_corrupt_receipt(tmp_path, monkeypatch):
    import json
    original = json.loads((governance.ROOT / governance.RECOVERED_EVIDENCE_RECEIPT).read_text())
    paths = [entry['repository_relative_path'] for entry in original['files']]
    paths.append(governance.RECOVERED_EVIDENCE_RECEIPT)
    receipt = tmp_path / governance.RECOVERED_EVIDENCE_RECEIPT
    receipt.parent.mkdir(parents=True)
    monkeypatch.setattr(governance, 'ROOT', tmp_path)
    receipt.write_text(json.dumps(original))
    # Pinned receipt alone cannot authorize files whose bytes are missing.
    assert any('invalid recovered evidence inventory' in error for error in product.tracked_path_errors(paths))
    original['files'][0]['repository_relative_path'] = 'research/frontend/arbitrary.py'
    paths[0] = 'research/frontend/arbitrary.py'
    receipt.write_text(json.dumps(original))
    errors = product.tracked_path_errors(paths)
    assert any('approved finite set' in error for error in errors)
    assert any('obsolete product/archive path token' in error for error in errors)
    receipt.write_text('{invalid')
    assert any('invalid recovered evidence inventory' in error for error in product.tracked_path_errors(paths))


def test_single_product_production_cli_smoke():
    import subprocess
    import sys
    result = subprocess.run(
        [sys.executable, str(Path(product.__file__))], cwd=product.ROOT,
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'architecture guard: PASS' in result.stdout
