from __future__ import annotations

import json
import hashlib
import re
import unittest
from pathlib import Path

from support import DEVELOP_ROOT


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
            source = (DEVELOP_ROOT / sample["source"]).resolve()
            self.assertTrue(source.is_file(), source)
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), sample["sha256"])


if __name__ == "__main__":
    unittest.main()
