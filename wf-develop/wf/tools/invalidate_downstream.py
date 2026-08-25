#!/usr/bin/env python3
"""Mark downstream AIWorkFlow artifacts stale after an upstream artifact changes."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


REVIEW_STATUS_RE = re.compile(r"^- 状态：(.+?)\s*$", re.MULTILINE)
REVIEWER_RE = re.compile(r"^- 审核人：.*?$", re.MULTILINE)
REVIEWED_AT_RE = re.compile(r"^- 审核时间：.*?$", re.MULTILINE)
REVISION_SOURCE_RE = re.compile(r"^- 修订来源：.*?$", re.MULTILINE)
TASK_RE = re.compile(r"^T-\d{3}\.md$")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def review_status(path: Path) -> str | None:
    if not path.exists():
        return None
    match = REVIEW_STATUS_RE.search(read_text(path))
    return match.group(1).strip() if match else None


def replace_or_insert_review_line(text: str, pattern: re.Pattern[str], line: str) -> str:
    if pattern.search(text):
        return pattern.sub(line, text, count=1)
    marker = "## 审核状态"
    index = text.find(marker)
    if index < 0:
        return text
    line_start = text.find("\n", index)
    if line_start < 0:
        return text + "\n\n" + line + "\n"
    return text[: line_start + 1] + line + "\n" + text[line_start + 1 :]


def mark_needs_update(path: Path, source: str) -> bool:
    if review_status(path) != "已确认":
        return False
    text = read_text(path)
    text = REVIEW_STATUS_RE.sub("- 状态：需更新", text, count=1)
    text = replace_or_insert_review_line(text, REVIEWER_RE, "- 审核人：")
    text = replace_or_insert_review_line(text, REVIEWED_AT_RE, "- 审核时间：")
    text = replace_or_insert_review_line(text, REVISION_SOURCE_RE, f"- 修订来源：上游产物已更新：{source}")
    write_text(path, text)
    return True


def downstream_paths(root: Path, changed: Path) -> list[Path]:
    try:
        parts = changed.relative_to(root).parts
    except ValueError:
        parts = changed.parts
    if len(parts) != 3 or parts[0] != "output" or not TASK_RE.fullmatch(parts[2]):
        return []
    task_id = parts[2].removesuffix(".md")
    if parts[1] == "specs":
        return [
            root / "output" / "reports" / f"{task_id}.md",
            root / "output" / "test-reports" / f"{task_id}.md",
        ]
    if parts[1] == "reports":
        return [root / "output" / "test-reports" / f"{task_id}.md"]
    return []


def invalidate(root: Path, changed_paths: list[Path]) -> list[Path]:
    updated: list[Path] = []
    for changed in changed_paths:
        changed_abs = changed if changed.is_absolute() else root / changed
        source = rel(changed_abs, root)
        for downstream in downstream_paths(root, changed_abs):
            if downstream.exists() and mark_needs_update(downstream, source):
                updated.append(downstream)
    return updated


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workspace")
    parser.add_argument("changed_artifacts", nargs="+")
    args = parser.parse_args()

    root = Path(args.workspace).resolve()
    changed_paths = [Path(item) for item in args.changed_artifacts]
    updated = invalidate(root, changed_paths)
    for path in updated:
        print(f"invalidated {rel(path, root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
