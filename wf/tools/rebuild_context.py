#!/usr/bin/env python3
"""Rebuild CONTEXT.md from AIWorkFlow artifact facts."""

from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path


REVIEW_RE = re.compile(r"^- 状态：(.+?)\s*$", re.MULTILINE)
TASK_RE = re.compile(r"\bT-\d{3}\b")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def section(text: str, heading: str) -> str:
    marker = f"## {heading}"
    start = text.find(marker)
    if start < 0:
        return ""
    rest = text[start + len(marker) :]
    next_match = re.search(r"\n## ", rest)
    if next_match:
        rest = rest[: next_match.start()]
    return rest.strip("\n")


def table_column_values(text: str, heading: str, column_index: int) -> list[str]:
    body = section(text, heading)
    values: list[str] = []
    for line in body.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) <= column_index:
            continue
        if cells[0] in {"ID", "任务", "#"} or set(cells[0]) <= {"-", " "}:
            continue
        values.append(cells[column_index])
    return values


def clean_table_path(value: str) -> str:
    value = value.strip()
    if value in {"", "—"}:
        return ""
    return value.strip("`").strip()


def title(text: str) -> str:
    first = text.splitlines()[0].strip() if text.splitlines() else "# 工作空间上下文 — 未命名"
    return first if first.startswith("# ") else "# 工作空间上下文 — 未命名"


def review_status(path: Path) -> str | None:
    if not path.exists():
        return None
    match = REVIEW_RE.search(read_text(path))
    return match.group(1).strip() if match else None


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def report_path(root: Path, task_id: str) -> Path:
    return root / "output" / "reports" / f"{task_id}.md"


def test_report_path(root: Path, task_id: str) -> Path:
    return root / "output" / "test-reports" / f"{task_id}.md"


def stage_artifacts(root: Path) -> list[Path]:
    output = root / "output"
    paths = [
        output / "analysis.md",
        output / "design.md",
    ]
    paths.extend(sorted((output / "specs").glob("T-*.md")))
    paths.extend(sorted((output / "reports").glob("T-*.md")))
    paths.extend(sorted((output / "test-reports").glob("T-*.md")))
    return [path for path in paths if path.exists()]


def pending_artifacts(root: Path) -> list[str]:
    pending: list[str] = []
    for path in stage_artifacts(root):
        status = review_status(path)
        if status in {"待审核", "需修改"}:
            pending.append(f"{rel(path, root)}（{status}）")
    return pending


def parse_design_tasks(root: Path) -> dict[str, str]:
    design = root / "output" / "design.md"
    if not design.exists():
        return {}
    tasks: dict[str, str] = {}
    for line in read_text(design).splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and TASK_RE.fullmatch(cells[0]):
            tasks[cells[0]] = cells[1]
    return tasks


def task_status(root: Path, task_id: str) -> tuple[bool, bool, bool]:
    output = root / "output"
    spec_confirmed = review_status(output / "specs" / f"{task_id}.md") == "已确认"
    report_confirmed = review_status(report_path(root, task_id)) == "已确认"
    test_confirmed = review_status(test_report_path(root, task_id)) == "已确认"
    return spec_confirmed, report_confirmed, test_confirmed


def test_files(root: Path, task_id: str) -> str:
    path = test_report_path(root, task_id)
    if not path.exists():
        return "—"
    files = []
    for value in table_column_values(read_text(path), "已生成单元测试", 3):
        cleaned = clean_table_path(value)
        if cleaned and cleaned not in files:
            files.append(cleaned)
    return "；".join(files) if files else "—"


def pending_stage(root: Path, pending: list[str]) -> str:
    if any(item.startswith("output/analysis.md") for item in pending):
        return "initialized"
    if any(item.startswith("output/design.md") for item in pending):
        return "requirements_analyzed"
    if any(item.startswith("output/specs/") for item in pending):
        return "design_ready"
    tasks = parse_design_tasks(root)
    any_confirmed_report = any(review_status(report_path(root, task)) == "已确认" for task in tasks)
    if any(item.startswith("output/test-reports/") for item in pending):
        all_reports = bool(tasks) and all(review_status(report_path(root, task)) == "已确认" for task in tasks)
        return "implementation_done" if all_reports else "implementation_in_progress"
    if any(item.startswith("output/reports/") for item in pending):
        return "implementation_in_progress" if any_confirmed_report else "specs_ready"
    return "initialized"


