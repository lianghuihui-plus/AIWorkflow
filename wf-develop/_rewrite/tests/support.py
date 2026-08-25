"""Shared paths and subprocess helpers for rewrite tests."""

from __future__ import annotations

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
