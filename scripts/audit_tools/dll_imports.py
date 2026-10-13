"""Read a dumpbin transcript or statically inspect ONE explicitly named binary.

Does not execute the inspected EXE/DLL, recurse folders, resolve system DLLs,
install tools, change PATH, or write into the LUMENIS worktree. Standard library.
The optional external command is Microsoft dumpbin /imports, never LoadLibrary.
New wrapper authored for this review; upstream parser attribution is separate.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import time
from binnexus_imports import parse_imports

MAX_TEXT = 4 * 1024 * 1024
MAX_BINARY = 256 * 1024 * 1024


def regular_path(path: Path, max_size: int) -> Path:
    path = path.absolute()
    for part in (path, *path.parents):
        st = part.lstat()
        if stat.S_ISLNK(st.st_mode) or (getattr(st, 'st_file_attributes', 0) & 0x400):
            raise ValueError('Linked/reparse input paths are not accepted')
    st = path.stat()
    if not stat.S_ISREG(st.st_mode) or st.st_size > max_size:
        raise ValueError('Input is not a bounded regular file')
    return path


def bounded_read(path: Path, limit: int) -> bytes:
    with path.open('rb') as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError('Input grew beyond the size limit')
    return raw


def inspect_text(raw: bytes, exit_code: int | None, origin: str) -> dict:
    if len(raw) > MAX_TEXT:
        raise ValueError('Transcript exceeds size limit')
    base = {'schema': 'lumenis.static-import-observation.v1',
            'scope': 'STATIC_DIRECT_IMPORTS_ONLY', 'origin': origin,
            'tool_exit_code': exit_code,
            'transcript_sha256': hashlib.sha256(raw).hexdigest(),
            'runtime_verified': False, 'dependency_resolution_verified': False,
            'current_source_build_verified': False}
    if exit_code is None or exit_code != 0:
        return {**base, 'status': 'TOOL_RESULT_NOT_SUCCESSFUL', 'imports': None}
    # dumpbin DLL lines are ASCII. Other localized text is not reproduced.
    names = sorted(parse_imports(raw.decode('utf-8-sig', errors='replace')))
    return {**base, 'status': 'IMPORTS_OBSERVED' if names else 'NO_IMPORTS_OBSERVED_NOT_PROOF_OF_NONE',
            'imports': names, 'count': len(names)}


def inspect_binary(binary: Path, dumpbin: Path, timeout: float = 15.0) -> dict:
    if os.name != 'nt':
        raise ValueError('Binary mode requires Windows; text mode is cross-platform')
    if not 1 <= timeout <= 30:
        raise ValueError('timeout must be between 1 and 30 seconds')
    binary = regular_path(binary, MAX_BINARY)
    dumpbin = regular_path(dumpbin, 64 * 1024 * 1024)
    if binary.suffix.lower() not in {'.dll', '.exe'} or dumpbin.name.lower() != 'dumpbin.exe':
        raise ValueError('Expected an EXE/DLL and an explicitly trusted dumpbin.exe')
    before = hashlib.sha256(bounded_read(binary, MAX_BINARY)).hexdigest()
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        proc = subprocess.Popen([str(dumpbin), '/imports', str(binary)],
                                stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                shell=False)
        deadline = time.monotonic() + timeout
        try:
            while True:
                exceeded = os.fstat(out.fileno()).st_size > MAX_TEXT or os.fstat(err.fileno()).st_size > MAX_TEXT
                if exceeded:
                    raise ValueError('dumpbin output exceeded limit')
                if proc.poll() is not None:
                    break
                if time.monotonic() >= deadline:
                    raise TimeoutError('dumpbin hard timeout')
                time.sleep(0.03)
            out.seek(0)
            raw = out.read(MAX_TEXT + 1)
            result = inspect_text(raw, proc.returncode, 'direct_dumpbin_invocation')
        finally:
            if proc.poll() is None:
                proc.kill()
            proc.wait(timeout=3)
    after = hashlib.sha256(bounded_read(binary, MAX_BINARY)).hexdigest()
    if before != after:
        raise ValueError('Binary changed during observation; result rejected')
    result.update(binary_name=binary.name, binary_sha256=before, binary_unchanged=True)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--from-text', type=Path)
    modes.add_argument('--binary', type=Path)
    parser.add_argument('--reported-exit-code', type=int,
                        help='Required in transcript mode; supplied, not independently verified')
    parser.add_argument('--dumpbin', type=Path,
                        help='Absolute path to an existing trusted Microsoft dumpbin.exe')
    parser.add_argument('--timeout', type=float, default=15.0)
    args = parser.parse_args()
    try:
        if args.from_text:
            if args.reported_exit_code is None:
                parser.error('--from-text requires --reported-exit-code')
            result = inspect_text(bounded_read(regular_path(args.from_text, MAX_TEXT), MAX_TEXT),
                                  args.reported_exit_code, 'transcript_with_user_supplied_exit_code')
        else:
            if not args.dumpbin or not args.dumpbin.is_absolute():
                parser.error('--binary requires an absolute --dumpbin path')
            result = inspect_binary(args.binary, args.dumpbin, args.timeout)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result['status'] == 'IMPORTS_OBSERVED' else 3
    except (ValueError, OSError, TimeoutError, subprocess.SubprocessError) as exc:
        # No raw external stderr, command paths or inspected text are echoed.
        print(json.dumps({'status': 'NOT_VERIFIED', 'error_class': type(exc).__name__}), file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
