"""Read-only code repository context captured when task work starts."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from .model import AIWorkflowError


def inspect_repository(raw_path: str | None) -> dict[str, Any]:
    if raw_path is None:
        raise AIWorkflowError(
            code="code_repository_required",
            message="Implementation and testing require a configured code repository.",
            exit_code=6,
        )
    repository = Path(raw_path)
    if not repository.is_dir():
        raise AIWorkflowError(
            code="code_repository_unavailable",
            message="Configured code repository is not accessible.",
            exit_code=6,
            details={"path": raw_path},
        )

    root = _git_output(repository, "rev-parse", "--show-toplevel")
    if root is None:
        return {
            "type": "directory",
            "path": str(repository.resolve()),
            "root": str(repository.resolve()),
            "head": None,
            "status_lines": [],
        }
    head = _git_output(repository, "rev-parse", "HEAD")
    status = _git_output(repository, "status", "--porcelain=v1", "--untracked-files=all")
    return {
        "type": "git",
        "path": str(repository.resolve()),
        "root": root,
        "head": head,
        "status_lines": status.splitlines() if status else [],
    }


def _git_output(repository: Path, *arguments: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repository), *arguments],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.rstrip("\r\n")
