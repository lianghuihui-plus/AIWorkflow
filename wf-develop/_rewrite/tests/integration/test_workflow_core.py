from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from support import bootstrap_engine, write_work_outputs

from aiwf_core.model import AIWorkflowError, SCHEMA_VERSION
from aiwf_core.workflow import WorkflowEngine


def analysis_result(*, requirement_id: str | None = None, summary: str = "Save a draft") -> dict[str, object]:
    requirement: dict[str, object] = {
        "title": "Save drafts",
        "summary": summary,
        "sources": ["prd/requirements.md#save-drafts"],
    }
    if requirement_id is not None:
        requirement["id"] = requirement_id
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": "analysis",
        "requirements": [requirement],
        "memory_delta": [
            {
                "operation": "add",
                "type": "Project Goal",
                "content": summary,
                "target_id": None,
            }
        ],
    }


def design_result() -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": "design",
        "tasks": [
            {
                "key": "draft-storage",
                "title": "Implement draft storage",
                "requirements": ["REQ-001"],
                "depends_on": [],
            }
        ],
        "memory_delta": [],
    }


def task_result(stage: str) -> dict[str, object]:
    common: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "stage": stage,
        "task_id": "T-001",
        "memory_delta": [],
    }
    if stage == "implementation":
        common.update(
            {
                "changed_files": ["src/drafts.txt"],
                "validation_summary": "Checked locally",
            }
        )
    elif stage == "testing":
        common.update(
            {
                "test_files": ["tests/test_drafts.txt"],
                "execution": {"command": "test", "exit_code": 0, "summary": "Passed"},
                "uncovered": [],
            }
        )
    return common


