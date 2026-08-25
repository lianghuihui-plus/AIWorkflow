from __future__ import annotations

import sys
import unittest

from support import TOOLS_ROOT

sys.path.insert(0, str(TOOLS_ROOT))

from aiwf_core.model import COMMAND_SPECS, MODES, SCHEMA_VERSION, STAGES  # noqa: E402


class WorkflowModelTests(unittest.TestCase):
    def test_command_surface_matches_approved_plan(self) -> None:
        self.assertEqual(
            [spec.name for spec in COMMAND_SPECS],
            [
                "init",
                "prepare",
                "submit",
                "review",
                "question",
                "decide",
                "status",
                "render",
                "migrate",
            ],
        )

    def test_stage_and_mode_vocabulary_is_stable(self) -> None:
        self.assertEqual(SCHEMA_VERSION, 1)
        self.assertEqual(
            STAGES,
            (
                "analysis",
                "design",
                "specification",
                "implementation",
                "testing",
                "completed",
            ),
        )
        self.assertEqual(MODES, ("ready", "working", "review", "blocked"))


if __name__ == "__main__":
    unittest.main()
