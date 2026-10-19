"""Real Bash regression for the existing Experience strict-mode selector."""
from pathlib import Path
import subprocess
import textwrap

import pytest


WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/platform-verify.yml"


def _selection_script():
    text = WORKFLOW.read_text(encoding="utf-8")
    start = text.index('          if ', text.index('          mode="--baseline"'))
    end = text.index('          fi\n', start) + len('          fi\n')
    # Execute the original condition and both branches under the actual CI shell
    # options. Only its already-discovered path input is supplied by this test.
    return (
        'set -e -o pipefail\nchanged="$(cat)"\nmode="--baseline"\n'
        + textwrap.dedent(text[start:end])
        + '\nprintf "selected_mode=%s\\n" "$mode"\n'
    )


@pytest.mark.parametrize("large", [False, True], ids=["short", "long"])
@pytest.mark.parametrize("surface_changed", [False, True], ids=["unrelated", "surface"])
def test_original_experience_selector_preserves_strict_under_pipefail(large, surface_changed):
    paths = ["app/lib/main.dart" if surface_changed else "tests/test_example.py"]
    if large:
        # Exceed pipe capacity deterministically. grep -q previously returned
        # early, causing the writer's SIGPIPE to select baseline under pipefail.
        paths.extend(f"research/history/{index:05d}-{'x' * 250}.json" for index in range(5000))
    completed = subprocess.run(
        ["/usr/bin/bash", "--noprofile", "--norc", "-c", _selection_script()],
        input="\n".join(paths) + "\n",
        text=True,
        capture_output=True,
        check=False,
        timeout=15,
    )
    assert completed.returncode == 0, completed.stderr
    expected = "--strict" if surface_changed else "--baseline"
    assert completed.stdout.splitlines()[-1] == f"selected_mode={expected}"
    assert "Broken pipe" not in completed.stderr