class WorkflowCoreTests(unittest.TestCase):
    def test_new_engine_instance_resumes_the_same_active_work(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            engine = bootstrap_engine(Path(directory))
            prepared = engine.prepare_work(goal="Analyze requirements")

            resumed = WorkflowEngine(Path(directory)).prepare_work(goal="Different caller text")

            self.assertEqual(resumed["work_id"], prepared["work_id"])
            self.assertEqual(resumed["goal"], "Analyze requirements")

    def test_active_work_metadata_drift_blocks_resume(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            engine = bootstrap_engine(Path(directory))
            prepared = engine.prepare_work(goal="Analyze requirements")
            work_path = engine.store.safe_path(
                f".aiwf/work/{prepared['work_id']}/work.json"
            )
            work = json.loads(work_path.read_text(encoding="utf-8"))
            work["artifact"]["output"] = "artifacts/other.md"
            work_path.write_text(json.dumps(work), encoding="utf-8")

            with self.assertRaises(AIWorkflowError) as raised:
                engine.prepare_work(goal="Resume")

            self.assertEqual(raised.exception.code, "work_drift")

    def test_analysis_submit_and_review_are_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            engine = bootstrap_engine(Path(directory))
            work = engine.prepare_work(goal="Analyze requirements")
            write_work_outputs(
                engine,
                work,
                markdown="# Analysis\n\nUsers can save drafts.\n",
                result=analysis_result(),
            )

            submitted = engine.submit_work(work["work_id"])
            repeated_submit = engine.submit_work(work["work_id"])

            self.assertEqual(submitted, repeated_submit)
            self.assertTrue((Path(directory) / "artifacts/analysis.md").is_file())
            self.assertFalse((Path(directory) / ".aiwf/work" / work["work_id"]).exists())
            self.assertEqual(engine.store.read_json("state.json")["mode"], "review")
            self.assertEqual(
                engine.store.read_json("requirements.json")["items"][0]["disposition"],
                "proposed",
            )

            approved = engine.review_artifact("analysis", 1, outcome="approved")
            repeated_approval = engine.review_artifact("analysis", 1, outcome="approved")

            self.assertEqual(approved, repeated_approval)
            state = engine.store.read_json("state.json")
            self.assertEqual((state["current_stage"], state["mode"]), ("design", "ready"))
            self.assertEqual(
                engine.store.read_json("requirements.json")["items"][0]["disposition"],
                "accepted",
            )
            memory = engine.store.read_json("memory.json")["items"]
            self.assertEqual(memory[0]["id"], "M-001")
            self.assertIn("Save a draft", (Path(directory) / ".aiwf/memory.md").read_text())

    def test_artifact_drift_blocks_review_and_is_reported_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            engine = bootstrap_engine(Path(directory))
            work = engine.prepare_work(goal="Analyze requirements")
            write_work_outputs(
                engine,
                work,
                markdown="# Analysis\n",
                result=analysis_result(),
            )
            engine.submit_work(work["work_id"])
            artifact_path = Path(directory) / "artifacts/analysis.md"
            artifact_path.write_text("# Changed outside workflow\n", encoding="utf-8")

            with self.assertRaises(AIWorkflowError) as raised:
                engine.review_artifact("analysis", 1, outcome="approved")

            self.assertEqual(raised.exception.code, "artifact_drift")
            self.assertEqual(engine.inspect()["status"], "artifact_drift")
            self.assertEqual(engine.store.read_json("state.json")["mode"], "review")

    def test_change_request_creates_a_seeded_successor_revision(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            engine = bootstrap_engine(Path(directory))
            first_work = engine.prepare_work(goal="Analyze requirements")
            write_work_outputs(
                engine,
                first_work,
                markdown="# Analysis v1\n",
                result=analysis_result(),
            )
            engine.submit_work(first_work["work_id"])

            change = engine.review_artifact(
                "analysis",
                1,
                outcome="changes_requested",
                feedback="Clarify offline behavior.",
            )
            successor = engine.prepare_work(goal="Ignored while resuming")
            self.assertEqual(successor["work_id"], change["work_id"])
            self.assertEqual(successor["feedback"], "Clarify offline behavior.")
            self.assertIn("Analysis v1", engine.store.safe_path(successor["draft_output"]).read_text())
            with self.assertRaises(AIWorkflowError) as raised:
                engine.review_artifact(
                    "analysis",
                    1,
                    outcome="changes_requested",
                    feedback="Different feedback.",
                )
            self.assertEqual(raised.exception.code, "idempotency_conflict")

            write_work_outputs(
                engine,
                successor,
                markdown="# Analysis v2\n\nOffline behavior clarified.\n",
                result=analysis_result(summary="Save a draft offline"),
            )
            submitted = engine.submit_work(successor["work_id"])

            self.assertEqual(submitted["revision"], 2)
            history = Path(directory) / ".aiwf/history/analysis/1.md"
            self.assertEqual(history.read_text(encoding="utf-8"), "# Analysis v1\n")

    def test_blocking_questions_resume_with_a_successor_work(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            engine = bootstrap_engine(Path(directory))
            work = engine.prepare_work(goal="Analyze requirements")
            engine.store.safe_path(work["draft_output"]).write_text(
                "# Partial analysis\n",
                encoding="utf-8",
            )
            opened = engine.open_questions(
                work["work_id"],
                [
                    {
                        "question": "Keep drafts offline?",
                        "reason": "Storage behavior is ambiguous.",
                        "recommendation": "Keep a local copy.",
                        "impact": ["analysis", "design"],
                    },
                    {
                        "question": "Expire drafts?",
                        "reason": "Retention is not specified.",
                        "recommendation": "Do not expire automatically.",
                        "impact": ["analysis"],
                    },
                ],
            )
            self.assertEqual(engine.open_questions(work["work_id"], [
                {
                    "question": "Keep drafts offline?",
                    "reason": "Storage behavior is ambiguous.",
                    "recommendation": "Keep a local copy.",
                    "impact": ["analysis", "design"],
                },
                {
                    "question": "Expire drafts?",
                    "reason": "Retention is not specified.",
                    "recommendation": "Do not expire automatically.",
                    "impact": ["analysis"],
                },
            ]), opened)

            first = engine.decide(opened["question_ids"][0], "Keep drafts offline.")
            self.assertIsNone(first["successor_work_id"])
            self.assertEqual(engine.store.read_json("state.json")["mode"], "blocked")
            second = engine.decide(opened["question_ids"][1], "Drafts do not expire.")
            self.assertIsNotNone(second["successor_work_id"])
            resumed = engine.prepare_work(goal="Ignored while resuming")
            self.assertEqual(resumed["work_id"], second["successor_work_id"])
            self.assertEqual(
                engine.store.safe_path(resumed["draft_output"]).read_text(encoding="utf-8"),
                "# Partial analysis\n",
            )
            memory_markdown = (Path(directory) / ".aiwf/memory.md").read_text(encoding="utf-8")
            self.assertIn("Keep drafts offline.", memory_markdown)
            self.assertIn("Drafts do not expire.", memory_markdown)

    def test_upstream_revision_recursively_invalidates_all_downstream_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            engine = bootstrap_engine(Path(directory))

            analysis = engine.prepare_work(goal="Analyze")
            write_work_outputs(engine, analysis, markdown="# Analysis\n", result=analysis_result())
            engine.submit_work(analysis["work_id"])
            engine.review_artifact("analysis", 1, outcome="approved")

            design = engine.prepare_work(goal="Design", depends_on=["analysis@1"])
            write_work_outputs(engine, design, markdown="# Design\n", result=design_result())
            engine.submit_work(design["work_id"])
            engine.review_artifact("design", 1, outcome="approved")

            specification = engine.prepare_work(
                goal="Specify T-001",
                active_item="T-001",
                depends_on=["analysis@1", "design@1"],
            )
            write_work_outputs(
                engine,
                specification,
                markdown="# Specification\n",
                result=task_result("specification"),
            )
            engine.submit_work(specification["work_id"])
            engine.review_artifact("T-001-spec", 1, outcome="approved")

            implementation = engine.prepare_work(
                goal="Implement T-001",
                active_item="T-001",
                depends_on=["T-001-spec@1"],
            )
            write_work_outputs(
                engine,
                implementation,
                markdown="# Implementation\n",
                result=task_result("implementation"),
            )
            engine.submit_work(implementation["work_id"])
            engine.review_artifact("T-001-implementation", 1, outcome="approved")

            testing = engine.prepare_work(
                goal="Test T-001",
                active_item="T-001",
                depends_on=["T-001-implementation@1"],
            )
            write_work_outputs(
                engine,
                testing,
                markdown="# Tests\n",
                result=task_result("testing"),
            )
            engine.submit_work(testing["work_id"])
            engine.review_artifact("T-001-test", 1, outcome="approved")
            self.assertEqual(engine.store.read_json("state.json")["current_stage"], "completed")

            revision_request = engine.request_revision(
                "analysis",
                feedback="Clarify cross-device behavior.",
            )
            revision_work = engine.prepare_work(goal="Ignored while resuming")
            self.assertEqual(revision_work["work_id"], revision_request["work_id"])
            write_work_outputs(
                engine,
                revision_work,
                markdown="# Analysis\n",
                result=analysis_result(
                    requirement_id="REQ-001",
                    summary="Save and resume drafts across devices",
                ),
            )
            submitted = engine.submit_work(revision_work["work_id"])

            self.assertEqual(
                set(submitted["invalidated"]),
                {"design", "T-001-spec", "T-001-implementation", "T-001-test"},
            )
            artifacts = {
                item["id"]: item for item in engine.store.read_json("artifacts.json")["items"]
            }
            for artifact_id in submitted["invalidated"]:
                self.assertEqual(artifacts[artifact_id]["status"], "stale")
            self.assertEqual(engine.store.read_json("tasks.json")["items"][0]["status"], "stale")

    def test_result_manifest_drift_also_blocks_review(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            engine = bootstrap_engine(Path(directory))
            work = engine.prepare_work(goal="Analyze requirements")
            write_work_outputs(
                engine,
                work,
                markdown="# Analysis\n",
                result=analysis_result(),
            )
            submitted = engine.submit_work(work["work_id"])
            artifact = next(
                item
                for item in engine.store.read_json("artifacts.json")["items"]
                if item["id"] == submitted["artifact_id"]
            )
            result_path = engine.store.safe_path(artifact["result_path"])
            result = json.loads(result_path.read_text(encoding="utf-8"))
            result["requirements"][0]["summary"] = "Changed outside the workflow"
            result_path.write_text(json.dumps(result), encoding="utf-8")

            with self.assertRaises(AIWorkflowError) as raised:
                engine.review_artifact("analysis", 1, outcome="approved")

            self.assertEqual(raised.exception.code, "artifact_drift")


if __name__ == "__main__":
    unittest.main()
