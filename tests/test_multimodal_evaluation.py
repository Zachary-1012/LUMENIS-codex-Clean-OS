import unittest
import hashlib

from lumenis.shared.evaluation.multimodal import MultimodalInput, assess_multimodal_result


class MultimodalEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.payload = b"actual image bytes supplied to the analyzer"
        self.media = MultimodalInput.from_bytes(
            input_id="media-1",
            kind="image",
            source_ref="upload://brief-image-1",
            evidence_ref="ev-brief-image-1",
            payload=self.payload,
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
            analysis_execution_ref="run-1",
            analysis_input_sha256=hashlib.sha256(self.payload).hexdigest(),
        )
        self.assertTrue(assessment["accepted"])
        self.assertEqual(assessment["state"], "complete")

    def test_unavailable_is_explicit_and_not_success(self):
        assessment = assess_multimodal_result(self.media, analysis_state="unavailable")
        self.assertFalse(assessment["accepted"])
        self.assertEqual(assessment["state"], "unavailable")

    def test_missing_evidence_rejects_non_empty_model_result(self):
        media = MultimodalInput.from_bytes(
            input_id="media-2", kind="video", source_ref="upload://video",
            evidence_ref="", payload=b"video bytes",
        )
        assessment = assess_multimodal_result(
            media,
            analysis_state="complete",
            result_ref="model-output-is-not-enough",
            grounded_in_evidence=True,
            analysis_execution_ref="run-2",
            analysis_input_sha256=media.content_sha256,
        )
        self.assertFalse(assessment["accepted"])
        self.assertIn("EVIDENCE_REF_REQUIRED", assessment["errors"])

    def test_reference_only_input_cannot_claim_complete_analysis(self):
        media = MultimodalInput("media-3", "image", "upload://only-ref", "ev-3")
        assessment = assess_multimodal_result(
            media, analysis_state="complete", result_ref="output", grounded_in_evidence=True,
            analysis_execution_ref="run-3",
        )
        self.assertFalse(assessment["accepted"])
        self.assertIn("INPUT_CONTENT_HASH_REQUIRED", assessment["errors"])
        self.assertIn("ANALYSIS_INPUT_HASH_REQUIRED", assessment["errors"])


if __name__ == "__main__":
    unittest.main()
