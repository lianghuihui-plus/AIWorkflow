"""Workflow command dispatch boundary."""

from __future__ import annotations

from typing import NoReturn

from .model import AIWorkflowError, CommandRequest


def execute(request: CommandRequest) -> NoReturn:
    """Reject commands until their owning implementation phase is complete."""

    raise AIWorkflowError(
        code="command_not_implemented",
        message=f"Command '{request.command}' is not implemented in phase 1.",
        exit_code=3,
        details={
            "command": request.command,
            "phase": 1,
            "workspace": str(request.workspace),
        },
    )
