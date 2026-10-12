"""Isolated regression tests for build_windows.ps1.

These tests copy the helper into a temporary Chinese-path app fixture and use
only a fake Flutter batch file. They verify helper mechanics, not a product
build or user-facing acceptance.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import unittest
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = REPO_ROOT / "app"
SOURCE_HELPER = APP_ROOT / "tool" / "build_windows.ps1"
FIXTURE_PARENT = APP_ROOT / "build" / "native-build-test-fixtures"
LOCAL_APP_DATA = Path(os.environ.get("LOCALAPPDATA", ""))
SCRATCH_PARENT = LOCAL_APP_DATA / "Lumenis" / "build-path-test"
POWERSHELL = shutil.which("pwsh")
REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


def _is_reparse_point(path: Path) -> bool:
    try:
        return bool(os.lstat(path).st_file_attributes & REPARSE_POINT)
    except FileNotFoundError:
        return False


def _within(path: Path, root: Path) -> bool:
    path_text = os.path.normcase(os.path.abspath(path))
    root_text = os.path.normcase(os.path.abspath(root))
    try:
        return os.path.commonpath((path_text, root_text)) == root_text
    except ValueError:
        return False


def _remove_reparse_entries(root: Path) -> None:
    """Unlink junctions/symlinks themselves before any recursive removal."""
    for directory, child_directories, filenames in os.walk(
        root, topdown=True, followlinks=False
    ):
        current = Path(directory)
        for name in list(child_directories):
            child = current / name
            if _is_reparse_point(child):
                if stat.S_ISDIR(os.lstat(child).st_mode):
                    os.rmdir(child)
                else:
                    os.unlink(child)
                child_directories.remove(name)
        for name in filenames:
            child = current / name
            if _is_reparse_point(child):
                os.unlink(child)


def _safe_remove_tree(path: Path, allowed_root: Path) -> None:
    """Remove one unique test root after checking its resolved containment."""
    if not path.exists():
        return
    absolute = Path(os.path.abspath(path))
    allowed = Path(os.path.realpath(allowed_root))
    resolved = Path(os.path.realpath(absolute))
    if (
        _is_reparse_point(absolute)
        or resolved == allowed
        or not _within(resolved, allowed)
    ):
        raise RuntimeError(f"Refusing recursive cleanup outside test root: {absolute}")
    _remove_reparse_entries(absolute)
    shutil.rmtree(absolute)


def _project_id(project: Path) -> str:
    canonical = str(Path(os.path.abspath(project))).rstrip("\\/")
    return hashlib.sha256(canonical.lower().encode("utf-8")).hexdigest()[:16]


def _create_junction(link: Path, target: Path) -> None:
    link.parent.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment["BUILD_WINDOWS_TEST_LINK"] = str(link)
    environment["BUILD_WINDOWS_TEST_TARGET"] = str(target)
    result = subprocess.run(
        [
            POWERSHELL,
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            (
                "New-Item -ItemType Junction -Path $env:BUILD_WINDOWS_TEST_LINK "
                "-Target $env:BUILD_WINDOWS_TEST_TARGET | Out-Null"
            ),
        ],
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(
            "Could not create an isolated test junction: "
            f"{result.stdout}\n{result.stderr}"
        )


class BuildWindowsHelperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if os.name != "nt":
            raise unittest.SkipTest("Windows helper tests require Windows.")
        if not POWERSHELL:
            raise unittest.SkipTest("PowerShell 7 (pwsh) is unavailable.")
        if not LOCAL_APP_DATA.is_absolute() or not LOCAL_APP_DATA.exists():
            raise unittest.SkipTest("LOCALAPPDATA is unavailable.")
        if not str(SCRATCH_PARENT).isascii():
            raise unittest.SkipTest("The authorized scratch path is not ASCII.")
        if not SOURCE_HELPER.is_file():
            raise unittest.SkipTest("build_windows.ps1 is unavailable.")

    def setUp(self) -> None:
        FIXTURE_PARENT.mkdir(parents=True, exist_ok=True)
        SCRATCH_PARENT.mkdir(parents=True, exist_ok=True)
        run_id = uuid.uuid4().hex
        self.fixture_root = FIXTURE_PARENT / f"run-{run_id}-中文"
        self.scratch_root = SCRATCH_PARENT / run_id
        self.fixture_root.mkdir()
        self.scratch_root.mkdir()
        if not str(self.scratch_root).isascii():
            self.fail("The fake SDK and AliasRoot must use an ASCII path.")

        self.alias_root = self.scratch_root / "aliases"
        self.sdk_dir = self.scratch_root / "fake-sdk"
        fake_bin = self.sdk_dir / "bin"
        fake_bin.mkdir(parents=True)
        self.flutter_bat = fake_bin / "flutter.bat"
        self.flutter_bat.write_bytes(
            (
                "@echo off\r\n"
                "setlocal\r\n"
                'if /I "%FAKE_FLUTTER_MODE%"=="exit23" exit /b 23\r\n'
                'if /I "%FAKE_FLUTTER_MODE%"=="exit0-noexe" exit /b 0\r\n'
                'if /I "%FAKE_FLUTTER_MODE%"=="build-success" (\r\n'
                '  if not exist "build\\windows\\x64\\runner\\Release" '
                'mkdir "build\\windows\\x64\\runner\\Release" >nul 2>nul\r\n'
                '  >"build\\windows\\x64\\runner\\Release\\lumenis_app.exe" '
                "echo fake-executable\r\n"
                '  if not exist "build\\windows\\x64\\CMakeCache.txt" '
                'echo CMAKE_HOME_DIRECTORY:INTERNAL=%FAKE_ALIAS%/windows>'
                '"build\\windows\\x64\\CMakeCache.txt"\r\n'
                "  exit /b 0\r\n"
                ")\r\n"
                "exit /b 79\r\n"
            ).encode("ascii")
        )

    def tearDown(self) -> None:
        # Unlink every fixture junction before deleting either target tree.
        # Cleanup validates both unique roots before recursive removal.
        _remove_reparse_entries(self.fixture_root)
        _remove_reparse_entries(self.scratch_root)
        _safe_remove_tree(self.scratch_root, SCRATCH_PARENT)
        _safe_remove_tree(self.fixture_root, FIXTURE_PARENT)

    def new_project(self, name: str) -> Path:
        project = self.fixture_root / name / "app"
        (project / "tool").mkdir(parents=True)
        (project / "windows").mkdir()
        (project / "lib").mkdir()
        (project / "tool" / "build_windows.ps1").write_bytes(
            SOURCE_HELPER.read_bytes()
        )
        (project / "pubspec.yaml").write_text(
            "name: helper_fixture\nflutter:\n  uses-material-design: true\n",
            encoding="utf-8",
        )
        (project / "windows" / "CMakeLists.txt").write_text(
            "cmake_minimum_required(VERSION 3.14)\nproject(helper_fixture)\n",
            encoding="utf-8",
        )
        (project / "lib" / "main.dart").write_text(
            "void main() {}\n", encoding="utf-8"
        )
        self.assertFalse(str(project).isascii(), "The app fixture must include Chinese path text.")
        return project

    def alias_for(self, project: Path, alias_root: Path | None = None) -> Path:
        root = alias_root or self.alias_root
        return root / _project_id(project)

    def invoke_helper(
        self,
        project: Path,
        mode: str,
        alias_root: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        root = alias_root or self.alias_root
        alias = self.alias_for(project, root)
        environment = os.environ.copy()
        environment["FAKE_FLUTTER_MODE"] = mode
        environment["FAKE_ALIAS"] = str(alias)
        command = [
            POWERSHELL,
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(project / "tool" / "build_windows.ps1"),
            "-FlutterSdk",
            str(self.sdk_dir),
            "-AliasRoot",
            str(root),
            "-Mode",
            "release",
        ]
        self.assertTrue(str(self.sdk_dir).isascii())
        self.assertTrue(str(root).isascii())
        return subprocess.run(
            command,
            env=environment,
            cwd=str(self.fixture_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            check=False,
        )

    def receipt(self, project: Path) -> dict[str, object]:
        receipts = sorted((project / "build" / "native-build-receipts").glob("*.json"))
        self.assertTrue(receipts, "The helper did not write a build receipt.")
        return json.loads(receipts[-1].read_text(encoding="utf-8-sig"))

    def make_matching_cache(self, project: Path) -> tuple[Path, str]:
        cache = project / "build" / "windows" / "x64" / "CMakeCache.txt"
        cache.parent.mkdir(parents=True, exist_ok=True)
        expected = str(self.alias_for(project) / "windows").replace("\\", "/")
        text = f"CMAKE_HOME_DIRECTORY:INTERNAL={expected}\n"
        cache.write_text(text, encoding="ascii")
        return cache, text

    def add_old_outputs(
        self,
        project: Path,
        marker_id: str,
        output_path: Path,
        slash_style: str,
        recorded_output: str | None = None,
    ) -> tuple[Path, Path]:
        build = project / "build"
        marker = build / ".last_build_id"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(marker_id, encoding="ascii")
        manifest = project / ".dart_tool" / "flutter_build" / marker_id / "outputs.json"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"preserve-old-output\n")
        output_text = recorded_output if recorded_output is not None else str(output_path)
        if slash_style == "forward":
            output_text = output_text.replace("\\", "/")
        manifest.write_text(json.dumps([output_text]), encoding="utf-8")
        return marker, manifest

    def test_linked_marker_rejection_precedes_cache_moves(self) -> None:
        project = self.new_project("marker-link-case")
        build = project / "build"
        cmake = build / "windows" / "x64" / "CMakeCache.txt"
        cmake.parent.mkdir(parents=True)
        cmake.write_text(
            "CMAKE_HOME_DIRECTORY:INTERNAL=C:/old/canonical/path/windows\n",
            encoding="ascii",
        )
        cmake_files = cmake.parent / "CMakeFiles"
        cmake_files.mkdir()
        sentinel = cmake_files / "sentinel.txt"
        sentinel.write_text("keep-cache-state", encoding="ascii")

        marker_target = self.scratch_root / "marker-target"
        marker_target.mkdir()
        marker_target_file = marker_target / "payload.txt"
        marker_target_file.write_text("linked-marker-target", encoding="ascii")
        marker = build / ".last_build_id"
        _create_junction(marker, marker_target)

        result = self.invoke_helper(project, "exit23")

        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("unexpected Flutter build marker", result.stdout + result.stderr)
        self.assertEqual(
            cmake.read_text(encoding="ascii"),
            "CMAKE_HOME_DIRECTORY:INTERNAL=C:/old/canonical/path/windows\n",
        )
        self.assertEqual(sentinel.read_text(encoding="ascii"), "keep-cache-state")
        self.assertTrue(_is_reparse_point(marker), "The linked marker was moved or replaced.")
        self.assertTrue((marker / "payload.txt").is_file())
        self.assertFalse(list((build / "native-build-receipts").glob("cache-*")))

    def test_stale_marker_archived_with_missing_or_matching_cmake(self) -> None:
        for cache_state in ("missing", "matching"):
            with self.subTest(cache_state=cache_state):
                project = self.new_project(f"stale-marker-{cache_state}")
                cmake = None
                cache_text = None
                if cache_state == "matching":
                    cmake, cache_text = self.make_matching_cache(project)
                marker_id = "0123456789abcdef0123456789abcdef"
                old_output = (
                    project
                    / "windows"
                    / "flutter"
                    / "ephemeral"
                    / "core_implementations.cc"
                )
                marker, manifest = self.add_old_outputs(
                    project, marker_id, old_output, slash_style="backslash"
                )
                original_manifest = manifest.read_bytes()
                original_output = old_output.read_bytes()

                result = self.invoke_helper(project, "exit23")

                self.assertEqual(result.returncode, 23, result.stdout + result.stderr)
                self.assertFalse(marker.exists(), "Stale marker should be archived before Flutter runs.")
                receipt = self.receipt(project)
                archived_markers = [
                    Path(item)
                    for item in receipt["archived_cache"]
                    if str(item).endswith("flutter-last-build-id")
                ]
                self.assertEqual(len(archived_markers), 1, receipt)
                self.assertEqual(archived_markers[0].read_text(encoding="ascii"), marker_id)
                self.assertEqual(manifest.read_bytes(), original_manifest)
                self.assertEqual(old_output.read_bytes(), original_output)
                if cmake is None:
                    self.assertFalse((project / "build" / "windows" / "x64" / "CMakeCache.txt").exists())
                else:
                    self.assertEqual(cmake.read_text(encoding="ascii"), cache_text)

    def test_external_alias_root_junction_into_app_is_rejected(self) -> None:
        project = self.new_project("alias-root-link-case")
        target = project / "build" / "alias-root-target"
        target.mkdir(parents=True)
        external_alias_root = self.scratch_root / "external-alias-root"
        _create_junction(external_alias_root, target)

        result = self.invoke_helper(project, "exit23", alias_root=external_alias_root)

        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("AliasRoot", result.stdout + result.stderr)
        self.assertFalse(
            (target / _project_id(project)).exists(),
            "The helper created its alias inside the linked project directory.",
        )

    def test_zero_flutter_exit_without_exe_is_wrapper_failure(self) -> None:
        project = self.new_project("missing-exe-case")

        result = self.invoke_helper(project, "exit0-noexe")

        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        receipt = self.receipt(project)
        self.assertEqual(receipt["flutter_exit_code"], 0, receipt)
        self.assertNotEqual(receipt["exit_code"], 0, receipt)
        self.assertFalse(receipt["completed"], receipt)
        self.assertIn("expected Windows executable", receipt["error"])
        self.assertEqual(receipt["product_acceptance"], "NOT_VERIFIED")

    def test_repeat_build_reuses_same_alias_and_preserves_fixture_files(self) -> None:
        project = self.new_project("repeat-build-case")
        source = project / "lib" / "main.dart"
        source_before = source.read_bytes()

        first = self.invoke_helper(project, "build-success")

        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        alias = self.alias_for(project)
        self.assertTrue(_is_reparse_point(alias), "The helper did not create a junction alias.")
        self.assertTrue(os.path.samefile(alias, project), "Alias must resolve to the fixture app itself.")
        cache, cache_text = self.make_matching_cache(project)
        marker_id = "fedcba9876543210fedcba9876543210"
        preserved_output = (
            project / "windows" / "flutter" / "ephemeral" / "preserved.bin"
        )
        marker, manifest = self.add_old_outputs(
            project,
            marker_id,
            preserved_output,
            slash_style="forward",
            recorded_output=(
                str(alias).replace("\\", "/")
                + "/windows/flutter/ephemeral/preserved.bin"
            ),
        )
        output_before = preserved_output.read_bytes()
        manifest_before = manifest.read_bytes()
        exe = project / "build" / "windows" / "x64" / "runner" / "Release" / "lumenis_app.exe"
        exe_before = exe.read_bytes()

        second = self.invoke_helper(project, "build-success")

        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertTrue(os.path.samefile(alias, project))
        self.assertEqual(source.read_bytes(), source_before)
        self.assertEqual(cache.read_text(encoding="ascii"), cache_text)
        self.assertEqual(marker.read_text(encoding="ascii"), marker_id)
        self.assertEqual(manifest.read_bytes(), manifest_before)
        self.assertEqual(preserved_output.read_bytes(), output_before)
        self.assertEqual(exe.read_bytes(), exe_before)
        receipt = self.receipt(project)
        self.assertEqual(receipt["archived_cache"], [], receipt)
        self.assertEqual(receipt["flutter_exit_code"], 0, receipt)
        self.assertEqual(receipt["exit_code"], 0, receipt)
        self.assertTrue(receipt["completed"], receipt)
        self.assertEqual(receipt["product_acceptance"], "NOT_VERIFIED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
