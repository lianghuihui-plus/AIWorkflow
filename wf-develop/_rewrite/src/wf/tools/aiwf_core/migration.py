"""Conservative one-time migration from the legacy Markdown workspace."""

from __future__ import annotations

import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

from .model import AIWorkflowError
from .storage import WorkspaceStore

LEGACY_FILES = (
    "README.md",
    "AGENT.md",
    "CONTEXT.md",
    "ISSUES.md",
    "REVISIONS.md",
    "JOURNAL.md",
    "CHANGELOG.md",
    "output",
    "dashboard.html",
)


def preview_migration(workspace: Path) -> dict[str, Any]:
    if (workspace / ".aiwf").exists():
        raise AIWorkflowError(
            code="already_migrated",
            message="Workspace already contains new AIWorkFlow data.",
            exit_code=5,
        )
    context_path = workspace / "CONTEXT.md"
    if not context_path.is_file():
        raise AIWorkflowError(
            code="legacy_workspace_not_found",
            message="Legacy CONTEXT.md was not found.",
            exit_code=4,
        )
    try:
        context = context_path.read_text(encoding="utf-8")
    except OSError as error:
        raise AIWorkflowError(
            code="legacy_workspace_unreadable",
            message="Legacy CONTEXT.md cannot be read.",
            exit_code=4,
        ) from error
    prd_root = workspace / "prd"
    prd_files = sorted(
        (path for path in prd_root.iterdir() if path.is_file()),
        key=lambda path: path.name.casefold(),
    ) if prd_root.is_dir() else []
    if not prd_files:
        raise AIWorkflowError(
            code="legacy_prd_missing",
            message="Legacy workspace has no direct PRD files.",
            exit_code=4,
        )
    name_match = re.search(r"^#\s+工作空间上下文\s*[—-]\s*(.+?)\s*$", context, re.MULTILINE)
    platform_match = re.search(r"^-\s*平台：(.+?)\s*$", context, re.MULTILINE)
    repository_match = re.search(r"^-\s*代码仓库：(.+?)\s*$", context, re.MULTILINE)
    stage_match = re.search(r"^-\s*阶段：(.+?)\s*$", context, re.MULTILINE)
    project_name = name_match.group(1).strip() if name_match else workspace.name
    platform = platform_match.group(1).strip() if platform_match else "unknown"
    repository = repository_match.group(1).strip() if repository_match else None
    if repository in {"", "无", "None", "null"}:
        repository = None
    backup_entries = [name for name in LEGACY_FILES if (workspace / name).exists()]
    output_files = []
    output_root = workspace / "output"
    if output_root.is_dir():
        output_files = [
            path.relative_to(workspace).as_posix()
            for path in sorted(output_root.rglob("*"))
            if path.is_file()
        ]
    return {
        "status": "preview",
        "workspace": str(workspace),
        "project": {
            "project_id": _slug(project_name),
            "name": project_name,
            "platform": platform,
            "code_repository": repository,
            "prd_files": [f"prd/{path.name}" for path in prd_files],
        },
        "legacy_stage": stage_match.group(1).strip() if stage_match else "unknown",
        "backup_entries": backup_entries,
        "unmapped_outputs": output_files,
        "strategy": "restart_from_analysis",
        "next_command": "migrate --apply",
    }


def apply_migration(store: WorkspaceStore) -> dict[str, Any]:
    preview = preview_migration(store.root)
    backup_target = store.root / "legacy-backup"
    temporary_backup = Path(tempfile.mkdtemp(prefix=".legacy-backup-", dir=store.root))
    installed = False
    try:
        for name in preview["backup_entries"]:
            source = store.root / name
            target = temporary_backup / name
            if source.is_dir():
                shutil.copytree(source, target)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
        store.bootstrap(
            preview["project"],
            allow_existing=True,
            reuse_existing_prd=True,
        )
        installed = True
        os.replace(temporary_backup, backup_target)
    except Exception:
        if installed:
            shutil.rmtree(store.data_root, ignore_errors=True)
            shutil.rmtree(store.root / "artifacts", ignore_errors=True)
        raise
    finally:
        shutil.rmtree(temporary_backup, ignore_errors=True)
    return {
        **preview,
        "status": "migrated",
        "backup": str(backup_target),
        "next_action": "analyze_requirements",
    }


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return normalized or "migrated-project"
