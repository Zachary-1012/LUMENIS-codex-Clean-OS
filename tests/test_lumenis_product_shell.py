"""Contract checks for the AI-first LUMENIS product hierarchy and reflow shell."""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_ai_first_aliases_and_hierarchy_are_explicit():
    source = _read("lumenis_frontend.py")
    assert 'redirect("/experience/#/AI-01")' in source
    assert 'redirect("/experience/#/CTH-01")' in source
    assert 'redirect("/experience/#/BMP-01")' in source
    assert 'redirect("/experience/#/SYS-05")' in source

    shell = _read("experience_v2/10_prototype/assets/shell.js")
    assert "LUMENIS AI -> CTH / BMP -> Settings" in shell
    assert "AI 对话" in shell
    assert "内容制作 · Content Studio" in shell
    assert "const ai = groupByKey" not in shell


def test_shared_content_is_linked_once_from_both_business_domains():
    shell = _read("experience_v2/10_prototype/assets/shell.js")
    assert "navGroupHTML('cth'" in shell
    assert "navGroupHTML('bmp'" in shell
    assert shell.count("id: 'SH-01'") == 1
    assert shell.count("const studio") == 1


def test_shell_has_adaptive_reflow_and_collapsed_navigation_affordance():
    css = _read("experience_v2/10_prototype/assets/shell.css")
    for width in ("max-width:1520px", "max-width:1280px", "max-width:1024px", "max-width:768px", "max-width:430px", "max-width:390px", "max-width:360px"):
        assert width in css
    assert "overflow-x:hidden" in css
    assert ".lum-nav-item__mark" in css
    assert ".lum-shared-skill-palette" in css


def test_ai_runtime_separates_chat_from_execution_and_uses_shared_surface():
    runtime = _read("experience_v2/10_prototype/assets/runtime.js")
    builder = _read("experience_runtime.py")
    app = _read("experience_v2/10_prototype/assets/app.js")
    assert "'/api/ai/chat'" in runtime
    assert "data-ai-execute" in builder
    assert '"title": "LUMENIS AI", "titleKey": None' in builder
    assert "id === 'AI-01' ? 'LUMENIS AI'" in app
    assert "data-shared-skill-palette" in builder
    assert "mountSharedSkillPalette" in runtime
    assert "data-ai-intent" not in runtime
