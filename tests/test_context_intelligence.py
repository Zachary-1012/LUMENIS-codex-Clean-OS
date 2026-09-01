from context_intelligence import analyze_context, to_event_metadata


def test_comment_context_surfaces_event_signal():
    note = {
        "note_id": "demo-1",
        "title": "新店终于开业了",
        "content": "今天去体验，整体不错，但是排队很久。",
        "comment_list": [
            {"content": "什么时候正式开业？"},
            {"content": "价格有点贵，但还是想去。"},
        ],
    }
    result = analyze_context(note)
    assert result["schema_version"] == "context-intelligence.v1"
    assert result["context"]["comment_count"] == 2
    assert any(x["event_signal"] == "opening" for x in result["event_candidates"])
    assert result["comment_signals"]["question_count"] == 1
    assert result["provenance"]["external_call"] is False


def test_context_does_not_make_legal_or_bullying_judgement():
    result = analyze_context({"note_id": "demo-2", "title": "投诉", "content": "服务态度不好"}, [])
    assert "legal_violation" not in result
    assert "cyberbullying" not in result
    assert result["provenance"]["pii_enrichment"] is False


def test_event_metadata_is_non_authoritative():
    result = analyze_context({"note_id": "demo-3", "title": "新品发布", "content": "今天上新"}, [])
    metadata = to_event_metadata(result)
    assert "context_intelligence" in metadata
    assert metadata["context_intelligence"]["event_candidates"]
