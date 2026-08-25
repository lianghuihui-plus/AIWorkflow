from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from support import SOURCE_ROOT, run_cli

from integration.test_analysis_cli import initialize_workspace


def run_success(arguments: list[str]) -> dict[str, object]:
    completed = run_cli(arguments)
    if completed.returncode != 0:
        raise AssertionError(completed.stderr)
    return json.loads(completed.stdout)["result"]


def write_outputs(
    workspace: Path,
    work: dict[str, object],
    *,
    markdown: str,
    result: dict[str, object],
) -> None:
    (workspace / str(work["draft_output"])).write_text(markdown, encoding="utf-8")
    (workspace / str(work["result_output"])).write_text(
        json.dumps(result, ensure_ascii=False),
        encoding="utf-8",
    )


def approve_analysis(workspace: Path) -> None:
    work = run_success(["prepare", "--workspace", str(workspace)])
    write_outputs(
        workspace,
        work,
        markdown="# Analysis\n\nUsers save drafts and resume editing.\n",
        result={
            "schema_version": 1,
            "stage": "analysis",
            "requirements": [
                {
                    "title": "Resume a draft",
                    "summary": "A signed-in user saves and resumes a draft.",
                    "sources": ["prd/requirements.md"],
                    "disposition": "proposed",
                }
            ],
            "memory_delta": [],
        },
    )
    run_success(["submit", "--workspace", str(workspace), "--work-id", str(work["work_id"])])
    run_success(
        [
            "review",
            "--workspace",
            str(workspace),
            "--artifact-id",
            "analysis",
            "--revision",
            "1",
            "--outcome",
            "approved",
        ]
    )


class DesignSpecificationCommandLineTests(unittest.TestCase):
    def test_design_and_multiple_specifications_advance_to_implementation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = initialize_workspace(Path(directory))
            approve_analysis(workspace)

            design = run_success(["prepare", "--workspace", str(workspace)])
            self.assertEqual(design["stage"], "design")
            self.assertEqual(design["active_item"], None)
            self.assertEqual(design["depends_on"], ["analysis@1"])
            self.assertIn("artifacts/analysis.md", design["inputs"])
            self.assertTrue((SOURCE_ROOT / "wf" / str(design["stage_guide"])).is_file())
            write_outputs(
                workspace,
                design,
                markdown="# Design\n\nPersist drafts, then expose resume behavior.\n",
                result={
                    "schema_version": 1,
                    "stage": "design",
                    "tasks": [
                        {
                            "key": "storage",
                            "title": "Persist drafts",
                            "requirements": ["REQ-001"],
                            "depends_on": [],
                        },
                        {
                            "key": "resume",
                            "title": "Resume draft editing",
                            "requirements": ["REQ-001"],
                            "depends_on": ["storage"],
                        },
                    ],
                    "memory_delta": [],
                },
            )
            run_success(
                ["submit", "--workspace", str(workspace), "--work-id", str(design["work_id"])]
            )
            run_success(
                [
                    "review",
                    "--workspace",
                    str(workspace),
                    "--artifact-id",
                    "design",
                    "--revision",
                    "1",
                    "--outcome",
                    "approved",
                ]
            )

            tasks = json.loads((workspace / ".aiwf/tasks.json").read_text(encoding="utf-8"))["items"]
            self.assertEqual([item["id"] for item in tasks], ["T-001", "T-002"])
            self.assertEqual(tasks[1]["depends_on"], ["T-001"])

            first_spec = run_success(["prepare", "--workspace", str(workspace)])
            self.assertEqual(first_spec["active_item"], "T-001")
            self.assertEqual(first_spec["depends_on"], ["analysis@1", "design@1"])
            self.assertIn("Persist drafts", first_spec["goal"])
            self.assertTrue((SOURCE_ROOT / "wf" / str(first_spec["stage_guide"])).is_file())
            write_outputs(
                workspace,
                first_spec,
                markdown="# T-001 Specification\n\nPersist draft content.\n",
                result={
                    "schema_version": 1,
                    "stage": "specification",
                    "task_id": "T-001",
                    "memory_delta": [],
                },
            )
            run_success(
                [
                    "submit",
                    "--workspace",
                    str(workspace),
                    "--work-id",
                    str(first_spec["work_id"]),
                ]
            )
            first_review = run_success(
                [
                    "review",
                    "--workspace",
                    str(workspace),
                    "--artifact-id",
                    "T-001-spec",
                    "--revision",
                    "1",
                    "--outcome",
                    "approved",
                ]
            )
            self.assertEqual(first_review["current_stage"], "specification")

            second_spec = run_success(["prepare", "--workspace", str(workspace)])
            self.assertEqual(second_spec["active_item"], "T-002")
            self.assertIn("Resume draft editing", second_spec["goal"])
            write_outputs(
                workspace,
                second_spec,
                markdown="# T-002 Specification\n\nResume the persisted draft.\n",
                result={
                    "schema_version": 1,
                    "stage": "specification",
                    "task_id": "T-002",
                    "memory_delta": [],
                },
            )
            run_success(
                [
                    "submit",
                    "--workspace",
                    str(workspace),
                    "--work-id",
                    str(second_spec["work_id"]),
                ]
            )
            final_review = run_success(
                [
                    "review",
                    "--workspace",
                    str(workspace),
                    "--artifact-id",
                    "T-002-spec",
                    "--revision",
                    "1",
                    "--outcome",
                    "approved",
                ]
            )
            self.assertEqual(final_review["current_stage"], "implementation")

            status = run_success(["status", "--workspace", str(workspace)])
            self.assertEqual(status["state"]["current_stage"], "implementation")
            self.assertEqual(status["next_action"], "implement_code")
            updated_tasks = json.loads(
                (workspace / ".aiwf/tasks.json").read_text(encoding="utf-8")
            )["items"]
            self.assertEqual([item["status"] for item in updated_tasks], ["in_progress", "in_progress"])

    def test_design_stage_rejects_an_explicit_task(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = initialize_workspace(Path(directory))
            approve_analysis(workspace)

            completed = run_cli(
                ["prepare", "--workspace", str(workspace), "--task-id", "T-999"]
            )

            self.assertEqual(completed.returncode, 4)
            self.assertEqual(
                json.loads(completed.stderr)["error"]["code"],
                "invalid_active_item",
            )


if __name__ == "__main__":
    unittest.main()
