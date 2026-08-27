from __future__ import annotations

import sys
import unittest

from support import TOOLS_ROOT

sys.path.insert(0, str(TOOLS_ROOT))

from aiwf_core.model import (  # noqa: E402
    COMMAND_SPECS,
    MODES,
    SCHEMA_VERSION,
    STAGES,
    TASK_STATUSES,
)


class WorkflowModelTests(unittest.TestCase):
    def test_command_surface_matches_approved_plan(self) -> None:
        self.assertEqual(
            [spec.name for spec in COMMAND_SPECS],
            [
                "init",
                "recover",
                "prepare",
                "submit",
                "review",
                "revise",
                "resolve-drift",
                "question",
                "decide",
                "route-decision",
                "route-upstream",
                "status",
                "render",
            ],
        )

    def test_stage_and_mode_vocabulary_is_stable(self) -> None:
        self.assertEqual(SCHEMA_VERSION, 8)
        self.assertNotIn("deferred", TASK_STATUSES)
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
        self.assertEqual(MODES, ("ready", "working", "review", "blocked", "decision"))


if __name__ == "__main__":
    unittest.main()
