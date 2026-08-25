"""Shared command and workflow model definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
STAGES = (
    "analysis",
    "design",
    "specification",
    "implementation",
    "testing",
    "completed",
)
MODES = ("ready", "working", "review", "blocked")


@dataclass(frozen=True)
class CommandSpec:
    name: str
    help: str


COMMAND_SPECS = (
    CommandSpec("init", "Initialize a workspace."),
    CommandSpec("prepare", "Prepare or resume the current work item."),
    CommandSpec("submit", "Submit a semantic artifact and result manifest."),
    CommandSpec("review", "Approve an artifact or request changes."),
    CommandSpec("question", "Record blocking questions for the current work."),
    CommandSpec("decide", "Record a user decision and resume work."),
    CommandSpec("status", "Read workspace status without modifying it."),
    CommandSpec("render", "Render the static workspace dashboard."),
    CommandSpec("migrate", "Migrate a legacy workspace after confirmation."),
)


@dataclass(frozen=True)
class CommandRequest:
    command: str
    workspace: Path


@dataclass
class AIWorkflowError(Exception):
    code: str
    message: str
    exit_code: int
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        super().__init__(self.message)

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
        }
        if self.details:
            payload["details"] = self.details
        return payload
