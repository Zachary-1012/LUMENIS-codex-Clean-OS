"""Actual optional eSpeak NG speech; absent engines skip, never fake success."""
import hashlib,os,wave,io
import pytest
from lumenis.shared.content_creation.offline_formant_speech import synthesize_formant_speech
from lumenis.shared.content_creation.video_editing import VideoEditingError

@pytest.fixture
def installed():
    if not os.environ.get('LUMENIS_ESPEAK_BINARY'):pytest.skip('explicit isolated eSpeak runtime not configured')

@pytest.mark.parametrize('language,text,voice',[('zh-CN','这是明确标记的机器合成测试。','cmn'),('ko','이 음성은 합성 테스트입니다.','ko'),('en','This is a clearly synthetic test.','en-us')])
def test_real_full_multilingual_formant_pcm(installed,language,text,voice):
    result=synthesize_formant_speech(text,language=language)
    report=result['report'];data=result['files']['speech.wav']
    assert report['voice']==voice and report['language']==language and report['synthesis_method']=='formant_non_neural'
    assert report['audio']['full_pcm_comparison']=='passed' and report['audio']['duration_sec']>0
    with wave.open(io.BytesIO(data)) as wav:assert wav.getnframes()==report['audio']['decoded_samples_per_channel']
    assert report['outputs']['speech.wav']['sha256']==hashlib.sha256(data).hexdigest()
    assert report['source']['text']==text and not report['audio_trimmed'] and not report['voice_cloned']
    assert 'NOT_EVALUATED' in report['naturalness']

@pytest.mark.parametrize('kwargs',[{'language':'xx'},{'language':'zh-CN','voice':'../../bad'},{'language':'ko','voice':'cmn'},{'language':[]}])
def test_invalid_language_or_voice_before_runtime(kwargs):
    with pytest.raises(VideoEditingError):synthesize_formant_speech('test',**kwargs)

@pytest.mark.parametrize('text',['',' ','<speak>text</speak>','[[phonemes]]','a\x00b','a'*4001,None])
def test_literal_input_rejects_markup_and_controls(text):
    with pytest.raises(VideoEditingError,match='TEXT_INVALID'):synthesize_formant_speech(text,language='zh-CN')


def test_cancel_does_not_generate(installed):
    def stop():raise RuntimeError('cancelled')
    with pytest.raises(RuntimeError,match='cancelled'):synthesize_formant_speech('合成测试',language='zh-CN',check_cancel=stop)


def test_missing_engine_is_explicit(monkeypatch):
    monkeypatch.setenv('LUMENIS_ESPEAK_BINARY','/missing/espeak-ng')
    with pytest.raises(VideoEditingError,match='ESPEAK_RUNTIME_UNAVAILABLE'):synthesize_formant_speech('合成测试',language='zh-CN')


def test_cancel_reaps_actual_started_engine(installed, monkeypatch):
    from pathlib import Path
    from lumenis.shared.content_creation import rendering
    original = rendering.subprocess.Popen
    started = []
    def observe(command, *args, **kwargs):
        process = original(command, *args, **kwargs)
        if '-w' in command and 'speech.wav' in command:
            started.append((process, Path(kwargs['cwd'])))
        return process
    monkeypatch.setattr(rendering.subprocess, 'Popen', observe)
    def cancel_after_start():
        if started:
            raise RuntimeError('cancelled after real engine start')
    with pytest.raises(RuntimeError, match='after real engine start'):
        synthesize_formant_speech('这是一段取消测试。' * 300, language='zh-CN', check_cancel=cancel_after_start)
    assert len(started) == 1
    process, directory = started[0]
    assert process.poll() is not None
    assert not directory.exists()
    assert synthesize_formant_speech('恢复测试。', language='zh-CN')['report']['audio']['full_decode'] == 'passed'
