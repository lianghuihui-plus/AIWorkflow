from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from support import SOURCE_ROOT

from integration.test_analysis_cli import initialize_workspace
from integration.test_design_specification_cli import approve_analysis, run_success, write_outputs


def initialize_git_repository(root: Path) -> tuple[Path, str]:
    repository = root / "repository"
    (repository / "src").mkdir(parents=True)
    (repository / "src/app.txt").write_text("initial\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    subprocess.run(["git", "-C", str(repository), "config", "user.name", "AIWorkFlow Test"], check=True)
    subprocess.run(
        ["git", "-C", str(repository), "config", "user.email", "aiworkflow@example.invalid"],
        check=True,
    )
    subprocess.run(["git", "-C", str(repository), "add", "src/app.txt"], check=True)
    subprocess.run(["git", "-C", str(repository), "commit", "-qm", "initial"], check=True)
    head = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return repository, head


def advance_single_task_to_implementation(workspace: Path) -> None:
    approve_analysis(workspace)
    design = run_success(["prepare", "--workspace", str(workspace)])
    write_outputs(
        workspace,
        design,
        markdown="# Design\n\nPersist drafts in the editor repository.\n",
        result={
            "schema_version": 1,
            "stage": "design",
            "tasks": [
                {
                    "key": "draft-storage",
                    "title": "Persist and resume drafts",
                    "requirements": ["REQ-001"],
                    "depends_on": [],
                }
            ],
            "memory_delta": [],
        },
    )
    run_success(["submit", "--workspace", str(workspace), "--work-id", str(design["work_id"])])
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
    specification = run_success(["prepare", "--workspace", str(workspace)])
    write_outputs(
        workspace,
        specification,
        markdown="# T-001 Specification\n\nPersist and restore draft content.\n",
        result={
            "schema_version": 1,
            "stage": "specification",
            "task_id": "T-001",
            "memory_delta": [],
        },
    )
    run_success(
        ["submit", "--workspace", str(workspace), "--work-id", str(specification["work_id"])]
    )
    run_success(
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


class ImplementationTestingCommandLineTests(unittest.TestCase):
    def test_implementation_and_testing_capture_repository_and_complete_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository, baseline = initialize_git_repository(root)
            (repository / "existing.txt").write_text("user change\n", encoding="utf-8")
            workspace = initialize_workspace(root, repository=repository)
            advance_single_task_to_implementation(workspace)

            implementation = run_success(["prepare", "--workspace", str(workspace)])
            self.assertEqual(implementation["stage"], "implementation")
            self.assertEqual(implementation["active_item"], "T-001")
            self.assertEqual(implementation["depends_on"], ["T-001-spec@1"])
            self.assertEqual(implementation["facts"]["task"]["id"], "T-001")
            self.assertEqual(
                [item["id"] for item in implementation["facts"]["requirements"]],
                ["REQ-001"],
            )
            repository_context = implementation["repository_context"]
            self.assertEqual(repository_context["type"], "git")
            self.assertEqual(repository_context["head"], baseline)
            self.assertIn("?? existing.txt", repository_context["status_lines"])
            self.assertTrue((SOURCE_ROOT / "wf" / str(implementation["stage_guide"])).is_file())
            self.assertNotIn(".aiwf/tasks.json", implementation["inputs"])

            (repository / "src/app.txt").write_text("draft persistence implemented\n", encoding="utf-8")
            write_outputs(
                workspace,
                implementation,
                markdown="# Implementation\n\nAdded draft persistence.\n",
                result={
                    "schema_version": 1,
                    "stage": "implementation",
                    "task_id": "T-001",
                    "changed_files": ["src/app.txt"],
                    "validation_summary": "Targeted check passed.",
                    "memory_delta": [],
                },
            )
            run_success(
                [
                    "submit",
                    "--workspace",
                    str(workspace),
                    "--work-id",
                    str(implementation["work_id"]),
                ]
            )
            run_success(
                [
                    "review",
                    "--workspace",
                    str(workspace),
                    "--artifact-id",
                    "T-001-implementation",
                    "--revision",
                    "1",
                    "--outcome",
                    "approved",
                ]
            )

            testing = run_success(["prepare", "--workspace", str(workspace)])
            self.assertEqual(testing["stage"], "testing")
            self.assertEqual(testing["active_item"], "T-001")
            self.assertEqual(testing["depends_on"], ["T-001-implementation@1"])
            self.assertIn(" M src/app.txt", testing["repository_context"]["status_lines"])
            self.assertIn("?? existing.txt", testing["repository_context"]["status_lines"])
            self.assertTrue((SOURCE_ROOT / "wf" / str(testing["stage_guide"])).is_file())

            (repository / "tests").mkdir()
            (repository / "tests/test_drafts.txt").write_text("draft test\n", encoding="utf-8")
            write_outputs(
                workspace,
                testing,
                markdown="# Tests\n\nDraft persistence behavior passed.\n",
                result={
                    "schema_version": 1,
                    "stage": "testing",
                    "task_id": "T-001",
                    "test_files": ["tests/test_drafts.txt"],
                    "execution": {
                        "command": "project-test",
                        "exit_code": 0,
                        "summary": "Passed",
                    },
                    "uncovered": [],
                    "memory_delta": [],
                },
            )
            run_success(
                ["submit", "--workspace", str(workspace), "--work-id", str(testing["work_id"])]
            )
            final = run_success(
                [
                    "review",
                    "--workspace",
                    str(workspace),
                    "--artifact-id",
                    "T-001-test",
                    "--revision",
                    "1",
                    "--outcome",
                    "approved",
                ]
            )
            self.assertEqual(final["current_stage"], "completed")
            status = run_success(["status", "--workspace", str(workspace)])
            self.assertEqual(status["next_action"], "completed")
            self.assertEqual(status["state"]["current_stage"], "completed")


if __name__ == "__main__":
    unittest.main()
