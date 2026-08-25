from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from support import run_cli

from integration.test_analysis_cli import initialize_workspace


def structured_snapshot(workspace: Path) -> dict[str, bytes]:
    return {
        path.relative_to(workspace).as_posix(): path.read_bytes()
        for path in sorted((workspace / ".aiwf").rglob("*"))
        if path.is_file()
    }


class DashboardTests(unittest.TestCase):
    def test_dashboard_is_generated_and_escapes_artifact_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = initialize_workspace(Path(directory))
            dashboard = workspace / "dashboard.html"
            self.assertTrue(dashboard.is_file())

            prepared = run_cli(["prepare", "--workspace", str(workspace)])
            self.assertEqual(prepared.returncode, 0, prepared.stderr)
            work = json.loads(prepared.stdout)["result"]
            (workspace / work["draft_output"]).write_text(
                "# Analysis\n\n<script>alert('unsafe')</script>\n",
                encoding="utf-8",
            )
            (workspace / work["result_output"]).write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "stage": "analysis",
                        "requirements": [
                            {
                                "title": "Draft",
                                "summary": "Save a draft.",
                                "sources": ["prd/requirements.md"],
                                "disposition": "proposed",
                            }
                        ],
                        "memory_delta": [],
                    }
                ),
                encoding="utf-8",
            )
            submitted = run_cli(
                ["submit", "--workspace", str(workspace), "--work-id", work["work_id"]]
            )
            self.assertEqual(submitted.returncode, 0, submitted.stderr)

            content = dashboard.read_text(encoding="utf-8")
            self.assertIn("需求追踪", content)
            self.assertIn("任务追踪", content)
            self.assertIn("产物预览", content)
            self.assertIn("&lt;script&gt;alert", content)
            self.assertNotIn("<script>alert", content)
            self.assertNotIn("https://", content)
            self.assertNotIn("http://", content)

    def test_explicit_render_does_not_change_structured_workspace_data(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = initialize_workspace(Path(directory))
            before = structured_snapshot(workspace)

            rendered = run_cli(["render", "--workspace", str(workspace)])

            self.assertEqual(rendered.returncode, 0, rendered.stderr)
            result = json.loads(rendered.stdout)["result"]
            self.assertEqual(result["status"], "rendered")
            self.assertGreater(result["bytes"], 1000)
            self.assertEqual(structured_snapshot(workspace), before)

    def test_render_failure_does_not_roll_back_successful_submission(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = initialize_workspace(Path(directory))
            prepared = run_cli(["prepare", "--workspace", str(workspace)])
            work = json.loads(prepared.stdout)["result"]
            (workspace / work["draft_output"]).write_text("# Analysis\n", encoding="utf-8")
            (workspace / work["result_output"]).write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "stage": "analysis",
                        "requirements": [],
                        "memory_delta": [],
                    }
                ),
                encoding="utf-8",
            )
            dashboard = workspace / "dashboard.html"
            dashboard.unlink()
            dashboard.mkdir()

            submitted = run_cli(
                ["submit", "--workspace", str(workspace), "--work-id", work["work_id"]]
            )

            self.assertEqual(submitted.returncode, 0, submitted.stderr)
            result = json.loads(submitted.stdout)["result"]
            self.assertEqual(result["artifact_id"], "analysis")
            self.assertEqual(result["warnings"][0]["type"], "dashboard_render_failed")
            state = json.loads((workspace / ".aiwf/state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["mode"], "review")
            self.assertTrue((workspace / "artifacts/analysis.md").is_file())


if __name__ == "__main__":
    unittest.main()
