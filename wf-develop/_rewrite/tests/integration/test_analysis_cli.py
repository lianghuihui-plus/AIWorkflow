from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from support import SOURCE_ROOT, run_cli


def initialize_workspace(root: Path) -> Path:
    workspace = root / "workspace"
    workspace.mkdir()
    prd = root / "requirements.md"
    prd.write_text(
        "# Drafts\n\nSigned-in users can save a draft and continue later.\n",
        encoding="utf-8",
    )
    completed = run_cli(
        [
            "init",
            "--workspace",
            str(workspace),
            "--name",
            "Draft Editor",
            "--platform",
            "web",
            "--prd",
            str(prd),
        ]
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stderr)
    return workspace


class AnalysisCommandLineTests(unittest.TestCase):
    def test_prepare_submit_and_review_analysis_across_processes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = initialize_workspace(Path(directory))

            prepared = run_cli(
                [
                    "prepare",
                    "--workspace",
                    str(workspace),
                    "--instruction",
                    "重点识别离线编辑约束",
                ]
            )
            self.assertEqual(prepared.returncode, 0, prepared.stderr)
            work = json.loads(prepared.stdout)["result"]
            repeated = run_cli(["prepare", "--workspace", str(workspace)])
            self.assertEqual(json.loads(repeated.stdout)["result"], work)

            self.assertEqual(work["stage"], "analysis")
            self.assertEqual(work["stage_guide"], "references/stages/analysis.md")
            self.assertIn("prd/requirements.md", work["inputs"])
            self.assertIn(".aiwf/project.json", work["inputs"])
            self.assertIn(".aiwf/requirements.json", work["inputs"])
            self.assertIn("重点识别离线编辑约束", work["goal"])
            guide = SOURCE_ROOT / "wf" / work["stage_guide"]
            self.assertTrue(guide.is_file())
            serialized = json.dumps(work, ensure_ascii=False)
            for framework_term in ("事务清单", "事件追加", "状态迁移", "dashboard"):
                self.assertNotIn(framework_term, serialized)

            (workspace / work["draft_output"]).write_text(
                "# 需求分析\n\n用户需要保存草稿并在稍后继续编辑。\n",
                encoding="utf-8",
            )
            result = {
                "schema_version": 1,
                "stage": "analysis",
                "requirements": [
                    {
                        "title": "保存并继续草稿",
                        "summary": "登录用户可以保存草稿并稍后继续编辑。",
                        "sources": ["prd/requirements.md"],
                        "disposition": "proposed",
                    }
                ],
                "memory_delta": [
                    {
                        "operation": "add",
                        "type": "business_requirement",
                        "content": "登录用户可以保存草稿并稍后继续编辑。",
                    }
                ],
            }
            (workspace / work["result_output"]).write_text(
                json.dumps(result, ensure_ascii=False),
                encoding="utf-8",
            )

            submitted = run_cli(
                ["submit", "--workspace", str(workspace), "--work-id", work["work_id"]]
            )
            self.assertEqual(submitted.returncode, 0, submitted.stderr)
            submission = json.loads(submitted.stdout)["result"]
            self.assertEqual((submission["artifact_id"], submission["revision"]), ("analysis", 1))

            status = json.loads(
                run_cli(["status", "--workspace", str(workspace)]).stdout
            )["result"]
            self.assertEqual(status["next_action"], "review")
            self.assertEqual(status["pending_reviews"][0]["id"], "analysis")

            reviewed = run_cli(
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
            self.assertEqual(reviewed.returncode, 0, reviewed.stderr)
            review = json.loads(reviewed.stdout)["result"]
            self.assertEqual(review["current_stage"], "design")
            memory = json.loads((workspace / ".aiwf/memory.json").read_text(encoding="utf-8"))
            self.assertEqual(memory["items"][0]["id"], "M-001")
            self.assertIn("保存草稿", (workspace / ".aiwf/memory.md").read_text(encoding="utf-8"))

            next_work = run_cli(["prepare", "--workspace", str(workspace)])
            self.assertEqual(next_work.returncode, 0, next_work.stderr)
            self.assertEqual(json.loads(next_work.stdout)["result"]["stage"], "design")

    def test_blocking_question_and_decision_resume_with_successor_work(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = initialize_workspace(Path(directory))
            prepared = run_cli(["prepare", "--workspace", str(workspace)])
            work = json.loads(prepared.stdout)["result"]
            questions = [
                {
                    "question": "草稿是否需要跨设备同步？",
                    "reason": "这会改变数据存储与一致性设计。",
                    "recommendation": "首版仅支持同设备。",
                    "impact": ["analysis", "design"],
                }
            ]

            opened = run_cli(
                [
                    "question",
                    "--workspace",
                    str(workspace),
                    "--work-id",
                    work["work_id"],
                    "--items-json",
                    json.dumps(questions, ensure_ascii=False),
                ]
            )
            self.assertEqual(opened.returncode, 0, opened.stderr)
            question_id = json.loads(opened.stdout)["result"]["question_ids"][0]

            decided = run_cli(
                [
                    "decide",
                    "--workspace",
                    str(workspace),
                    "--question-id",
                    question_id,
                    "--decision",
                    "首版只支持同设备保存，不做跨设备同步。",
                ]
            )
            self.assertEqual(decided.returncode, 0, decided.stderr)
            successor = json.loads(decided.stdout)["result"]["successor_work_id"]
            resumed = json.loads(
                run_cli(["prepare", "--workspace", str(workspace)]).stdout
            )["result"]
            self.assertEqual(resumed["work_id"], successor)
            self.assertIn(
                "首版只支持同设备保存",
                (workspace / ".aiwf/memory.md").read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
