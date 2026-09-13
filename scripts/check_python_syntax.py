"""Check tracked Python source against the CI grammar without writing bytecode."""
import ast
from pathlib import Path
import subprocess


def main():
    root = Path(__file__).resolve().parents[1]
    files = subprocess.check_output(
        ['git', 'ls-files', '-z', '--', '*.py'], cwd=root
    ).decode('utf-8').split('\0')
    errors = []
    for name in filter(None, files):
        try:
            ast.parse((root / name).read_text(encoding='utf-8-sig'),
                      filename=name, feature_version=(3, 11))
        except (SyntaxError, UnicodeError, OSError) as exc:
            errors.append((name, str(exc)))
    for name, error in errors:
        print(f'{name}: {error}')
    print(f'Python 3.11 syntax: {len(files)-1} tracked files, {len(errors)} errors')
    return bool(errors)


if __name__ == '__main__':
    raise SystemExit(main())
