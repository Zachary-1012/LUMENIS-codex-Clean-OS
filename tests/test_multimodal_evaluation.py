import unittest

from lumenis.shared.evaluation.multimodal import MultimodalInput, assess_multimodal_result


class MultimodalEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.media = MultimodalInput(
            input_id="media-1",
            kind="image",
            source_ref="upload://brief-image-1",
            evidence_ref="ev-brief-image-1",
        )

    def test_complete_result_requires_evidence_grounding(self):
        assessment = assess_multimodal_result(
            self.media,
            analysis_state="complete",
            result_ref="analysis-1",
            grounded_in_evidence=False,
        )
        self.assertFalse(assessment["accepted"])
        self.assertIn("EVIDENCE_GROUNDING_REQUIRED", assessment["errors"])

    def test_complete_source_backed_result_is_accepted(self):
        assessment = assess_multimodal_result(
            self.media,
            analysis_state="complete",
            result_ref="analysis-1",
            grounded_in_evidence=True,
            human_reviewed=True,
        )
        self.assertTrue(assessment["accepted"])
        self.assertEqual(assessment["state"], "complete")

    def test_unavailable_is_explicit_and_not_success(self):
        assessment = assess_multimodal_result(self.media, analysis_state="unavailable")
        self.assertFalse(assessment["accepted"])
        self.assertEqual(assessment["state"], "unavailable")

    def test_missing_evidence_rejects_non_empty_model_result(self):
        media = MultimodalInput("media-2", "video", "upload://video", "")
        assessment = assess_multimodal_result(
            media,
            analysis_state="complete",
            result_ref="model-output-is-not-enough",
            grounded_in_evidence=True,
        )
        self.assertFalse(assessment["accepted"])
        self.assertIn("EVIDENCE_REF_REQUIRED", assessment["errors"])


if __name__ == "__main__":
    unittest.main()
