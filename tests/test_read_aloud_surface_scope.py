"""Read-aloud document scope: current iOS delivery and retained research."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / '00-GOVERNANCE/LOOP-PLAN-20261014/product-plan-full.md'
SKETCH = ROOT / '00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md'


def test_read_aloud_mobile_acceptance_matches_current_ios_scope():
    text = PLAN.read_text(encoding='utf-8')
    section = text.split('#### 本地朗读的停止与声音资格', 1)[1].split('\n#### ', 1)[0]
    assert '移动核iOS精确locale和音频焦点' in section
    assert '移动核Android/iOS' not in section
    for retained in ('Web保cancel后paused真实态', 'PC分别核Windows/macOS原生回执',
                     '键盘/触控/读屏等价', '真实离线/停止/释放/恢复验收仍待执行'):
        assert retained in section


def test_android_linux_references_have_explicit_non_delivery_context():
    lines = PLAN.read_text(encoding='utf-8').splitlines()
    mentions = [line for line in lines if re.search(r'android|linux|安卓', line, re.IGNORECASE)]
    # Additional historical/platform research references are permitted.
    assert any('原生 Android/Linux不在当前交付要求' in line
               and 'Linux服务/CI及各OS浏览器和窄屏Web仍在范围' in line for line in mentions)
    assert any(line.startswith('| N2 |') and 'Linux/Android原生客户端不在当前scope' in line
               and 'Linux服务器/CI与浏览器覆盖保持' in line for line in mentions)


def test_historical_android_tts_research_is_preserved_without_acceptance_claim():
    lines = PLAN.read_text(encoding='utf-8').splitlines()
    research = next(line for line in lines if line.startswith('本地朗读补研核固定main与2248相同的7份实现'))
    assert '[Android TTS](https://developer.android.com/reference/android/speech/tts/TextToSpeech)' in research
    assert '23自写断言分TTS8/归因15' in research
    assert '不能算实机声音、客户订单或产品四端通过' in research
