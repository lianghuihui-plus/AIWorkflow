"""Workspace path and storage boundaries."""

from __future__ import annotations

from pathlib import Path

from .model import AIWorkflowError


def resolve_workspace(raw_path: str) -> Path:
    candidate = Path(raw_path).expanduser()
    try:
        workspace = candidate.resolve(strict=True)
    except OSError as error:
        raise AIWorkflowError(
            code="invalid_workspace",
            message="Workspace directory does not exist or cannot be resolved.",
            exit_code=2,
            details={"path": str(candidate)},
        ) from error

    if not workspace.is_dir():
        raise AIWorkflowError(
            code="invalid_workspace",
            message="Workspace path is not a directory.",
            exit_code=2,
            details={"path": str(workspace)},
        )

    return workspace
