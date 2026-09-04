import pytest

from video_intelligence import VideoEvidence, VideoIntelligenceEngine


def test_passive_engine_normalizes_provider_output():
    def provider(evidence):
        assert evidence.source == "browser_rendered"
        return {
            "entities": ["Guangzhou Taikoo Hui"],
            "topics": ["event"],
            "sentiment": "positive",
            "risk_level": "low",
            "marketing_signals": ["brand_exposure"],
            "confidence": 1.2,
        }

    evidence = VideoEvidence(
        evidence_id="ev-1",
        note_id="note-1",
        frame_refs=["frame-1"],
        ocr_text="广州太古汇",
        asr_text="周年活动",
    )
    result = VideoIntelligenceEngine(provider, "test", "v1").analyze(evidence)

    assert result.note_id == "note-1"
    assert result.transcript == "周年活动"
    assert result.on_screen_text == "广州太古汇"
    assert result.confidence == 1.0
    assert result.provider == "test"


def test_rejects_non_rendered_sources():
    evidence = VideoEvidence("ev-1", "note-1", source="remote_download")
    with pytest.raises(ValueError, match="browser-rendered"):
        VideoIntelligenceEngine().analyze(evidence)


def test_ai_failure_does_not_need_platform_access():
    evidence = VideoEvidence("ev-1", "note-1")
    result = VideoIntelligenceEngine().analyze(evidence)
    assert result.sentiment == "unknown"
    assert result.risk_level == "unknown"
