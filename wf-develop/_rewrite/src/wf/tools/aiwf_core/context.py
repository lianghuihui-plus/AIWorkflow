"""Task packet ownership boundary."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TaskPacketPaths:
    draft_output: Path
    result_output: Path
