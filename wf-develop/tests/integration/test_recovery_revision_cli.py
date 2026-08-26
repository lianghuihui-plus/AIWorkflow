from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from support import run_cli

from aiwf_core.model import now_iso
from aiwf_core.storage import InjectedTransactionFailure, json_bytes
from aiwf_core.workflow import WorkflowEngine
from integration.test_analysis_cli import initialize_workspace
from integration.test_design_specification_cli import approve_analysis, run_success


class RecoveryRevisionCommandLineTests(unittest.TestCase):
    def test_recover_command_resolves_an_incomplete_transaction(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = initialize_workspace(Path(directory))
            engine = WorkflowEngine(workspace)
            original_state = engine.store.read_json("state.json")
            changed_state = {**original_state, "updated_at": now_iso()}
            with engine.store.lock(exclusive=True):
                engine.store.inject_failure_after(1)
                with self.assertRaises(InjectedTransactionFailure):
                    engine.store.commit_locked(
                        {".aiwf/state.json": json_bytes(changed_state)},
                        event_type="test_change",
                        event_data={},
                        command_key="test:recover-cli",
                        request_digest="recover-cli",
                    )

            status = run_success(["status", "--workspace", str(workspace)])
            self.assertEqual(status["status"], "needs_recovery")
            recovered = run_success(["recover", "--workspace", str(workspace)])
            self.assertEqual(recovered["status"], "recovered")
            self.assertTrue(recovered["recovered"])
            self.assertEqual(
                run_success(["status", "--workspace", str(workspace)])["status"],
                "ok",
            )

    def test_revise_command_resumes_an_approved_revision(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = initialize_workspace(Path(directory))
            approve_analysis(workspace)

            revised = run_success(
                [
                    "revise",
                    "--workspace",
                    str(workspace),
                    "--artifact-id",
                    "analysis",
                    "--revision",
                    "1",
                    "--feedback",
                    "Clarify offline behavior.",
                ]
            )
            resumed = run_success(["prepare", "--workspace", str(workspace)])
            self.assertEqual(resumed["work_id"], revised["work_id"])
            self.assertEqual(resumed["stage"], "analysis")
            self.assertEqual(resumed["feedback"], "Clarify offline behavior.")
            editable_result = json.loads(
                (workspace / resumed["result_output"]).read_text(encoding="utf-8")
            )
            self.assertNotIn("artifact_id", editable_result)
            self.assertLessEqual(
                set(editable_result),
                set(resumed["result_schema"]["properties"]),
            )

    def test_revise_requires_confirmation_and_archives_superseded_work(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = initialize_workspace(Path(directory))
            approve_analysis(workspace)
            active = run_success(["prepare", "--workspace", str(workspace)])
            (workspace / active["draft_output"]).write_text(
                "# Unfinished design\n", encoding="utf-8"
            )

            arguments = [
                "revise",
                "--workspace",
                str(workspace),
                "--artifact-id",
                "analysis",
                "--revision",
                "1",
                "--feedback",
                "Change the approved requirement.",
            ]
            rejected = run_cli(arguments)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertEqual(json.loads(rejected.stderr)["error"]["code"], "active_work_conflict")

            revised = run_success([*arguments, "--supersede-active-work"])
            archive = workspace / ".aiwf/history/abandoned" / active["work_id"]
            self.assertEqual(
                (archive / "artifact.md").read_text(encoding="utf-8"),
                "# Unfinished design\n",
            )
            self.assertEqual(
                json.loads((archive / "work.json").read_text(encoding="utf-8"))["status"],
                "abandoned",
            )
            self.assertNotEqual(revised["work_id"], active["work_id"])

    def test_memory_projection_drift_is_reported_and_rebuilt_by_prepare(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = initialize_workspace(Path(directory))
            memory_path = workspace / ".aiwf/memory.md"
            memory_path.write_text("tampered\n", encoding="utf-8")

            status = run_success(["status", "--workspace", str(workspace)])
            self.assertEqual(status["status"], "issues_found")
            self.assertIn("generated_view_drift", {item["type"] for item in status["issues"]})

            run_success(["prepare", "--workspace", str(workspace)])
            self.assertIn("Confirmed Decisions", memory_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
