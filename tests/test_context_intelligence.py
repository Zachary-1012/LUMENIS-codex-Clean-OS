import unittest

from context_intelligence import analyze_context, to_event_metadata


class ContextIntelligenceTests(unittest.TestCase):
    def test_comment_signals(self):
        result = analyze_context(
            {"note_id": "n1", "title": "新店开业", "content": "终于来了"},
            [
                {"content": "什么时候开门？"},
                {"content": "太贵了，投诉服务"},
                {"content": "推荐去看看"},
                {"content": "比隔壁品牌好"},
            ],
        )
        self.assertEqual(result["context"]["comment_count"], 4)
        self.assertEqual(result["comment_signals"]["question_count"], 1)
        self.assertEqual(result["comment_signals"]["complaint_count"], 1)
        self.assertEqual(result["comment_signals"]["recommendation_count"], 1)
        self.assertEqual(result["comment_signals"]["comparison_count"], 1)
        self.assertTrue(any(x["event_signal"] == "opening" for x in result["event_candidates"]))

    def test_event_output_is_non_authoritative(self):
        result = analyze_context({"note_id": "n2", "content": "活动开始"})
        self.assertTrue(result["event_candidates"])
        self.assertFalse(result["provenance"]["authoritative"])
        metadata = to_event_metadata(result)
        self.assertIn("context_intelligence", metadata)
        self.assertFalse(metadata["context_intelligence"]["provenance"]["authoritative"])

    def test_no_external_or_pii_enrichment(self):
        result = analyze_context({"note_id": "n3", "content": "普通内容"})
        self.assertFalse(result["provenance"]["external_call"])
        self.assertFalse(result["provenance"]["pii_enrichment"])

    def test_string_comments_supported(self):
        result = analyze_context({"note_id": "n4", "content": ""}, ["请问价格多少？"])
        self.assertEqual(result["comment_signals"]["comment_count"], 1)
        self.assertEqual(result["comment_signals"]["question_count"], 1)


if __name__ == "__main__":
    unittest.main()
