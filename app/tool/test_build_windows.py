"""Isolated regression tests for build_windows.ps1.

These tests copy the helper into a temporary Chinese-path app fixture and use
only a fake Flutter batch file. They verify helper mechanics, not a product
build or user-facing acceptance.
"""

from __future__ import annotations

import hashlib
import importlib.abc
import importlib.util
import json
import os
import shutil
import stat
import struct
import subprocess
import sys
import unittest
import uuid
from pathlib import Path
from unittest import mock

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
        # Packaged desktop hosts can virtualize a newly created LOCALAPPDATA
        # child without redirecting its pre-existing logical parent. Pin the
        # actual unique root at creation; teardown must retain that identity.
        self.scratch_resolved = Path(os.path.realpath(self.scratch_root))
        if not _within(self.scratch_resolved, Path(os.path.realpath(LOCAL_APP_DATA))):
            raise RuntimeError("The isolated scratch root escaped LOCALAPPDATA")
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
        if Path(os.path.realpath(self.scratch_root)) != self.scratch_resolved:
            raise RuntimeError("The isolated scratch root changed identity")
        _remove_reparse_entries(self.fixture_root)
        _remove_reparse_entries(self.scratch_root)
        _safe_remove_tree(self.scratch_root, self.scratch_resolved.parent)
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
        project_alias: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        root = alias_root or self.alias_root
        alias = project_alias or self.alias_for(project, root)
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
        if project_alias is not None:
            command.extend(["-ProjectAlias", str(project_alias)])
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

    def test_explicit_existing_alias_must_be_the_same_directory_not_a_source_copy(self):
        project = self.new_project("explicit-alias-source")
        duplicate = self.scratch_root / "source-copy"
        shutil.copytree(project, duplicate)
        result = self.invoke_helper(project, "build-success", project_alias=duplicate)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("copies are refused", result.stdout + result.stderr)
        self.assertFalse((project / "build/windows").exists())
        self.assertFalse(self.alias_for(project).exists())
        self.assertEqual((duplicate / "lib/main.dart").read_bytes(), (project / "lib/main.dart").read_bytes())

    def test_explicit_existing_same_directory_alias_reuses_cache_and_preserves_mapping(self):
        project = self.new_project("explicit-alias-target")
        alias = self.scratch_root / "existing-app-path"
        _create_junction(alias, project)
        result = self.invoke_helper(project, "build-success", project_alias=alias)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        receipt = self.receipt(project)
        self.assertEqual(receipt["alias_selection"], "EXPLICIT_EXISTING_SAME_DIRECTORY")
        self.assertEqual(receipt["alias"], str(alias))
        self.assertTrue(_is_reparse_point(alias))
        self.assertEqual((alias / "lib/main.dart").read_bytes(), (project / "lib/main.dart").read_bytes())

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


