import unittest

from collection_intelligence import completeness, quality_envelope


class CollectionIntelligenceTests(unittest.TestCase):
    def test_missing_is_not_empty(self):
        result = completeness({"note_id": "n1", "title": "测试"})
        self.assertEqual(result["states"]["content"], "UNKNOWN")

    def test_failed_collection_is_not_empty(self):
        result = completeness({"note_id": "n2", "collection_state": "BLOCKED"})
        self.assertEqual(result["states"]["content"], "BLOCKED")

    def test_not_applicable(self):
        result = completeness({"note_id": "n3", "cover_not_applicable": True})
        self.assertEqual(result["states"]["cover"], "NOT_APPLICABLE")

    def test_quality_envelope_keeps_context_non_authoritative(self):
        result = quality_envelope({
            "note_id": "n4",
            "title": "新店开业",
            "content": "活动开始",
            "comment_list": [{"content": "推荐去看看"}],
        })
        self.assertIn("collection_quality", result)
        self.assertIn("context_shadow", result)
        self.assertFalse(result["provenance"]["derived_context_authoritative"])


if __name__ == "__main__":
    unittest.main()
