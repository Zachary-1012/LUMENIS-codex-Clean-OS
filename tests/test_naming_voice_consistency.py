"""Bounded regression checks; no live system, model or production data access."""
from pathlib import Path
import subprocess
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
PLAN = ROOT / '00-GOVERNANCE/LOOP-PLAN-20261014/product-plan-full.md'
SKETCH = ROOT / '00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md'


def test_repository_display_name_and_compatibility_id(monkeypatch, tmp_path):
    from flask import Flask
    import lumenis_agg_api as api
    monkeypatch.setattr(api, '_ZBC_ROOT', tmp_path / 'source')
    monkeypatch.setattr(api, '_osai_root', lambda: None)
    monkeypatch.setattr(api, '_git_info', lambda p: {'available': False, 'status': 'UNAVAILABLE'})
    app = Flask('repository-display-check')
    app.register_blueprint(api.agg_bp)
    response = app.test_client().get('/api/system/repository')
    assert response.status_code == 200
    record = response.get_json()['repositories'][0]
    assert record['name'] == 'LUMENIS-codex-Clean-OS'
    assert record['repository_id'] == 'ZBC'
    assert record['git']['status'] == 'UNAVAILABLE'


def test_models_display_boundary_uses_current_identity(monkeypatch):
    from flask import Flask
    import lumenis_agg_api as api
    from lumenis.system.ai_gateway import core, user_api_adapter
    monkeypatch.setattr(core, 'owned_service_observation', lambda domain=None: {
        'state': 'UNAVAILABLE', 'service_binding': 'NOT_BOUND', 'available': False,
        'reason': 'OWNED_RUNTIME_NOT_BOUND', 'model_id': None,
    })
    monkeypatch.setattr(user_api_adapter, 'is_selected', lambda: False)
    app = Flask('models-display-check')
    app.register_blueprint(api.agg_bp)
    response = app.test_client().get('/api/intelligence/models')
    assert response.status_code == 200
    body = response.get_json()
    assert body['truth_boundary'] == 'AI is enhancement only; LUMENIS Canonical data and Evidence remain authoritative'
    assert body['runtime_available'] is False
    assert body['fallback_chain'] == []


@pytest.mark.parametrize('signals,level,confidence,expected', [
    ({'keyword': '展览', 'volume_notes': 12, 'risk_events': 2}, 'repeated', 0.52, 'LUMENIS 真实信号'),
    ({'keyword': '展览', 'volume_notes': 1}, 'single_case', 0.41, 'LUMENIS 真实信号'),
    ({'volume_notes': 0}, 'assumption', 0.35, '未接入 LUMENIS 真实样本'),
])
def test_idea_provenance_display_preserves_evidence_state(monkeypatch, signals, level, confidence, expected):
    from scripts import idea_generator as ig
    monkeypatch.setattr(ig, '_case_backing', lambda mech: None)
    monkeypatch.setattr(ig, '_circle_backing', lambda circle: None)
    monkeypatch.setattr(ig, '_node_circles', lambda hotspot: None)
    body = ig._provenance('展览', 'neutral', 'eventify', 'premium', '都市职场', signals, 'consumer')
    assert expected in body['seed_signal']
    assert 'ZBC' not in body['seed_signal']
    assert body['evidence_level'] == level
    assert body['confidence'] == confidence
    assert body['counter_example_check'].startswith('pending')


def test_cli_help_uses_current_name():
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/idea_generator.py'), '--help'],
                            capture_output=True, text=True, check=False, timeout=10)
    assert result.returncode == 0, result.stderr
    assert 'LUMENIS 舆情关键词' in result.stdout
    assert 'ZBC' not in result.stdout


def test_current_p8_preserves_tts_and_authorized_import_boundary():
    row = next(line for line in PLAN.read_text().splitlines() if line.startswith('| P8 |'))
    for value in ('自有 TTS 运行时', '多音色', '外部依法获权音色/语音包', '导入与使用', '产品内不执行克隆', '用户选择才启用', 'AI 配音'):
        assert value in row, value
    assert '声音克隆仅本人授权' not in row


def test_sketch_voice_boundaries_agree_with_plan():
    text = SKETCH.read_text()
    assert '声音克隆只在本人明确授权后' not in text
    assert '声音克隆需本人授权' not in text
    assert text.count('外部依法获权音色/语音包') == 2
    assert text.count('产品内不执行克隆') == 2
    assert '没有麦克风授权可导入，不自动开麦' in text
    assert '转写/说话人和AI配音缺模型时保留导入稿/手工标注/剪辑混音' in text


def test_personal_capture_cancellation_does_not_remove_other_voice_work():
    text = PLAN.read_text()
    current = next(line for line in text.splitlines() if line.startswith('6. 已取消采集用户本人声音'))
    for value in ('制作本人声音包作为默认语音的专项待办', '播客', '语音交互', 'ASR/字幕', '配音', '用户上传授权声音', '默认范围'):
        assert value in current, value
    assert '产品内不执行克隆' in text


def test_cancelled_reference_note_is_inside_three_column_table():
    lines = PLAN.read_text().splitlines()
    start = lines.index('| 当前分类 | 名称与调整理由 | 原位置 |')
    table = []
    for line in lines[start:]:
        if not line.startswith('|'):
            break
        table.append(line)
    assert all(len(line.strip('|').split('|')) == 3 for line in table)
    row = next(line for line in table if '约315MB' in line)
    cells = row.strip('|').split('|')
    assert '后续研究已取消' in cells[1]
    assert '历史读取失败及未知范围保留' in cells[1]


def test_original_historical_claims_remain_preserved():
    text = PLAN.read_text()
    assert 'J25.11 / IC-176 本人授权后才可声音克隆，核声音来源与使用范围，无授权不执行。' in text
    assert '\n自有 TTS 运行时，多音色；声音克隆仅本人授权\n' in text
    assert '\n验收：用户选择才启用；标「AI 配音」；无授权不克隆\n' in text
    assert '原文字仅作为历史来源保全，不形成待办' in text


def test_current_voice_adjudications_do_not_require_owners_personal_voice():
    lines = PLAN.read_text().splitlines()
    voice_decisions = [line for line in lines if line.startswith('当前裁决：') and '声音当前为' in line]
    assert len(voice_decisions) == 2
    for line in voice_decisions:
        assert '外部依法获权音色/语音包' in line
        assert '用户上传授权声音' in line
        assert '不做产品内克隆' in line
        assert '外部本人制作' not in line


def test_python_sources_compile_without_writing_bytecode():
    for path in ('lumenis_agg_api.py', 'scripts/idea_generator.py'):
        compile((ROOT / path).read_bytes(), path, 'exec')
