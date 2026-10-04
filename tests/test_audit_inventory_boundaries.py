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
        for name in ("work", ".venv", "venv"):
            self.write(f"{name}/candidate/runtime.py", "not valid Python")
        real_scandir = database.os.scandir

        def scoped_scandir(path):
            relative = Path(path).relative_to(self.root)
            if relative.parts and relative.parts[0] in {"work", ".venv", "venv"}:
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
