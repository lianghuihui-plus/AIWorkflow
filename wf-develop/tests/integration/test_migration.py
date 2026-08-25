from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from support import run_cli

from integration.test_initialization_status import workspace_snapshot


def create_legacy_workspace(root: Path) -> Path:
    workspace = root / "legacy"
    workspace.mkdir()
    (workspace / "prd").mkdir()
    (workspace / "prd/requirements.md").write_text("# Legacy PRD\n", encoding="utf-8")
    (workspace / "output/specs").mkdir(parents=True)
    (workspace / "output/analysis.md").write_text("# Legacy analysis\n", encoding="utf-8")
    (workspace / "output/specs/T-001.md").write_text("# Legacy spec\n", encoding="utf-8")
    (workspace / "CONTEXT.md").write_text(
        """# 工作空间上下文 — Legacy Drafts

## 当前状态

- 阶段：design_ready
- 下一步：generate-specs

## 项目约束

- 平台：web
- 代码仓库：无
""",
        encoding="utf-8",
    )
    (workspace / "AGENT.md").write_text("# Legacy rules\n", encoding="utf-8")
    (workspace / "JOURNAL.md").write_text("# Legacy journal\n", encoding="utf-8")
    (workspace / "dashboard.html").write_text("legacy dashboard", encoding="utf-8")
    return workspace


class MigrationTests(unittest.TestCase):
    def test_preview_is_read_only_and_reports_unmapped_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = create_legacy_workspace(Path(directory))
            before = workspace_snapshot(workspace)

            completed = run_cli(["migrate", "--workspace", str(workspace)])

            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)["result"]
            self.assertEqual(result["status"], "preview")
            self.assertEqual(result["project"]["name"], "Legacy Drafts")
            self.assertEqual(result["project"]["platform"], "web")
            self.assertEqual(result["legacy_stage"], "design_ready")
            self.assertEqual(result["strategy"], "restart_from_analysis")
            self.assertIn("output/analysis.md", result["unmapped_outputs"])
            self.assertEqual(workspace_snapshot(workspace), before)

    def test_apply_creates_new_workspace_and_preserves_legacy_backup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = create_legacy_workspace(Path(directory))

            completed = run_cli(["migrate", "--workspace", str(workspace), "--apply"])

            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)["result"]
            self.assertEqual(result["status"], "migrated")
            self.assertEqual(result["next_action"], "analyze_requirements")
            self.assertTrue((workspace / ".aiwf/project.json").is_file())
            self.assertTrue((workspace / "artifacts/specs").is_dir())
            self.assertTrue((workspace / "dashboard.html").is_file())
            self.assertEqual(
                (workspace / "legacy-backup/output/analysis.md").read_text(encoding="utf-8"),
                "# Legacy analysis\n",
            )
            self.assertEqual(
                (workspace / "legacy-backup/CONTEXT.md").read_text(encoding="utf-8"),
                (workspace / "CONTEXT.md").read_text(encoding="utf-8"),
            )
            self.assertEqual(
                (workspace / "prd/requirements.md").read_text(encoding="utf-8"),
                "# Legacy PRD\n",
            )
            status = run_cli(["status", "--workspace", str(workspace)])
            self.assertEqual(status.returncode, 0, status.stderr)
            status_result = json.loads(status.stdout)["result"]
            self.assertEqual(status_result["state"]["current_stage"], "analysis")
            self.assertEqual(status_result["next_action"], "analyze_requirements")

            repeated = run_cli(["migrate", "--workspace", str(workspace), "--apply"])
            self.assertEqual(repeated.returncode, 5)
            self.assertEqual(json.loads(repeated.stderr)["error"]["code"], "already_migrated")


if __name__ == "__main__":
    unittest.main()
