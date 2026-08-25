from __future__ import annotations

import unittest
from pathlib import Path


class ScenarioFixtureTests(unittest.TestCase):
    def test_minimal_scenario_has_prd_and_code_repository(self) -> None:
        fixture_root = Path(__file__).parent / "fixtures"

        self.assertTrue((fixture_root / "minimal-prd" / "requirements.md").is_file())
        self.assertTrue((fixture_root / "minimal-repo" / "src" / "app.txt").is_file())


if __name__ == "__main__":
    unittest.main()
