#!/usr/bin/env python3
"""AIWorkFlow workspace validator.

This script performs deterministic structure checks only. It does not judge
business quality and never modifies files.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


VALID_STAGES = {
    "initialized",
    "requirements_analyzed",
    "design_ready",
    "specs_ready",
    "implementation_in_progress",
    "implementation_done",
    "tests_done",
    "blocked_by_decision",
    "blocked_by_missing_input",
    "blocked_by_inconsistent_state",
}

VALID_NEXT = {
    "analyze-requirements",
    "design-solution",
    "generate-specs",
    "implement-code",
    "generate-tests",
    "review-artifact",
    "status",
    "resolve-decision",
    "fix-workspace",
}

VALID_REVIEW = {"待审核", "需修改", "已确认"}
REVIEW_RE = re.compile(r"^- 状态：(.+?)\s*$", re.MULTILINE)
TASK_RE = re.compile(r"\bT-\d{3}\b")
Q_RE = re.compile(r"\bQ-\d{3}\b")
R_RE = re.compile(r"\bR-\d{3}\b")


@dataclass
class Issue:
    level: str
    type: str
    file: str
    message: str
    suggestion: str = ""


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


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


def parse_context_field(text: str, name: str) -> str:
    current = section(text, "当前状态")
    match = re.search(rf"^- {re.escape(name)}：(.+?)\s*$", current, re.MULTILINE)
    return match.group(1).strip() if match else ""


def parse_project_field(text: str, name: str) -> str:
    project = section(text, "项目约束")
    match = re.search(rf"^- {re.escape(name)}：(.+?)\s*$", project, re.MULTILINE)
    return match.group(1).strip() if match else ""


def parse_list_block(text: str, label: str) -> list[str]:
    current = section(text, "当前状态")
    lines = current.splitlines()
    items: list[str] = []
    in_block = False
    for line in lines:
        if line.startswith(f"- {label}："):
            in_block = True
            continue
        if in_block:
            if line.startswith("- ") and not line.startswith("  - "):
                break
            if line.startswith("  - "):
                items.append(line[4:].strip())
    return items


def parse_table_tasks(text: str, heading: str) -> dict[str, str]:
    body = section(text, heading)
    result: dict[str, str] = {}
    for line in body.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not cells or not TASK_RE.fullmatch(cells[0]):
            continue
        result[cells[0]] = " | ".join(cells[1:])
    return result


def review_status(path: Path) -> str | None:
    if not path.exists():
        return None
    match = REVIEW_RE.search(read_text(path))
    return match.group(1).strip() if match else None


def stage_artifacts(root: Path) -> list[Path]:
    output = root / "output"
    paths = [
        output / "analysis.md",
        output / "design.md",
    ]
    paths.extend(sorted((output / "specs").glob("T-*.md")))
    paths.extend(sorted(output.glob("report-T-*.md")))
    paths.extend(sorted(output.glob("test-report-T-*.md")))
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


def duplicate_ids(path: Path, pattern: re.Pattern[str]) -> list[str]:
    if not path.exists():
        return []
    ids = pattern.findall(read_text(path))
    seen: set[str] = set()
    duplicates: set[str] = set()
    for item in ids:
        if item in seen:
            duplicates.add(item)
        seen.add(item)
    return sorted(duplicates)


def add(issue_list: list[Issue], level: str, typ: str, file: str, message: str, suggestion: str = "") -> None:
    issue_list.append(Issue(level, typ, file, message, suggestion))


def issue_blocks(root: Path) -> list[tuple[str, str]]:
    path = root / "ISSUES.md"
    if not path.exists():
        return []
    text = read_text(path)
    matches = list(re.finditer(r"(?m)^### (Q-\d{3})\b.*$", text))
    blocks: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        blocks.append((match.group(1), text[match.start() : end]))
    return blocks


def issue_field(block: str, label: str) -> str:
    match = re.search(rf"^[ \t]*[-*]?[ \t]*\*\*{re.escape(label)}：\*\*[ \t]*(.*?)[ \t]*$", block, re.MULTILINE)
    return match.group(1).strip() if match else ""


def issue_resolved(block: str) -> bool:
    return "状态：已解决" in block


def validate(root: Path, action: str | None = None, target: str | None = None) -> dict:
    issues: list[Issue] = []
    required = ["CONTEXT.md", "AGENT.md", "ISSUES.md", "REVISIONS.md", "JOURNAL.md", "CHANGELOG.md"]
    for item in required:
        if not (root / item).exists():
            add(issues, "fail", "missing_workspace_file", item, f"缺少 {item}", "补齐工作空间文件后重新执行 wf")
    for item in ["prd", "output"]:
        if not (root / item).is_dir():
            add(issues, "fail", "missing_workspace_dir", item, f"缺少 {item}/", "补齐工作空间目录后重新执行 wf")

    context_path = root / "CONTEXT.md"
    context = read_text(context_path) if context_path.exists() else ""
    stage = parse_context_field(context, "阶段")
    next_step = parse_context_field(context, "下一步")
    if context:
        if not stage:
            add(issues, "fail", "missing_stage", "CONTEXT.md", "CONTEXT.md 缺少阶段字段")
        elif stage not in VALID_STAGES:
            add(issues, "fail", "invalid_stage", "CONTEXT.md", f"阶段取值无效：{stage}")
        if not next_step:
            add(issues, "fail", "missing_next_step", "CONTEXT.md", "CONTEXT.md 缺少下一步字段")
        elif next_step not in VALID_NEXT:
            add(issues, "fail", "invalid_next_step", "CONTEXT.md", f"下一步取值无效：{next_step}")
        pending_in_context = parse_list_block(context, "待处理产物")
        if not pending_in_context:
            add(issues, "fail", "missing_pending_artifacts_field", "CONTEXT.md", "CONTEXT.md 缺少待处理产物字段")
        else:
            actual_pending = pending_artifacts(root)
            normalized_context = [] if pending_in_context == ["暂无"] else pending_in_context
            if sorted(normalized_context) != sorted(actual_pending):
                add(
                    issues,
                    "fail",
                    "pending_artifacts_mismatch",
                    "CONTEXT.md",
                    "CONTEXT.md 待处理产物列表与产物审核状态不一致",
                    "执行 rebuild-context 重建状态快照",
                )
            pending_allowed_next = {"review-artifact"}
            if stage in {"blocked_by_decision", "blocked_by_missing_input", "blocked_by_inconsistent_state"}:
                pending_allowed_next.update({"resolve-decision", "fix-workspace"})
            if actual_pending and next_step not in pending_allowed_next:
                add(
                    issues,
                    "fail",
                    "pending_requires_review_artifact",
                    "CONTEXT.md",
                    "存在待处理产物时下一步必须为 review-artifact",
                    "执行 rebuild-context 重建状态快照",
                )

    for artifact in stage_artifacts(root):
        status = review_status(artifact)
        file = rel(artifact, root)
        if status is None:
            add(issues, "warn", "missing_review_status", file, f"{file} 缺少审核状态")
        elif status not in VALID_REVIEW:
            add(issues, "fail", "invalid_review_status", file, f"{file} 审核状态无效：{status}")

    for dup in duplicate_ids(root / "ISSUES.md", Q_RE):
        add(issues, "fail", "duplicate_issue_id", "ISSUES.md", f"问题编号重复：{dup}")
    for dup in duplicate_ids(root / "REVISIONS.md", R_RE):
        add(issues, "fail", "duplicate_revision_id", "REVISIONS.md", f"修订编号重复：{dup}")

    tasks = parse_design_tasks(root)
    for task_id in tasks:
        spec = root / "output" / "specs" / f"{task_id}.md"
        if not spec.exists():
            add(issues, "warn", "missing_spec", rel(spec, root), f"{task_id} 缺少规格文件")

    context_done = parse_table_tasks(context, "代码产出")
    for task_id, value in context_done.items():
        if "已完成" in value:
            report = root / "output" / f"report-{task_id}.md"
            if review_status(report) != "已确认":
                add(
                    issues,
                    "fail",
                    "missing_confirmed_report",
                    rel(report, root),
                    f"{task_id} 标记已完成，但代码报告不存在或未确认",
                    "执行 rebuild-context 重建状态快照",
                )

    context_tested = parse_table_tasks(context, "测试记录")
    for task_id, value in context_tested.items():
        if "已完成" in value:
            test_report = root / "output" / f"test-report-{task_id}.md"
            if review_status(test_report) != "已确认":
                add(
                    issues,
                    "fail",
                    "missing_confirmed_test_report",
                    rel(test_report, root),
                    f"{task_id} 标记已测试，但测试报告不存在或未确认",
                    "执行 rebuild-context 重建状态快照",
                )

    if action:
        validate_action(root, action, issues, context, target)

    level_rank = {"pass": 0, "warn": 1, "fail": 2}
    status = "pass"
    for issue in issues:
        if level_rank[issue.level] > level_rank[status]:
            status = issue.level
    return {
        "status": status,
        "action": action,
        "target": target,
        "stage": stage,
        "next_step": next_step,
        "issues": [asdict(issue) for issue in issues],
    }


def validate_action(root: Path, action: str, issues: list[Issue], context: str, target: str | None = None) -> None:
    output = root / "output"
    code_repo = parse_project_field(context, "代码仓库")
    if action == "analyze-requirements":
        prd = root / "prd"
        if not prd.exists() or not any(path.suffix in {".md", ".txt", ".pdf"} for path in prd.iterdir()):
            add(issues, "fail", "missing_prd", "prd", "prd/ 中缺少支持格式的 PRD 文件")
    elif action == "design-solution":
        if review_status(output / "analysis.md") != "已确认":
            add(issues, "fail", "unconfirmed_analysis", "output/analysis.md", "需求分析未确认，不能进入技术设计")
    elif action == "generate-specs":
        if review_status(output / "analysis.md") != "已确认":
            add(issues, "fail", "unconfirmed_analysis", "output/analysis.md", "需求分析未确认，不能生成规格")
        if review_status(output / "design.md") != "已确认":
            add(issues, "fail", "unconfirmed_design", "output/design.md", "技术方案未确认，不能生成规格")
        if not parse_design_tasks(root):
            add(issues, "fail", "missing_design_tasks", "output/design.md", "技术方案中没有可生成规格的任务")
    elif action == "implement-code":
        if not code_repo or code_repo == "无" or not Path(code_repo).exists():
            add(issues, "fail", "missing_code_repo", "CONTEXT.md", "代码仓库路径缺失或不可访问")
        if review_status(output / "design.md") != "已确认":
            add(issues, "fail", "unconfirmed_design", "output/design.md", "技术方案不存在或未确认，不能实现代码")
        tasks = parse_design_tasks(root)
        if not tasks:
            add(issues, "fail", "missing_design_tasks", "output/design.md", "技术方案中没有可实现任务")
        for task_id in tasks:
            spec = output / "specs" / f"{task_id}.md"
            if review_status(spec) != "已确认":
                add(issues, "fail", "missing_confirmed_spec", rel(spec, root), f"{task_id} 规格不存在或未确认")
    elif action == "generate-tests":
        if not code_repo or code_repo == "无" or not Path(code_repo).exists():
            add(issues, "fail", "missing_code_repo", "CONTEXT.md", "代码仓库路径缺失或不可访问")
        implemented = []
        for task_id in parse_design_tasks(root):
            report = output / f"report-{task_id}.md"
            test_report = output / f"test-report-{task_id}.md"
            if review_status(report) == "已确认" and review_status(test_report) != "已确认":
                implemented.append(task_id)
        if not implemented:
            add(issues, "fail", "no_implemented_untested_task", "CONTEXT.md", "没有已实现但未测试的任务")
    elif action == "review-artifact":
        if not pending_artifacts(root):
            add(issues, "fail", "no_pending_artifact", "output", "没有待审核或需修改的阶段产物")
    elif action == "resolve-decision":
        blocks = issue_blocks(root)
        open_blocks = [(qid, block) for qid, block in blocks if not issue_resolved(block)]
        if target:
            matched = [(qid, block) for qid, block in blocks if qid == target]
            if not matched:
                add(issues, "fail", "missing_issue", "ISSUES.md", f"未找到目标问题：{target}")
                return
            if len(matched) > 1:
                add(issues, "fail", "duplicate_issue_id", "ISSUES.md", f"问题编号重复：{target}")
                return
            qid, block = matched[0]
        else:
            if not open_blocks:
                add(issues, "fail", "no_open_issue", "ISSUES.md", "没有待处理的人工决策问题")
                return
            if len(open_blocks) > 1:
                add(issues, "fail", "target_issue_required", "ISSUES.md", "存在多个待决策问题，必须指定目标 Q-XXX")
                return
            qid, block = open_blocks[0]
        if issue_resolved(block):
            add(issues, "fail", "issue_already_resolved", "ISSUES.md", f"{qid} 已标记为已解决")
        if not issue_field(block, "人工决策"):
            add(issues, "fail", "missing_manual_decision", "ISSUES.md", f"{qid} 缺少人工决策")
        if not issue_field(block, "影响"):
            add(issues, "fail", "missing_issue_impact", "ISSUES.md", f"{qid} 缺少影响范围")


def print_human(payload: dict) -> None:
    print(f"状态：{payload['status']}")
    if payload.get("action"):
        print(f"动作：{payload['action']}")
    print(f"阶段：{payload.get('stage') or '未知'}")
    print(f"下一步：{payload.get('next_step') or '未知'}")
    if not payload["issues"]:
        print("未发现确定性结构问题。")
        return
    print("问题：")
    for issue in payload["issues"]:
        suggestion = f" 建议：{issue['suggestion']}" if issue.get("suggestion") else ""
        print(f"- [{issue['level']}] {issue['type']} {issue['file']}：{issue['message']}{suggestion}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workspace", nargs="?", default=".")
    parser.add_argument("--action")
    parser.add_argument("--target")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    root = Path(args.workspace).resolve()
    payload = validate(root, args.action, args.target)
    if args.as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_human(payload)
    return 1 if payload["status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
