from __future__ import annotations

import unittest

import support  # noqa: F401

from aiwf_core.artifacts import reconcile_tasks, validate_result_manifest
from aiwf_core.model import AIWorkflowError, SCHEMA_VERSION


class ArtifactResultTests(unittest.TestCase):
    def test_task_dependencies_use_submission_keys_then_normalize_to_ids(self) -> None:
        result = {
            "schema_version": SCHEMA_VERSION,
            "stage": "design",
            "memory_delta": [],
            "tasks": [
                {
                    "key": "base",
                    "title": "Base task",
                    "requirements": ["REQ-001"],
                    "depends_on": [],
                },
                {
                    "key": "dependent",
                    "title": "Dependent task",
                    "requirements": ["REQ-001"],
                    "depends_on": ["base"],
                },
            ],
        }
        validate_result_manifest("design", result, active_item=None)

        tasks, normalized = reconcile_tasks(
            {"schema_version": SCHEMA_VERSION, "items": []},
            {
                "schema_version": SCHEMA_VERSION,
                "items": [
                    {
                        "id": "REQ-001",
                        "title": "Requirement",
                        "summary": "Summary",
                        "disposition": "accepted",
                        "sources": ["prd/requirements.md"],
                        "origin_revision": 1,
                    }
                ],
            },
            result,
            revision=1,
        )

        self.assertEqual([item["id"] for item in tasks["items"]], ["T-001", "T-002"])
        self.assertEqual(normalized["tasks"][1]["depends_on"], ["T-001"])

    def test_task_dependency_cycle_is_rejected(self) -> None:
        result = {
            "schema_version": SCHEMA_VERSION,
            "stage": "design",
            "memory_delta": [],
            "tasks": [
                {
                    "key": "a",
                    "title": "A",
                    "requirements": ["REQ-001"],
                    "depends_on": ["b"],
                },
                {
                    "key": "b",
                    "title": "B",
                    "requirements": ["REQ-001"],
                    "depends_on": ["a"],
                },
            ],
        }

        with self.assertRaises(AIWorkflowError) as raised:
            reconcile_tasks(
                {"schema_version": SCHEMA_VERSION, "items": []},
                {
                    "schema_version": SCHEMA_VERSION,
                    "items": [
                        {
                            "id": "REQ-001",
                            "title": "Requirement",
                            "summary": "Summary",
                            "disposition": "accepted",
                            "sources": ["prd/requirements.md"],
                            "origin_revision": 1,
                        }
                    ],
                },
                result,
                revision=1,
            )

        self.assertEqual(raised.exception.code, "task_dependency_cycle")


if __name__ == "__main__":
    unittest.main()
