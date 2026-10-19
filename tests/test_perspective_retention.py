"""G103 full view retention and explicit summary, through real CLI."""
import copy
import json
import subprocess
import sys
from pathlib import Path
import pytest
from scripts.campaign_plan import generate_plan
from scripts.perspective_adapter import adapt_plan, _PERSPECTIVE_SECTION_ORDER

@pytest.mark.parametrize('role', ['client', 'agency', 'vendor'])
def test_complete_view_preserves_every_section_and_original_order_tail(role):
    plan = generate_plan('原品牌', goal='真实目标', budget='未知')
    plan['sections']['用户原创附录'] = {'fact': ['未核实，不得承诺']}
    original = copy.deepcopy(plan)
    view = adapt_plan(plan, role)
    priority = [k for k in _PERSPECTIVE_SECTION_ORDER[role] if k in plan['sections']]
    assert list(view['sections']) == priority + [k for k in plan['sections'] if k not in priority]
    assert view['sections'] == plan['sections']
    assert view['view_kind'] == 'complete' and view['omitted_sections'] == []
    assert view['source_plan'] == original
    assert view['source_plan_ref'] == {'kind': 'inline_snapshot', 'field': 'source_plan'}
    view['sections']['用户原创附录']['fact'].append('编辑只影响视图')
    view['source_plan']['sections']['用户原创附录']['fact'].append('引用快照也独立')
    view['touchpoints'].append('编辑视图不影响原稿资源')
    assert plan == original

@pytest.mark.parametrize('role', ['client', 'agency', 'vendor'])
def test_summary_is_explicit_and_retains_full_source(role):
    plan = generate_plan('原品牌')
    plan['sections']['用户附录'] = '独立原创正文'
    view = adapt_plan(plan, role, summary=True)
    assert view['view_kind'] == 'summary'
    assert view['omitted_sections'] == [k for k in plan['sections'] if k not in view['sections']]
    assert '用户附录' in view['omitted_sections']
    assert view['source_plan'] == plan
    assert {k: plan['sections'][k] for k in view['sections']} == view['sections']

@pytest.mark.parametrize('value', ['false', 0, 1, None])
def test_summary_not_implicitly_coerced(value):
    with pytest.raises(ValueError, match='boolean'):
        adapt_plan(generate_plan('原品牌'), summary=value)

@pytest.mark.parametrize('role', ['client', 'agency', 'vendor'])
@pytest.mark.parametrize('summary', [False, True])
def test_cli_json_and_text_never_silently_lose_original_sections(role, summary):
    script = Path(__file__).resolve().parents[1] / 'scripts' / 'perspective_adapter.py'
    command = [sys.executable, str(script), '--perspective', role, '--brand', '实际输入品牌']
    if summary: command.append('--summary')
    result = json.loads(subprocess.check_output(command + ['--json'], text=True))
    text = subprocess.check_output(command, text=True)
    assert result['source_plan']['meta']['brand'] == '实际输入品牌'
    assert len(result['source_plan']['sections']) == 10
    assert result['view_kind'] == ('summary' if summary else 'complete')
    assert all(heading in text for heading in result['source_plan']['sections'])
    if summary: assert '[摘要视图]' in text and '[完整原稿]' in text
    else: assert len(result['sections']) == 10