class WindowsPortableBundleTests(unittest.TestCase):
    """Package mechanics only. No real Flutter SDK, Core, App, DB or network."""

    @classmethod
    def setUpClass(cls):
        BuildWindowsHelperTests.setUpClass()
        source = SOURCE_HELPER.read_text("utf-8-sig")
        worker = source.split("# LUMENIS_BUNDLE_WRITER_BEGIN\n", 1)[1].split(
            "# LUMENIS_BUNDLE_WRITER_END", 1
        )[0]
        class BundleSourceLoader(importlib.abc.SourceLoader):
            def get_filename(self, fullname):
                return str(SOURCE_HELPER)

            def get_data(self, path):
                return worker.encode("utf-8")

        loader = BundleSourceLoader()
        spec = importlib.util.spec_from_loader("bundle_mechanics", loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        cls.worker = vars(module)

    def setUp(self):
        self.h = BuildWindowsHelperTests("runTest")
        self.h.setUp()
        self.root = self.h.fixture_root / "source"
        self.root.mkdir()
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        (self.root / "app/build/web").mkdir(parents=True)
        (self.root / "app/.gitignore").write_text("/build/\n", encoding="utf-8")
        (self.root / "app/pubspec.yaml").write_text("name: bundle_fixture\nversion: 1.0.0+1\n", encoding="utf-8")
        (self.root / "app/lib").mkdir()
        (self.root / "app/lib/main.dart").write_text("void main() {}\n", encoding="utf-8")
        (self.root / "app/windows").mkdir()
        (self.root / "app/windows/CMakeLists.txt").write_text("# selected runner source\n", encoding="utf-8")
        (self.root / "app/pubspec.lock").write_text("packages: {}\n", encoding="utf-8")
        (self.root / "app/.dart_tool").mkdir()
        (self.root / "app/.dart_tool/package_config.json").write_text('{"packages": []}', encoding="utf-8")
        self.flutter = self.h.flutter_bat
        (self.h.sdk_dir / "bin/internal").mkdir()
        (self.h.sdk_dir / "bin/internal/engine.version").write_text("selected-engine", encoding="utf-8")
        (self.h.sdk_dir / "bin/cache").mkdir()
        (self.h.sdk_dir / "bin/cache/flutter.version.json").write_text('{"frameworkRevision": "fixture"}', encoding="utf-8")
        for filename in ("index.html", "flutter_bootstrap.js", "main.dart.js"):
            (self.root / "app/build/web" / filename).write_text("isolated-web-build", encoding="utf-8")
        (self.root / "app/build/web/version.json").write_text(
            json.dumps({"version": "1.0.0", "build_number": "1"}), encoding="utf-8")
        self.base = self.h.fixture_root / "python-base"
        for name in ("python.exe", "python313.dll", "python3.dll", "vcruntime140.dll",
                     "LICENSE.txt", "Lib/os.py", "DLLs/_sqlite3.pyd"):
            path = self.base / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"isolated-python-fixture")
        self.runner = self.root / "app/build/windows/x64/runner/Release"
        for name in ("lumenis_app.exe", "flutter_windows.dll", "data/icudtl.dat",
                     "data/app.so",
                     "data/flutter_assets/fonts/original.ttf"):
            path = self.runner / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"isolated-runner-fixture")
        (self.runner / "data/app.so").write_bytes(b"compiled http://127.0.0.1:58724 fixture")
        self.media = self.h.fixture_root / "media"
        self.media.mkdir()
        for name in ("ffmpeg.exe", "ffprobe.exe", "LICENSE.txt"):
            (self.media / name).write_bytes(b"isolated-media-fixture")
        self.site = self.h.fixture_root / "site"
        self.site.mkdir()
        self.vc_runtime = self.h.fixture_root / "redist/x64/Microsoft.VC145.CRT"
        self.vc_runtime.mkdir(parents=True)
        for name in ("msvcp140.dll", "vcruntime140.dll", "vcruntime140_1.dll"):
            (self.vc_runtime / name).write_bytes(b"isolated-release-redist-fixture")
        self.vc_notice = self.h.fixture_root / "Redist.txt"
        self.vc_notice.write_text("fixture redistributable notice\n", encoding="utf-8")
        for name in ("app.py", "run_supervised.py", "runtime_preflight.py", "LICENSE",
                     "00-GOVERNANCE/THIRD-PARTY-COMPONENT-REGISTER.md"):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# isolated source\n", encoding="utf-8")
        launcher = self.root / "scripts/start_production.ps1"
        launcher.parent.mkdir()
        launcher.write_bytes((REPO_ROOT / "scripts/start_production.ps1").read_bytes())
        (self.root / "requirements.txt").write_text("bundle-fixture==1.0\n", encoding="utf-8")
        self.dist("bundle-fixture", "1.0")
        self.output = self.h.scratch_root / "bundle"
        for assets in (self.root / "app/build/web/assets", self.runner / "data/flutter_assets"):
            assets.mkdir(parents=True, exist_ok=True)
            (assets / "AssetManifest.bin").write_bytes(b"\x0d\x00")
            (assets / "FontManifest.json").write_text("[]", encoding="utf-8")
        self.seal("web")
        self.seal("windows")

    def tearDown(self):
        self.h.tearDown()

    def dist(self, name, version, requirements=()):
        module = name.replace("-", "_")
        (self.site / f"{module}.py").write_text("# wheel payload\n", encoding="utf-8")
        directory = self.site / f"{module}-{version}.dist-info"
        directory.mkdir()
        metadata_text = f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\nLicense: MIT\n"
        metadata_text += "".join(f"Requires-Dist: {item}\n" for item in requirements)
        (directory / "METADATA").write_text(metadata_text, encoding="utf-8")
        (directory / "LICENSE").write_text("fixture license\n", encoding="utf-8")
        records = [f"{module}.py", f"{directory.name}/METADATA", f"{directory.name}/LICENSE"]
        (directory / "RECORD").write_text("".join(f"{item},,\n" for item in records), encoding="utf-8")

    def seal(self, target, url="http://127.0.0.1:58724"):
        preparation = self.root / "app/build/native-build-receipts" / (uuid.uuid4().hex + ".source.json")
        self.worker["prepare_build"](self.root, target, "release", url, self.flutter, preparation)
        return self.worker["complete_build"](self.root, target, "release", url, self.flutter, preparation, 0)

    def assemble(self, **overrides):
        values = {"repo": self.root, "output": self.output, "runner": self.runner,
                  "sites": [self.site], "media": self.media,
                  "core_url": "http://127.0.0.1:58724", "app_url": "http://127.0.0.1:58724",
                  "vc_runtime": self.vc_runtime, "vc_notices": [self.vc_notice]}
        values.update(overrides)
        with mock.patch.object(self.worker["sys"], "base_prefix", str(self.base)):
            # Source commit is a factual local test repo identity, not publication.
            original = self.worker["subprocess"].run

            def run(args, **kwargs):
                if args[-2:] == ["rev-parse", "HEAD"]:
                    return subprocess.CompletedProcess(args, 0, "a" * 40 + "\n", "")
                return original(args, **kwargs)

            with mock.patch.object(self.worker["subprocess"], "run", side_effect=run):
                return self.worker["assemble"](**values)

    def test_endpoint_and_compiled_app_binding_fail_before_output(self):
        for url in ("http://127.0.0.1:8201", "http://localhost:58724", "https://example.com"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                self.assemble(core_url=url)
            self.assertFalse(self.output.exists())
        with self.assertRaisesRegex(ValueError, "compiled Dart define"):
            self.assemble(app_url="http://127.0.0.1:58725")
        self.assertFalse(self.output.exists())
        (self.runner / "data/app.so").write_bytes(b"http://127.0.0.1:58725")
        with self.assertRaisesRegex(ValueError, "compiled Windows snapshot"):
            self.assemble()
        self.assertFalse(self.output.exists())

    def test_dependency_closure_obeys_extras_and_refuses_missing_versions(self):
        self.dist("bundle-second", "2.0")
        self.dist("bundle-extra", "3.0")
        self.dist("bundle-parent", "1.0", (
            "bundle-second>=2", "bundle-extra==3; extra == 'office'",
            "unavailable-package; python_version < '2'",
        ))
        requirements = self.root / "requirements.txt"
        requirements.write_text("bundle-parent[office]==1\n", encoding="utf-8")
        closure = self.worker["requirements_closure"](requirements, [self.site])
        self.assertEqual(set(closure), {"bundle-parent", "bundle-second", "bundle-extra"})
        requirements.write_text("bundle-second==99\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "does not satisfy"):
            self.worker["requirements_closure"](requirements, [self.site])
        requirements.write_text("missing-package\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "missing"):
            self.worker["requirements_closure"](requirements, [self.site])

    def test_bundle_contains_base_python_and_selected_wheels_never_private_data(self):
        for name in (".env", "data/monitor.db", "data/platform_cookies.json",
                     "system_config.json", "brand_directory.json", "personal-notes.txt",
                     "work/private.py", "tests/test_data.py"):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"PRIVATE_SENTINEL")
        (self.site / "unselected_private.py").write_bytes(b"PRIVATE_SENTINEL")
        (self.site / "startup.pth").write_text("import private_hook\n", encoding="utf-8")
        for name in ("domain/__init__.py", "domain/models/__init__.py", "domain/models/report.py"):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# production domain model, not model weights\n", encoding="utf-8")
        manifest = self.assemble()
        payload = [p for p in self.output.rglob("*") if p.is_file()]
        self.assertFalse(any(b"PRIVATE_SENTINEL" in p.read_bytes() for p in payload))
        self.assertFalse(any(p.suffix in {".pth", ".db"} for p in payload))
        self.assertTrue((self.output / "runtime/python/python313.dll").is_file())
        self.assertTrue((self.output / "runtime/python/Lib/os.py").is_file())
        self.assertTrue((self.output / "runtime/python/Lib/site-packages/bundle_fixture.py").is_file())
        self.assertTrue((self.output / "core/domain/models/report.py").is_file())
        self.assertTrue((self.output / "app/msvcp140.dll").is_file())
        self.assertEqual((self.output / "runtime/python/vcruntime140.dll").read_bytes(),
                         b"isolated-release-redist-fixture")
        self.assertNotIn(str(self.base), (self.output / "runtime/python/python313._pth").read_text())
        self.assertFalse(manifest["installer"])
        self.assertEqual(manifest["runtime_acceptance"], "NOT_VERIFIED")
        self.assertEqual(manifest["core_port"], 58724)

    def test_existing_output_and_missing_media_are_preserved(self):
        self.output.mkdir()
        sentinel = self.output / "keep.txt"
        sentinel.write_bytes(b"existing-output")
        with self.assertRaisesRegex(ValueError, "new directory"):
            self.assemble()
        self.assertEqual(sentinel.read_bytes(), b"existing-output")
        self.output = self.h.scratch_root / "missing-media"
        (self.media / "ffprobe.exe").unlink()
        with self.assertRaisesRegex(ValueError, "ffprobe.exe"):
            self.assemble()
        self.assertFalse(self.output.exists())
        (self.media / "ffprobe.exe").write_bytes(b"restored-media-fixture")
        (self.vc_runtime / "msvcp140.dll").unlink()
        with self.assertRaisesRegex(ValueError, "Visual C\\+\\+ redistributable missing"):
            self.assemble()
        self.assertFalse(self.output.exists())

    def test_ignored_in_project_distribution_contains_web_without_recopying_outputs(self):
        previous = self.root / "app/build/distribution/OEVIRA-old/keep.txt"
        previous.parent.mkdir(parents=True)
        previous.write_bytes(b"PRIVATE_OLD_OUTPUT")
        self.output = self.root / "app/build/distribution/OEVIRA-1.0.0"
        manifest = self.assemble()
        web = self.output / "core/app/build/web"
        self.assertEqual((web / "main.dart.js").read_bytes(),
                         (self.root / "app/build/web/main.dart.js").read_bytes())
        self.assertEqual(manifest["workspace_web"]["root"], "core/app/build/web")
        self.assertEqual(manifest["workspace_web"]["main_sha256"],
                         hashlib.sha256((web / "main.dart.js").read_bytes()).hexdigest())
        self.assertEqual(previous.read_bytes(), b"PRIVATE_OLD_OUTPUT")
        self.assertFalse(any("distribution" in f["path"] for f in manifest["files"]))

    def test_only_the_exact_ignored_in_project_output_root_is_allowed(self):
        for output in (self.root / "OEVIRA-1", self.root / "app/build/OEVIRA-1",
                       self.root / "app/build/distribution/not-a-product-bundle"):
            with self.subTest(output=output), self.assertRaisesRegex(ValueError, "In-project bundles"):
                self.assemble(output=output)
            self.assertFalse(output.exists())
        (self.root / "app/.gitignore").write_text("", encoding="utf-8")
        output = self.root / "app/build/distribution/OEVIRA-1"
        with self.assertRaisesRegex(ValueError, "In-project bundles"):
            self.assemble(output=output)
        self.assertFalse(output.exists())

    def test_linked_distribution_root_is_rejected_without_touching_target(self):
        target = self.h.scratch_root / "separate-output"
        target.mkdir()
        sentinel = target / "keep.txt"
        sentinel.write_bytes(b"protected-target")
        _create_junction(self.root / "app/build/distribution", target)
        with self.assertRaisesRegex(ValueError, "Linked bundle"):
            self.assemble(output=self.root / "app/build/distribution/OEVIRA-1")
        self.assertEqual(sentinel.read_bytes(), b"protected-target")
        self.assertFalse((target / "OEVIRA-1").exists())

    def test_missing_or_different_version_web_build_fails_before_output(self):
        main = self.root / "app/build/web/main.dart.js"
        main.unlink()
        with self.assertRaisesRegex(ValueError, "Web Workspace build is incomplete"):
            self.assemble()
        self.assertFalse(self.output.exists())
        main.write_text("restored fixture", encoding="utf-8")
        (self.root / "app/build/web/version.json").write_text(
            json.dumps({"version": "0.9.0", "build_number": "1"}), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Web build version differs"):
            self.assemble()
        self.assertFalse(self.output.exists())

    def test_missing_build_receipt_cannot_adopt_a_same_version_existing_web_build(self):
        self.worker["build_receipt_path"](self.root, "web").unlink()
        with self.assertRaisesRegex(ValueError, "Verified web build receipt is missing"):
            self.assemble()
        self.assertFalse(self.output.exists())

    def test_same_version_web_built_for_a_different_core_is_rejected(self):
        self.seal("web", "http://127.0.0.1:58725")
        with self.assertRaisesRegex(ValueError, "Verified web build configuration/source/output"):
            self.assemble()
        self.assertFalse(self.output.exists())

    def test_same_version_stale_web_source_and_changed_output_are_rejected(self):
        main = self.root / "app/build/web/main.dart.js"
        original = main.read_bytes()
        main.write_bytes(b"different-compiled-output-with-unchanged-version-json")
        with self.assertRaisesRegex(ValueError, "Verified web build configuration/source/output"):
            self.assemble()
        self.assertFalse(self.output.exists())
        main.write_bytes(original)
        (self.root / "app/lib/main.dart").write_text("void main() { print('changed source'); }\n", encoding="utf-8")
        self.seal("windows")
        with self.assertRaisesRegex(ValueError, "Verified web build configuration/source/output"):
            self.assemble()
        self.assertFalse(self.output.exists())

    def test_build_receipts_ignore_backend_and_governance_changes(self):
        (self.root / "app.py").write_text("# separately frozen Core fix\n", encoding="utf-8")
        (self.root / "00-GOVERNANCE/current.md").write_text("# later publication\n", encoding="utf-8")
        manifest = self.assemble()
        self.assertEqual(manifest["flutter_build_receipts"]["binding"], "ACTUAL_BUILD_ARGUMENTS_SOURCE_AND_OUTPUT_HASHES")
        for target in ("web", "windows"):
            self.assertTrue((self.output / f"notices/build/{target}.json").is_file())

    def test_failed_compilation_and_source_drift_never_publish_a_new_verified_receipt(self):
        receipt = self.worker["build_receipt_path"](self.root, "web")
        receipt.unlink()
        preparation = receipt.parent / "pending.source.json"
        self.worker["prepare_build"](self.root, "web", "release", "http://127.0.0.1:58724", self.flutter, preparation)
        with self.assertRaisesRegex(ValueError, "failed Flutter invocation"):
            self.worker["complete_build"](self.root, "web", "release", "http://127.0.0.1:58724", self.flutter, preparation, 23)
        self.assertFalse(receipt.exists())
        (self.root / "app/pubspec.lock").write_text("packages: {changed: true}\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "configuration/source changed"):
            self.worker["complete_build"](self.root, "web", "release", "http://127.0.0.1:58724", self.flutter, preparation, 0)
        self.assertFalse(receipt.exists())

    def test_web_wrapper_records_actual_arguments_and_successful_output_without_real_sdk(self):
        self._invoke_web_wrapper(0)

    def test_web_wrapper_refuses_failed_fake_compilation_without_publishing_receipt(self):
        self._invoke_web_wrapper(23)

    def test_web_wrapper_archives_only_a_stale_path_marker_before_fake_build(self):
        self._invoke_web_wrapper(0, "changed")

    def test_web_wrapper_preserves_a_marker_already_using_the_same_alias(self):
        self._invoke_web_wrapper(0, "same")

    def test_web_and_windows_receipts_reject_empty_asset_or_font_manifests(self):
        for target, assets in (("web", self.root / "app/build/web/assets"),
                               ("windows", self.runner / "data/flutter_assets")):
            for name in ("AssetManifest.bin", "FontManifest.json"):
                with self.subTest(target=target, missing=name):
                    path = assets / name
                    original = path.read_bytes()
                    path.write_bytes(b"")
                    with self.assertRaisesRegex(ValueError, "Required Flutter asset is missing/empty"):
                        self.seal(target)
                    path.write_bytes(original)

    def test_web_and_windows_receipts_require_every_asset_manifest_variant_file(self):
        def size(value):
            if value < 254:
                return bytes([value])
            if value <= 0xFFFF:
                return b"\xfe" + value.to_bytes(2, "little")
            return b"\xff" + value.to_bytes(4, "little")

        encoded = bytearray()

        def encode(value):
            if isinstance(value, str):
                payload = value.encode("utf-8")
                encoded.extend(b"\x07" + size(len(payload)) + payload)
            elif isinstance(value, float):
                encoded.append(6)
                encoded.extend(b"\x00" * ((-len(encoded)) % 8))
                encoded.extend(struct.pack("<d", value))
            elif isinstance(value, list):
                encoded.extend(b"\x0c" + size(len(value)))
                for item in value:
                    encode(item)
            elif isinstance(value, dict):
                encoded.extend(b"\x0d" + size(len(value)))
                for key, item in value.items():
                    encode(key)
                    encode(item)
            else:
                raise AssertionError(f"unsupported fixture value: {value!r}")

        encode({"assets/manifest-only.dat": [
            {"asset": "assets/manifest-only.dat", "dpr": 2.0}
        ]})
        for target, assets in (("web", self.root / "app/build/web/assets"),
                               ("windows", self.runner / "data/flutter_assets")):
            with self.subTest(target=target):
                (assets / "AssetManifest.bin").write_bytes(encoded)
                bundled = assets / "assets/manifest-only.dat"
                bundled.parent.mkdir(parents=True, exist_ok=True)
                bundled.write_bytes(b"manifest-listed fixture")
                self.seal(target)
                bundled.unlink()
                with self.assertRaisesRegex(ValueError, "Required Flutter asset is missing/empty: assets/manifest-only.dat"):
                    self.seal(target)

    def test_web_declared_assets_fonts_and_material_icons_must_be_in_the_actual_output(self):
        spec = self.root / "app/pubspec.yaml"
        spec.write_text(spec.read_text("utf-8") +
            "flutter:\n  uses-material-design: true\n  assets:\n    - assets/logo.png\n"
            "  fonts:\n    - family: ProductFont\n      fonts:\n        - asset: assets/ProductFont.ttf\n", encoding="utf-8")
        source = self.root / "app/assets"
        source.mkdir()
        (source / "logo.png").write_bytes(b"original-product-asset")
        (source / "ProductFont.ttf").write_bytes(b"original-product-font")
        assets = self.root / "app/build/web/assets"
        (assets / "assets").mkdir()
        for name in ("logo.png", "ProductFont.ttf"):
            (assets / "assets" / name).write_bytes((source / name).read_bytes())
        (assets / "FontManifest.json").write_text(json.dumps([
            {"family": "ProductFont", "fonts": [{"asset": "assets/ProductFont.ttf"}]}]), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "MaterialIcons font is missing"):
            self.seal("web")
        fonts = json.loads((assets / "FontManifest.json").read_text("utf-8"))
        fonts.append({"family": "MaterialIcons", "fonts": [{"asset": "fonts/MaterialIcons-Regular.otf"}]})
        (assets / "FontManifest.json").write_text(json.dumps(fonts), encoding="utf-8")
        (assets / "fonts").mkdir()
        (assets / "fonts/MaterialIcons-Regular.otf").write_bytes(b"tree-shaken-icon-font")
        self.seal("web")
        (assets / "assets/ProductFont.ttf").unlink()
        with self.assertRaisesRegex(ValueError, "Required Flutter asset is missing/empty"):
            self.seal("web")
        (assets / "assets/ProductFont.ttf").write_bytes(b"wrong-font-version")
        with self.assertRaisesRegex(ValueError, "source asset differs"):
            self.seal("web")

    def _invoke_web_wrapper(self, exit_code, marker_mode=""):
        script = self.root / "app/tool/build_windows.ps1"
        script.parent.mkdir()
        script.write_bytes(SOURCE_HELPER.read_bytes())
        alias = self.h.scratch_root / "web-app"
        _create_junction(alias, self.root / "app")
        marker = self.root / "app/build/web/.last_build_id"
        if marker_mode:
            marker.write_text("b" * 32, encoding="ascii")
            old = self.root / "app/.dart_tool/flutter_build" / ("b" * 32)
            old.mkdir(parents=True)
            prefix = str(self.root / "app") if marker_mode == "changed" else str(alias)
            (old / "outputs.json").write_text(json.dumps([prefix + "\\build\\web\\assets\\FontManifest.json"]), encoding="utf-8")
        marker_check = ('if exist "build\\web\\.last_build_id" exit /b 94\n' if marker_mode == "changed" else
                        'if not exist "build\\web\\.last_build_id" exit /b 95\n' if marker_mode == "same" else "")
        self.flutter.write_text(
            '@echo off\nif not "%~1"=="build" exit /b 91\n'
            'if not "%~2"=="web" exit /b 92\n'
            'echo %*\necho %CD%\n' + marker_check +
            f'exit /b {exit_code}\n', encoding="ascii")
        receipt_path = self.worker["build_receipt_path"](self.root, "web")
        receipt_path.unlink()
        result = subprocess.run([
            POWERSHELL, "-NoLogo", "-NoProfile", "-NonInteractive", "-File", str(script),
            "-BuildWeb", "-FlutterSdk", str(self.h.sdk_dir),
            "-ProjectAlias", str(alias),
            "-CoreBaseUrl", "http://127.0.0.1:58724", "-PythonExecutable", sys.executable,
        ], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60, check=False)
        if exit_code:
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(receipt_path.exists())
        else:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("--dart-define=LUMENIS_CORE_BASE_URL=http://127.0.0.1:58724", result.stdout)
            self.assertIn(str(alias).lower(), result.stdout.lower())
            receipt = json.loads(receipt_path.read_text("utf-8"))
            self.assertEqual(receipt["arguments"], ["build", "web", "--release", "--no-pub",
                "--dart-define=LUMENIS_CORE_BASE_URL=http://127.0.0.1:58724"])
            self.assertEqual(receipt["outputs"], self.worker["inventory"](self.root / "app/build/web"))
            self.assertEqual(receipt["sources"], self.worker["ui_sources"](self.root))
            archived = list((self.root / "app/build/native-build-receipts").glob("web-cache-*/flutter-last-build-id"))
            self.assertEqual(len(archived), 1 if marker_mode == "changed" else 0)
            if marker_mode == "same":
                self.assertEqual(marker.read_text("ascii"), "b" * 32)

    def test_dependency_notice_directories_are_indexed_even_without_license_filename(self):
        info = self.site / "bundle_fixture-1.0.dist-info"
        notice = info / "licenses/data/windows_x64/BUILD_LICENSES/pdfium.txt"
        notice.parent.mkdir(parents=True)
        notice.write_text("fixture PDFium dependency terms", encoding="utf-8")
        with (info / "RECORD").open("a", encoding="utf-8") as stream:
            stream.write(f"{notice.relative_to(self.site).as_posix()},,\n")
        manifest = self.assemble()
        records = manifest["dependencies"][0]["license_notices"]
        entry = next(record for record in records if record["path"].endswith("/pdfium.txt"))
        self.assertEqual(entry["sha256"], hashlib.sha256(notice.read_bytes()).hexdigest())
        self.assertEqual((self.output / entry["path"]).read_bytes(), notice.read_bytes())

    def test_version_pinned_official_notice_is_included_and_tampering_is_rejected(self):
        self.dist("ordered-set", "4.1.0")
        (self.root / "requirements.txt").write_text("ordered-set==4.1.0\n", encoding="utf-8")
        filename = "ordered-set-4.1.0.LICENSE.txt"
        notice = self.root / "vendor/lumenis-reuse-notices/windows-python" / filename
        notice.parent.mkdir(parents=True)
        original = REPO_ROOT / "vendor/lumenis-reuse-notices/windows-python" / filename
        notice.write_bytes(original.read_bytes())
        manifest = self.assemble()
        dependency = manifest["dependencies"][0]
        supplemental = next(entry for entry in dependency["license_notices"] if entry["source"].startswith("https://"))
        self.assertIn("d921651b2737f5cfe711868fab558a8ef79e26ca", supplemental["source"])
        self.assertEqual((self.output / supplemental["path"]).read_bytes(), original.read_bytes())
        self.assertNotIn(("ordered-set", "4.2.0"), self.worker["SUPPLEMENTAL_LICENSES"])
        notice.write_text("changed license", encoding="utf-8")
        dist = self.worker["metadata"].Distribution.at(self.site / "ordered_set-4.1.0.dist-info")
        with self.assertRaisesRegex(ValueError, "Pinned supplemental license missing or changed"):
            self.worker["dependency_license"]("ordered-set", dist, self.root, self.media)

    def test_declared_magika_without_detector_resource_is_rejected(self):
        self.dist("magika", "0.6.3")
        (self.root / "requirements.txt").write_text("magika==0.6.3\n", encoding="utf-8")
        filename = "magika-0.6.3.LICENSE.txt"
        notice = self.root / "vendor/lumenis-reuse-notices/windows-python" / filename
        notice.parent.mkdir(parents=True)
        notice.write_bytes((REPO_ROOT / "vendor/lumenis-reuse-notices/windows-python" / filename).read_bytes())
        with self.assertRaisesRegex(ValueError, "Expected exactly one pinned Magika"):
            self.assemble()

    def test_unknown_lgpl_is_identified_and_replaceable_source_is_preserved(self):
        info = self.site / "bundle_fixture-1.0.dist-info"
        text = (info / "METADATA").read_text("utf-8").replace("License: MIT\n", "")
        (info / "METADATA").write_text(text, encoding="utf-8")
        (info / "LICENSE").write_text("GNU LESSER GENERAL PUBLIC LICENSE\nVersion 3, 29 June 2007\n",
                                     encoding="utf-8")
        (self.media / "LICENSE.txt").write_bytes((REPO_ROOT / "tools/LICENSE").read_bytes())
        manifest = self.assemble()
        dependency = manifest["dependencies"][0]
        self.assertEqual(dependency["license_declared"], "UNKNOWN")
        self.assertEqual(dependency["license"], "LGPL-3.0")
        self.assertTrue(dependency["gpl_license_text_included"])
        self.assertFalse(dependency["library_modified_by_bundle"])
        self.assertEqual(dependency["library_replacement"], "PLAIN_PYTHON_SOURCE_REPLACEABLE")
        for entry in dependency["library_source_files"]:
            self.assertEqual(hashlib.sha256((self.output / entry["path"]).read_bytes()).hexdigest(), entry["sha256"])
        self.assertEqual(manifest["redistribution_clearance"], "BLOCKED")
        self.assertIn("VISUAL_STUDIO_REDISTRIBUTION_ENTITLEMENT_REQUIRED", manifest["redistribution_blockers"])
        self.assertTrue(manifest["visual_cpp_runtime"]["signature_does_not_grant_redistribution"])

    def test_mismatched_ffmpeg_build_readme_fails_before_output(self):
        readme = self.media / "README.txt"
        readme.write_text("Version: 9.0.2-full_build-www.gyan.dev\n", encoding="utf-8")
        original_sha = self.worker["sha"]
        hashes = {"ffmpeg.exe": "3256173f3f8bffd7df12227c68adf68025edb1832273a9530688a7bb1ed8edec",
                  "ffprobe.exe": "f0d36ecbbdd3bcfac3efa078c96c7271c2e68b3810595552ac3b7f17e9a65c52"}
        def sha(path):
            return hashes[path.name] if path.parent == self.media and path.name in hashes else original_sha(path)
        with mock.patch.dict(self.worker, sha=sha), self.assertRaisesRegex(ValueError, "different binary build"):
            self.assemble()
        self.assertFalse(self.output.exists())

    def test_full_build_parent_gpl_notice_is_used_without_copying_unselected_media_tree(self):
        info = self.site / "bundle_fixture-1.0.dist-info"
        (info / "METADATA").write_text("Name: bundle-fixture\nVersion: 1.0\n", encoding="utf-8")
        (info / "LICENSE").write_text("GNU LESSER GENERAL PUBLIC LICENSE\nVersion 3, 29 June 2007\n",
                                     encoding="utf-8")
        parent_license = self.h.fixture_root / "full-build-LICENSE.txt"
        parent_license.write_bytes((REPO_ROOT / "tools/LICENSE").read_bytes())
        # An explicitly selected original notice can live outside the bin directory.
        notice = self.h.fixture_root / "full-build/LICENSE"
        notice.parent.mkdir()
        notice.write_bytes(parent_license.read_bytes())
        manifest = self.assemble(media_notices=[notice])
        self.assertTrue(manifest["dependencies"][0]["gpl_license_text_included"])
        self.assertEqual((self.output / "notices/ffmpeg/LICENSE").read_bytes(), notice.read_bytes())
        self.assertFalse(any("full-build-LICENSE" in entry["path"] for entry in manifest["files"]))

    def test_changed_media_cannot_publish_notices_bound_to_earlier_binaries(self):
        original = self.worker["dependency_license"]
        def license_record(*args, **kwargs):
            result = original(*args, **kwargs)
            (self.media / "ffmpeg.exe").write_bytes(b"changed-after-build-identity-selection")
            return result
        with mock.patch.dict(self.worker, dependency_license=license_record), self.assertRaisesRegex(
                ValueError, "Media binary identity changed"):
            self.assemble()
        self.assertTrue(self.output.is_dir())
        self.assertFalse((self.output / "bundle-manifest.json").exists())

    def test_describe_plan_checks_hashes_and_never_creates_user_data(self):
        self.assemble()
        data = self.h.scratch_root / "future-user-data"
        windows_powershell = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
        self.assertTrue(windows_powershell.is_file())
        environment = os.environ.copy()
        environment["PSModulePath"] = str(Path(POWERSHELL).parent / "Modules")
        commands = [[host, "-NoProfile", "-NonInteractive", "-File",
                     str(self.output / "core/scripts/start_production.ps1"),
                     "-DesktopBundle", "-DescribeBundle", "-DataRoot", str(data)]
                    for host in (POWERSHELL, str(windows_powershell))]
        for command in commands:
            with self.subTest(host=command[0]):
                result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace",
                                        env=environment, timeout=30, check=False)
                self.assertEqual(result.returncode, 0, result.stderr)
                plan = json.loads(result.stdout)
                self.assertEqual(plan["core_port"], 58724)
                self.assertFalse(plan["starts_product"])
                self.assertFalse(data.exists())
        cmd = (self.output / "Start-OEVIRA.cmd").read_text("ascii")
        self.assertIn('setlocal\nset "PSModulePath="\n', cmd)
        self.assertIn('"%SystemRoot%\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"', cmd)
        self.assertNotIn("pwsh", cmd.lower())
        (self.output / "core/app.py").write_text("changed", encoding="utf-8")
        for command in commands:
            with self.subTest(tampered_host=command[0]):
                result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace",
                                        env=environment, timeout=30, check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("identity changed", result.stderr)
                self.assertFalse(data.exists())

    def test_native_owned_job_compiles_without_starting_any_process(self):
        import base64
        source = (REPO_ROOT / "scripts/start_production.ps1").read_text("utf-8-sig")
        native = source.split("Add-Type -TypeDefinition @'\n", 1)[1].split("\n'@", 1)[0]
        command = "Add-Type -TypeDefinition @'\n" + native + "\n'@\n'JOB_TYPE_COMPILED'"
        encoded = base64.b64encode(command.encode("utf-16le")).decode("ascii")
        result = subprocess.run([POWERSHELL, "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
                                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("JOB_TYPE_COMPILED", result.stdout)

    def test_describe_plan_restores_module_path_in_the_calling_shell(self):
        import base64
        self.assemble()
        environment = os.environ.copy()
        environment.update(BUNDLE_TEST_SCRIPT=str(self.output / "core/scripts/start_production.ps1"),
                           BUNDLE_TEST_DATA=str(self.h.scratch_root / "not-created-by-inspection"),
                           PSModulePath=str(Path(POWERSHELL).parent / "Modules"))
        command = r"""
$before = $env:PSModulePath
& $env:BUNDLE_TEST_SCRIPT -DesktopBundle -DescribeBundle -DataRoot $env:BUNDLE_TEST_DATA
if ($LASTEXITCODE -ne 0) { throw 'Inspection failed' }
if ($env:PSModulePath -cne $before) { throw 'The calling process module path changed' }
[Console]::WriteLine('CALLING_MODULE_PATH_RESTORED')
"""
        encoded = base64.b64encode(command.encode("utf-16le")).decode("ascii")
        windows_powershell = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
        for host in (POWERSHELL, str(windows_powershell)):
            with self.subTest(host=host):
                result = subprocess.run([host, "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
                    env=environment, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30, check=False)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("CALLING_MODULE_PATH_RESTORED", result.stdout)
                self.assertFalse(Path(environment["BUNDLE_TEST_DATA"]).exists())

    def test_native_job_reaps_only_its_owned_helper_tree(self):
        """Real Windows job mechanics with disposable PowerShell helpers only."""
        import base64
        source = (REPO_ROOT / "scripts/start_production.ps1").read_text("utf-8-sig")
        native = source.split("Add-Type -TypeDefinition @'\n", 1)[1].split("\n'@", 1)[0]
        helper = self.h.fixture_root / "owned-helper.ps1"
        marker = self.h.fixture_root / "owned-helper-pids.txt"
        helper.write_text(r"""
$exe=Join-Path $env:SystemRoot 'System32/WindowsPowerShell/v1.0/powershell.exe'
$child=Start-Process $exe -WindowStyle Hidden -PassThru -ArgumentList @('-NoProfile','-NonInteractive','-Command','Start-Sleep -Seconds 30')
[IO.File]::WriteAllText($env:BUNDLE_TEST_JOB_MARKER,"$PID,$($child.Id)")
Start-Sleep -Seconds 30
""", encoding="utf-8")
        environment = os.environ.copy()
        environment.update(BUNDLE_TEST_JOB_HELPER=str(helper), BUNDLE_TEST_JOB_MARKER=str(marker))
        command = "$ErrorActionPreference='Stop'\nAdd-Type -TypeDefinition @'\n" + native + "\n'@\n"
        command += r"""
$job=New-Object OeviraDesktopJob
$owned=$null
$grandchild=$null
try {
 $values=@{}
 foreach($entry in [Environment]::GetEnvironmentVariables().GetEnumerator()){$values[[string]$entry.Key]=[string]$entry.Value}
 $exe=Join-Path $env:SystemRoot 'System32/WindowsPowerShell/v1.0/powershell.exe'
 $arguments='-NoLogo -NoProfile -NonInteractive -File "'+$env:BUNDLE_TEST_JOB_HELPER+'"'
 $owned=$job.Start($exe,$arguments,(Split-Path -Parent $env:BUNDLE_TEST_JOB_HELPER),$values,$true)
 for($i=0;$i -lt 60 -and -not(Test-Path -LiteralPath $env:BUNDLE_TEST_JOB_MARKER);$i++){Start-Sleep -Milliseconds 100}
 if(-not(Test-Path -LiteralPath $env:BUNDLE_TEST_JOB_MARKER)){throw 'Owned helper did not become ready'}
 $ids=(Get-Content -LiteralPath $env:BUNDLE_TEST_JOB_MARKER -Raw).Split(',')
 if([int]$ids[0] -ne $owned.Id){throw 'Owned helper identity mismatch'}
 $grandchild=[Diagnostics.Process]::GetProcessById([int]$ids[1])
 $heldHandle=$grandchild.Handle
 $job.Dispose()
 if(-not $owned.WaitForExit(5000) -or -not $grandchild.WaitForExit(5000)){throw 'Owned helper tree survived job close'}
 'OWNED_HELPER_TREE_REAPED'
} finally {
 $job.Dispose()
 foreach($member in @($grandchild,$owned)){
  if($null -ne $member){if(-not $member.HasExited){$member.Kill();$member.WaitForExit(5000)|Out-Null};$member.Dispose()}
 }
}
"""
        encoded = base64.b64encode(command.encode("utf-16le")).decode("ascii")
        result = subprocess.run([POWERSHELL, "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
                                capture_output=True, text=True, encoding="utf-8", errors="replace",
                                env=environment, timeout=30, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("OWNED_HELPER_TREE_REAPED", result.stdout)

    def test_data_initialization_preserves_owned_database_and_refuses_legacy_root(self):
        import base64
        self.assemble()
        data = self.h.scratch_root / "user-data"
        legacy = self.h.scratch_root / "legacy-data"
        legacy.mkdir()
        (legacy / "monitor.db").write_bytes(b"PROTECTED_EXISTING_DATABASE")
        environment = os.environ.copy()
        environment.update(BUNDLE_TEST_SCRIPT=str(self.output / "core/scripts/start_production.ps1"),
                           BUNDLE_TEST_CORE=str(self.output / "core"),
                           BUNDLE_TEST_DATA=str(data), BUNDLE_TEST_LEGACY=str(legacy))
        command = r"""
$ErrorActionPreference='Stop'
$syntax=[Management.Automation.Language.Parser]::ParseFile($env:BUNDLE_TEST_SCRIPT,[ref]$null,[ref]$null)
$function=$syntax.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Initialize-LumenisDesktopData'},$true)
Invoke-Expression $function.Extent.Text
$plan=[pscustomobject]@{Core=$env:BUNDLE_TEST_CORE;Data=$env:BUNDLE_TEST_DATA}
Initialize-LumenisDesktopData $plan
[IO.File]::WriteAllText((Join-Path $plan.Data 'monitor.db'),'PERSISTENT_USER_DATABASE')
Initialize-LumenisDesktopData $plan
$plan.Data=$env:BUNDLE_TEST_LEGACY
try {Initialize-LumenisDesktopData $plan;throw 'EXPECTED_LEGACY_REFUSAL'} catch {
 if($_.Exception.Message -eq 'EXPECTED_LEGACY_REFUSAL'){throw}
 if($_.Exception.Message -notlike '*nonempty data root*'){throw}
}
$plan.Core=Join-Path (Split-Path -Parent $env:BUNDLE_TEST_CORE) 'separate-adoption-core'
[IO.Directory]::CreateDirectory($plan.Core) | Out-Null
Initialize-LumenisDesktopData $plan -AdoptExisting
'DATA_OWNERSHIP_CHECKED'
"""
        encoded = base64.b64encode(command.encode("utf-16le")).decode("ascii")
        result = subprocess.run([POWERSHELL, "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
                                capture_output=True, text=True, encoding="utf-8", errors="replace", env=environment, timeout=30, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("DATA_OWNERSHIP_CHECKED", result.stdout)
        self.assertEqual((data / "monitor.db").read_text(), "PERSISTENT_USER_DATABASE")
        self.assertEqual((legacy / "monitor.db").read_bytes(), b"PROTECTED_EXISTING_DATABASE")
        self.assertEqual(json.loads((legacy / ".oevira-user-data.json").read_text())["schema"],
                         "lumenis.desktop-user-data/v1")


if __name__ == "__main__":
    unittest.main(verbosity=2)
