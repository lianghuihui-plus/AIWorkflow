from __future__ import annotations

import unittest

import support  # noqa: F401

from aiwf_core.model import AIWorkflowError, SCHEMA_VERSION, next_id, validate_document


class SchemaTests(unittest.TestCase):
    def test_state_requires_active_work_while_working(self) -> None:
        state = {
            "schema_version": SCHEMA_VERSION,
            "current_stage": "analysis",
            "mode": "working",
            "active_item": None,
            "active_work": None,
            "active_work_sha256": None,
            "pending_reviews": [],
            "blocking_questions": [],
            "updated_at": "2026-08-25T10:00:00+08:00",
        }

        with self.assertRaises(AIWorkflowError) as raised:
            validate_document("state.json", state)

        self.assertEqual(raised.exception.code, "invalid_schema")

    def test_ids_are_monotonic_and_never_reuse_gaps(self) -> None:
        self.assertEqual(next_id("requirement", ["REQ-001", "REQ-003"]), "REQ-004")
        self.assertEqual(next_id("work", ["W-000009"]), "W-000010")


if __name__ == "__main__":
    unittest.main()