def active_state(root: Path) -> tuple[str, str]:
    output = root / "output"
    tasks = parse_design_tasks(root)
    if tasks:
        statuses = {task: task_status(root, task) for task in tasks}
        all_specs = all(value[0] for value in statuses.values())
        all_reports = all(value[1] for value in statuses.values())
        all_tests = all(value[2] for value in statuses.values())
        any_report = any(value[1] for value in statuses.values())
        any_untested = any(value[1] and not value[2] for value in statuses.values())
        if all_reports and all_tests:
            return "tests_done", "status"
        if all_reports and any_untested:
            return "implementation_done", "generate-tests"
        if any_report:
            return "implementation_in_progress", "implement-code"
        if all_specs:
            return "specs_ready", "implement-code"
    if review_status(output / "design.md") == "已确认":
        return "design_ready", "generate-specs"
    if review_status(output / "analysis.md") == "已确认":
        return "requirements_analyzed", "design-solution"
    return "initialized", "analyze-requirements"


def count_open_issues(root: Path) -> int:
    issues = root / "ISSUES.md"
    if not issues.exists():
        return 0
    text = read_text(issues)
    count = 0
    for block in re.split(r"\n### ", text):
        if re.search(r"\bQ-\d{3}\b", block) and "状态：已解决" not in block:
            count += 1
    return count


def requirement_summary(root: Path) -> str:
    analysis = root / "output" / "analysis.md"
    if analysis.exists():
        summary = section(read_text(analysis), "需求概要")
        if summary:
            return summary.strip()
    return "[执行 `wf` 后由需求分析能力填充]"


def render_context(root: Path) -> str:
    context_path = root / "CONTEXT.md"
    existing = read_text(context_path)
    pending = pending_artifacts(root)
    stage, next_step = (pending_stage(root, pending), "review-artifact") if pending else active_state(root)
    tasks = parse_design_tasks(root)
    issue_count = count_open_issues(root)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    project_constraints = section(existing, "项目约束") or "- 平台：HarmonyOS\n- 代码仓库：无"

    lines: list[str] = [
        title(existing),
        "",
        f"> 最后更新：{now}",
        "",
        "## 需求概要",
        "",
        requirement_summary(root),
        "",
        "## 当前状态",
        "",
        f"- 阶段：{stage}",
        f"- 待决策：{issue_count} 项（详见 ISSUES.md）",
        f"- 下一步：{next_step}",
        "- 待处理产物：",
    ]
    if pending:
        lines.extend(f"  - {item}" for item in pending)
    else:
        lines.append("  - 暂无")

    lines.append("- 规格：")
    if not tasks:
        lines.append("  - 暂无")
    else:
        for task_id, task_title in tasks.items():
            spec_confirmed, report_confirmed, test_confirmed = task_status(root, task_id)
            markers: list[str] = []
            if spec_confirmed:
                markers.append("✅ 已确认")
            if report_confirmed:
                markers.append("✅ 已实现")
            if test_confirmed:
                markers.append("✅ 已测试")
            suffix = f" {' '.join(markers)}" if markers else ""
            lines.append(f"  - {task_id} — {task_title}{suffix}")

    lines.extend([
        "",
        "## 项目约束",
        "",
        project_constraints.strip(),
        "",
        "## 代码产出",
        "",
        "| 任务 | 状态 |",
        "|---|---|",
    ])
    if not tasks:
        lines.append("| — | — |")
    else:
        for task_id in tasks:
            _, report_confirmed, _ = task_status(root, task_id)
            status = "✅ 已完成" if report_confirmed else "待开发"
            lines.append(f"| {task_id} | {status} |")

    lines.extend([
        "",
        "> 状态取值：`待开发` / `✅ 已完成`",
        "",
        "## 测试记录",
        "",
        "| 任务 | 测试文件 | 状态 |",
        "|---|---|---|",
    ])
    if not tasks:
        lines.append("| — | — | — |")
    else:
        for task_id in tasks:
            _, report_confirmed, test_confirmed = task_status(root, task_id)
            if test_confirmed:
                lines.append(f"| {task_id} | {test_files(root, task_id)} | ✅ 已完成 |")
            elif report_confirmed:
                lines.append(f"| {task_id} | — | 待测试 |")
            else:
                lines.append(f"| {task_id} | — | — |")

    lines.extend(["", "> 状态取值：`待测试` / `✅ 已完成`", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workspace", nargs="?", default=".")
    args = parser.parse_args()
    root = Path(args.workspace).resolve()
    context = root / "CONTEXT.md"
    if not context.exists():
        raise SystemExit(f"missing CONTEXT.md in {root}")
    write_text(context, render_context(root))
    print(f"rebuilt {context}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
