"""Shared paths and subprocess helpers for rewrite tests."""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

REWRITE_ROOT = Path(__file__).resolve().parents[1]
DEVELOP_ROOT = REWRITE_ROOT.parent
REPOSITORY_ROOT = DEVELOP_ROOT.parent
SOURCE_ROOT = REWRITE_ROOT / "src"
TOOLS_ROOT = SOURCE_ROOT / "wf" / "tools"
CLI_PATH = TOOLS_ROOT / "aiwf.py"
sys.path.insert(0, str(TOOLS_ROOT))

from aiwf_core.workflow import WorkflowEngine  # noqa: E402


def run_cli(
    arguments: Sequence[str],
    *,
    cwd: Path = REWRITE_ROOT,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI_PATH), *arguments],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )


def bootstrap_engine(workspace: Path) -> WorkflowEngine:
    engine = WorkflowEngine(workspace)
    engine.bootstrap(
        {
            "project_id": "test-project",
            "name": "Test Project",
            "platform": "test",
            "code_repository": None,
            "prd_files": [],
        }
    )
    return engine


def write_work_outputs(
    engine: WorkflowEngine,
    work: dict[str, object],
    *,
    markdown: str,
    result: dict[str, object],
) -> None:
    engine.store.safe_path(str(work["draft_output"])).write_text(markdown, encoding="utf-8")
    engine.store.safe_path(str(work["result_output"])).write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
