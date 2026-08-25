from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


class AnalysisEvaluationSampleTests(unittest.TestCase):
    def test_two_real_prd_samples_are_selected_with_a_quality_rubric(self) -> None:
        registry_path = Path(__file__).with_name("analysis_samples.json")
        registry = json.loads(registry_path.read_text(encoding="utf-8"))

        self.assertEqual(registry["schema_version"], 1)
        self.assertGreaterEqual(len(registry["samples"]), 2)
        self.assertGreaterEqual(len(registry["rubric"]), 8)
        self.assertEqual(len({sample["id"] for sample in registry["samples"]}), 2)
        for sample in registry["samples"]:
            self.assertRegex(sample["sha256"], re.compile(r"^[0-9a-f]{64}$"))
            self.assertTrue(sample["source"].endswith(".md"))
            self.assertTrue(sample["selection_reason"].strip())


if __name__ == "__main__":
    unittest.main()
