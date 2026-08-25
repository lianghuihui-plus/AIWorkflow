from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from support import run_cli


class CommandLineTests(unittest.TestCase):
    def test_help_lists_all_internal_commands(self) -> None:
        completed = run_cli(["--help"])

        self.assertEqual(completed.returncode, 0, completed.stderr)
        for command in (
            "init",
            "prepare",
            "submit",
            "review",
            "question",
            "decide",
            "status",
            "render",
            "migrate",
        ):
            self.assertIn(command, completed.stdout)

    def test_cli_does_not_depend_on_calling_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            completed = run_cli(["--version"], cwd=Path(directory))

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.strip(), "aiwf 0.3.0.dev1")

    def test_unimplemented_command_returns_structured_error(self) -> None:
        with tempfile.TemporaryDirectory() as workspace:
            completed = run_cli(["prepare", "--workspace", workspace])

        self.assertEqual(completed.returncode, 3)
        self.assertEqual(completed.stdout, "")
        self.assertNotIn("Traceback", completed.stderr)
        payload = json.loads(completed.stderr)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "command_not_implemented")
        self.assertEqual(payload["error"]["details"]["command"], "prepare")
        self.assertEqual(payload["error"]["details"]["workspace"], str(Path(workspace).resolve()))

    def test_missing_workspace_returns_structured_error(self) -> None:
        completed = run_cli(["status", "--workspace", "/path/that/does/not/exist"])

        self.assertEqual(completed.returncode, 2)
        payload = json.loads(completed.stderr)
        self.assertEqual(payload["error"]["code"], "invalid_workspace")

    def test_invalid_arguments_return_structured_error(self) -> None:
        completed = run_cli(["unknown-command"])

        self.assertEqual(completed.returncode, 2)
        payload = json.loads(completed.stderr)
        self.assertEqual(payload["error"]["code"], "invalid_arguments")


if __name__ == "__main__":
    unittest.main()
