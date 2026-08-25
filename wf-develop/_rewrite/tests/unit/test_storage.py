from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from support import TOOLS_ROOT

sys.path.insert(0, str(TOOLS_ROOT))

from aiwf_core.model import AIWorkflowError  # noqa: E402
from aiwf_core.storage import resolve_workspace  # noqa: E402


class WorkspaceResolutionTests(unittest.TestCase):
    def test_resolves_existing_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(resolve_workspace(directory), Path(directory).resolve())

    def test_rejects_missing_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing"
            with self.assertRaises(AIWorkflowError) as raised:
                resolve_workspace(str(missing))

        self.assertEqual(raised.exception.code, "invalid_workspace")
        self.assertEqual(raised.exception.exit_code, 2)
        self.assertEqual(str(raised.exception), raised.exception.message)


if __name__ == "__main__":
    unittest.main()
