#!/usr/bin/env python3
"""Render a read-only AIWorkFlow dashboard from workspace facts."""

from __future__ import annotations

import argparse
import html
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


REVIEW_RE = re.compile(r"^- (状态|审核人|审核时间|修订来源)：(.*?)\s*$", re.MULTILINE)
TASK_RE = re.compile(r"\bT-\d{3}\b")
Q_HEADING_RE = re.compile(r"(?m)^### (Q-\d{3})\b\s*(?:—\s*)?(.*)$")
R_HEADING_RE = re.compile(r"(?m)^### (R-\d{3})\b\s*(?:—\s*)?(.*)$")
LOG_ENTRY_RE = re.compile(r"(?m)^### (\d{2}:\d{2})\s*—\s*(.*)$")
DATE_RE = re.compile(r"(?m)^## (\d{4}-\d{2}-\d{2})\s*$")
ISSUE_STAGES = ["分析阶段", "设计阶段", "实现阶段", "测试阶段"]
STAGE_LABELS = {
    "initialized": "准备进行需求分析",
    "requirements_analyzed": "需求已确认，等待技术设计",
    "design_ready": "技术方案已确认，等待规格或审核",
    "specs_ready": "规格已确认，等待代码实现",
    "implementation_in_progress": "代码实现中",
    "implementation_done": "实现已完成，等待测试",
    "tests_done": "流程已完成",
    "blocked_by_decision": "等待人工决策",
    "blocked_by_missing_input": "缺少必要输入",
    "blocked_by_inconsistent_state": "状态需要修复",
}
NEXT_STEP_LABELS = {
    "analyze-requirements": "生成需求分析",
    "design-solution": "生成技术方案",
    "generate-specs": "生成开发规格",
    "implement-code": "实现下一个任务",
    "generate-tests": "生成测试",
    "review-artifact": "等待人工审核",
    "status": "查看最终状态",
    "resolve-decision": "处理人工决策",
    "fix-workspace": "修复工作空间",
}
PIPELINE_STEPS = [
    ("analysis", "需求分析"),
    ("design", "技术设计"),
    ("specs", "规格生成"),
    ("implementation", "代码实现"),
    ("tests", "测试生成"),
    ("done", "完成"),
]
STAGE_PROGRESS = {
    "initialized": 0,
    "requirements_analyzed": 1,
    "design_ready": 2,
    "specs_ready": 3,
    "implementation_in_progress": 3,
    "implementation_done": 4,
    "tests_done": 5,
}
NEXT_STEP_INDEX = {
    "analyze-requirements": 0,
    "design-solution": 1,
    "generate-specs": 2,
    "implement-code": 3,
    "generate-tests": 4,
    "status": 5,
}


@dataclass
class Artifact:
    path: Path
    kind: str
    task_id: str
    status: str
    reviewer: str
    reviewed_at: str
    revision_source: str


@dataclass
class Issue:
    issue_id: str
    title: str
    stage: str
    problem: str
    suggestion: str
    impact: str
    decision: str
    status: str


@dataclass
class Revision:
    revision_id: str
    title: str
    bucket: str
    target: str
    kind: str
    opinion: str
    impact: str
    status: str
    result: str
    updated: str
    handled_at: str


@dataclass
class TimelineEntry:
    date: str
    time: str
    title: str
    details: list[str]


@dataclass
class RequirementDecision:
    req_id: str
    title: str
    module: str
    source: str
    decision: str


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def esc(value: str) -> str:
    return html.escape(value, quote=True)


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


def project_name(root: Path, context: str) -> str:
    for line in context.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            for prefix in ["工作空间上下文 — ", "工作空间上下文 - "]:
                if title.startswith(prefix):
                    return title[len(prefix) :].strip() or root.name
            return title or root.name
    return root.name


def markdown_field(block: str, label: str) -> str:
    pattern = rf"^[ \t]*-?[ \t]*\*\*{re.escape(label)}：\*\*[ \t]*(.*?)[ \t]*$"
    match = re.search(pattern, block, re.MULTILINE)
    return match.group(1).strip() if match else ""


def plain_markdown(text: str) -> str:
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    return text.strip()


def split_heading_blocks(text: str, pattern: re.Pattern[str]) -> list[tuple[re.Match[str], str]]:
    matches = list(pattern.finditer(text))
    blocks: list[tuple[re.Match[str], str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        blocks.append((match, text[match.start() : end].strip()))
    return blocks


def parse_context_field(text: str, name: str) -> str:
    current = section(text, "当前状态")
    match = re.search(rf"^- {re.escape(name)}：(.+?)\s*$", current, re.MULTILINE)
    return match.group(1).strip() if match else "未知"


def parse_project_field(text: str, name: str) -> str:
    project = section(text, "项目约束")
    match = re.search(rf"^- {re.escape(name)}：(.+?)\s*$", project, re.MULTILINE)
    return match.group(1).strip() if match else "未知"


def human_stage(stage: str) -> str:
    return STAGE_LABELS.get(stage, stage or "未知")


def human_next_step(next_step: str) -> str:
    return NEXT_STEP_LABELS.get(next_step, next_step or "未知")


def pipeline_current_index(stage: str, next_step: str) -> int:
    if next_step in NEXT_STEP_INDEX:
        return NEXT_STEP_INDEX[next_step]
    return STAGE_PROGRESS.get(stage, 0)


def render_pipeline(stage: str, next_step: str, pending_artifacts: int, open_issues: int) -> str:
    current = pipeline_current_index(stage, next_step)
    blocked = stage.startswith("blocked_by")
    review = next_step == "review-artifact"
    steps = []
    for index, (_, label) in enumerate(PIPELINE_STEPS):
        if blocked and index == current:
            state = "blocked"
            note = human_next_step(next_step)
        elif review and index == current:
            state = "review"
            note = f"{pending_artifacts} 个待审核" if pending_artifacts else "等待审核"
        elif index < current or stage == "tests_done":
            state = "done"
            note = "已完成"
        elif index == current:
            state = "current"
            note = human_next_step(next_step)
        else:
            state = "upcoming"
            note = "未开始"
        steps.append(
            f"""
            <div class="pipeline-step {state}" data-state="{state}">
              <div class="pipeline-dot">{index + 1}</div>
              <div>
                <strong>{esc(label)}</strong>
                <span>{esc(note)}</span>
              </div>
            </div>
            """
        )
    return '<div class="pipeline">' + "\n".join(steps) + "</div>"


def workspace_status(root: Path) -> tuple[str, list[str]]:
    required = ["README.md", "AGENT.md", "CONTEXT.md", "ISSUES.md", "REVISIONS.md", "JOURNAL.md", "CHANGELOG.md", "prd", "output"]
    missing = [name for name in required if not (root / name).exists()]
    if missing:
        return "缺少必要文件", missing
    return "结构完整", []


def prd_files(root: Path) -> list[Path]:
    prd = root / "prd"
    if not prd.exists():
        return []
    return sorted(path for path in prd.iterdir() if path.is_file() and path.suffix.lower() in {".md", ".txt", ".pdf"})


def requirement_summary(root: Path, context: str) -> str:
    analysis = root / "output" / "analysis.md"
    if analysis.exists():
        summary = section(read_text(analysis), "需求概要").strip()
        if summary:
            return summary
    summary = section(context, "需求概要").strip()
    return summary or "暂无需求概要。"


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
                item = line[4:].strip()
                if item and item != "暂无":
                    items.append(item)
    return items


def stage_artifact_paths(root: Path) -> list[Path]:
    output = root / "output"
    paths = [output / "analysis.md", output / "design.md"]
    paths.extend(sorted((output / "specs").glob("T-*.md")))
    paths.extend(sorted((output / "reports").glob("T-*.md")))
    paths.extend(sorted((output / "test-reports").glob("T-*.md")))
    return [path for path in paths if path.exists()]


def artifact_kind(path: Path) -> str:
    parts = path.parts
    if path.name == "analysis.md":
        return "需求分析"
    if path.name == "design.md":
        return "技术方案"
    if "specs" in parts:
        return "开发规格"
    if "reports" in parts:
        return "代码报告"
    if "test-reports" in parts:
        return "测试报告"
    return "阶段产物"


def review_fields(path: Path) -> dict[str, str]:
    fields = {"状态": "未设置", "审核人": "", "审核时间": "", "修订来源": ""}
    if not path.exists():
        return fields
    for key, value in REVIEW_RE.findall(read_text(path)):
        fields[key] = value.strip()
    return fields


def artifacts(root: Path) -> list[Artifact]:
    result: list[Artifact] = []
    for path in stage_artifact_paths(root):
        fields = review_fields(path)
        task_match = TASK_RE.search(path.name)
        result.append(
            Artifact(
                path=path,
                kind=artifact_kind(path),
                task_id=task_match.group(0) if task_match else "—",
                status=fields["状态"] or "未设置",
                reviewer=fields["审核人"] or "—",
                reviewed_at=fields["审核时间"] or "—",
                revision_source=fields["修订来源"] or "—",
            )
        )
    return result


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


def parse_issues(root: Path) -> list[Issue]:
    path = root / "ISSUES.md"
    if not path.exists():
        return []
    text = read_text(path)
    result: list[Issue] = []
    for stage in ISSUE_STAGES:
        stage_text = section(text, stage)
        for match, block in split_heading_blocks(stage_text, Q_HEADING_RE):
            status = markdown_field(block, "状态") or "待决策"
            result.append(
                Issue(
                    issue_id=match.group(1),
                    title=match.group(2).strip() or match.group(1),
                    stage=stage,
                    problem=markdown_field(block, "问题") or "未填写",
                    suggestion=markdown_field(block, "AI 建议") or "未填写",
                    impact=markdown_field(block, "影响") or "未填写",
                    decision=markdown_field(block, "人工决策") or "未填写",
                    status=status,
                )
            )
    return result


def parse_revisions(root: Path) -> list[Revision]:
    path = root / "REVISIONS.md"
    if not path.exists():
        return []
    text = read_text(path)
    result: list[Revision] = []
    for bucket in ["待处理", "已处理"]:
        bucket_text = section(text, bucket)
        for match, block in split_heading_blocks(bucket_text, R_HEADING_RE):
            result.append(
                Revision(
                    revision_id=match.group(1),
                    title=match.group(2).strip() or match.group(1),
                    bucket=bucket,
                    target=markdown_field(block, "目标产物") or "未填写",
                    kind=markdown_field(block, "修订类型") or "未填写",
                    opinion=markdown_field(block, "用户意见") or "未填写",
                    impact=markdown_field(block, "影响范围") or "未填写",
                    status=markdown_field(block, "状态") or bucket,
                    result=markdown_field(block, "处理结果") or "—",
                    updated=markdown_field(block, "更新产物") or "—",
                    handled_at=markdown_field(block, "处理时间") or "—",
                )
            )
    return result


def parse_timeline(root: Path, name: str, limit: int | None = None) -> list[TimelineEntry]:
    path = root / name
    if not path.exists():
        return []
    text = read_text(path)
    entries: list[TimelineEntry] = []
    date_matches = list(DATE_RE.finditer(text))
    for index, date_match in enumerate(date_matches):
        end = date_matches[index + 1].start() if index + 1 < len(date_matches) else len(text)
        date_body = text[date_match.end() : end]
        logs = list(LOG_ENTRY_RE.finditer(date_body))
        for log_index, log_match in enumerate(logs):
            log_end = logs[log_index + 1].start() if log_index + 1 < len(logs) else len(date_body)
            body = date_body[log_match.end() : log_end]
            details = [plain_markdown(line[2:]) for line in body.splitlines() if line.startswith("- ")]
            entries.append(TimelineEntry(date_match.group(1), log_match.group(1), plain_markdown(log_match.group(2)), details))
    ordered = entries[::-1]
    return ordered if limit is None else ordered[:limit]


def parse_requirement_decisions(root: Path) -> list[RequirementDecision]:
    path = root / "output" / "analysis.md"
    if not path.exists():
        return []
    table = section(read_text(path), "功能需求")
    decisions: list[RequirementDecision] = []
    in_table = False
    for line in table.splitlines():
        if "需求纳入决策表" in line:
            in_table = True
            continue
        if not in_table:
            continue
        if not line.startswith("|"):
            if decisions:
                break
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not cells or cells[0] in {"ID", "---"} or set(cells[0]) <= {"-", " "}:
            continue
        if len(cells) >= 5:
            decisions.append(RequirementDecision(cells[0], cells[1], cells[2], cells[3], cells[4]))
    return decisions


def status_class(status: str) -> str:
    if status in {"已确认", "已处理", "结构完整"}:
        return "ok"
    if status == "待审核" or status == "需更新" or status == "待决策" or status == "待处理":
        return "warn"
    if status in {"需修改", "阻塞", "缺少必要文件"}:
        return "danger"
    return "muted"


def path_text(path: str) -> str:
    return f'<code class="path">{esc(path)}</code>'


def artifact_anchor(path: Path, root: Path) -> str:
    raw = rel(path, root)
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "-", raw).strip("-").lower()
    return f"artifact-{safe or 'item'}"


def artifact_link(path: Path, root: Path, label: str = "查看内容", extra_class: str = "") -> str:
    classes = "artifact-link" + (f" {extra_class}" if extra_class else "")
    return f'<a class="{esc(classes)}" href="#{esc(artifact_anchor(path, root))}">{esc(label)}</a>'


def pill(value: str) -> str:
    return f'<span class="pill {status_class(value)}">{esc(value)}</span>'


def todo_meta(items: list[tuple[str, str]]) -> str:
    blocks = ""
    for label, value in items:
        meta_class = "todo-meta-status" if label == "状态" else "todo-meta-text"
        value_html = pill(value) if label == "状态" else esc(value)
        blocks += f'<div class="{meta_class}"><span>{esc(label)}</span><strong>{value_html}</strong></div>'
    return f'<div class="todo-meta">{blocks}</div>'


def todo_summary(text: str, limit: int = 96) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def metric(label: str, value: str, tone: str = "", href: str = "") -> str:
    tone_class = f" {tone}" if tone else ""
    body = f"<span>{esc(label)}</span><strong>{esc(value)}</strong>"
    if href:
        return f'<a class="metric{tone_class}" href="{esc(href)}">{body}</a>'
    return f'<div class="metric{tone_class}">{body}</div>'


def section_heading(title: str, note: str) -> str:
    return f'<div class="section-heading"><h2>{esc(title)}</h2><p>{esc(note)}</p></div>'


def empty(message: str) -> str:
    return f'<p class="empty">{esc(message)}</p>'


def render_action_queue(root: Path, artifact_items: list[Artifact], issues: list[Issue], revisions: list[Revision]) -> str:
    cards: list[str] = []
    for item in artifact_items:
        if item.status in {"待审核", "需修改"}:
            path = rel(item.path, root)
            cards.append(
                f"""
                <article class="todo-card {status_class(item.status)}">
                  <div class="todo-type"><strong>产物审核</strong><span>{esc(item.kind)}</span></div>
                  <div class="todo-main">
                    <div class="todo-content">
                      <h3>{path_text(path)}</h3>
                      <p>需要人工确认该阶段产物是否可以进入后续流程。</p>
                      {todo_meta([("状态", item.status), ("审核人", item.reviewer), ("修订来源", item.revision_source)])}
                    </div>
                    <div class="todo-action">{artifact_link(item.path, root, "去审核", "todo-action-link")}</div>
                  </div>
                </article>
                """
            )
    for issue in issues:
        if issue.status != "已解决":
            cards.append(
                f"""
                <article class="todo-card warn">
                  <div class="todo-type"><strong>待决策</strong><span>{esc(issue.stage)}</span></div>
                  <div class="todo-main">
                    <div class="todo-content">
                      <h3>{esc(issue.issue_id)} — {esc(issue.title)}</h3>
                      <p>{esc(todo_summary(issue.problem))}</p>
                      {todo_meta([("状态", issue.status), ("阶段", issue.stage)])}
                    </div>
                    <div class="todo-action"><a class="artifact-link todo-action-link" href="#issues">去处理</a></div>
                  </div>
                </article>
                """
            )
    for revision in revisions:
        if revision.bucket == "待处理":
            cards.append(
                f"""
                <article class="todo-card {status_class(revision.status)}">
                  <div class="todo-type"><strong>用户修订</strong><span>{esc(revision.kind)}</span></div>
                  <div class="todo-main">
                    <h3>{esc(revision.revision_id)} — {esc(revision.title)}</h3>
                    <p>{esc(revision.opinion)}</p>
                    {todo_meta([("状态", revision.status), ("目标", revision.target), ("影响", revision.impact)])}
                  </div>
                </article>
                """
            )
    if not cards:
        return empty("暂无人工待办。")
    return '<div class="todo-list">' + "\n".join(cards) + "</div>"


def artifact_progress(items: list[Artifact]) -> tuple[int, int]:
    total = len(items)
    confirmed = len([item for item in items if item.status == "已确认"])
    return confirmed, total


def artifact_group_order() -> list[str]:
    return ["需求分析", "技术方案", "开发规格", "代码报告", "测试报告", "阶段产物"]


def artifact_status_summary(items: list[Artifact]) -> dict[str, int]:
    summary = {"已确认": 0, "待审核": 0, "需修改": 0, "需更新": 0, "未设置": 0}
    for item in items:
        summary[item.status] = summary.get(item.status, 0) + 1
    return summary


def stage_summary_tone(items: list[Artifact]) -> str:
    if not items:
        return "muted"
    if any(item.status == "需修改" for item in items):
        return "danger"
    if any(item.status in {"待审核", "需更新"} for item in items):
        return "warn"
    if all(item.status == "已确认" for item in items):
        return "ok"
    return "muted"


def render_artifact_board(root: Path, items: list[Artifact]) -> str:
    if not items:
        return empty("暂无阶段产物。")
    grouped: dict[str, list[Artifact]] = {name: [] for name in artifact_group_order()}
    for item in items:
        grouped.setdefault(item.kind, []).append(item)
    cards = []
    for kind in artifact_group_order():
        group_items = grouped.get(kind, [])
        if not group_items:
            continue
        tone = stage_summary_tone(group_items)
        confirmed = len([item for item in group_items if item.status == "已确认"])
        summary = artifact_status_summary(group_items)
        if kind in {"需求分析", "技术方案"} and len(group_items) == 1:
            item = group_items[0]
            body = f"""
              <div class="artifact-main">
                {path_text(rel(item.path, root))}
                {pill(item.status)}
                {artifact_link(item.path, root)}
              </div>
              <div class="artifact-meta">
                <span>审核人：{esc(item.reviewer)}</span>
                <span>时间：{esc(item.reviewed_at)}</span>
                <span>修订：{esc(item.revision_source)}</span>
              </div>
            """
        else:
            chips = "".join(
                f'<span class="status-count {status_class(status)}"><strong>{esc(status)}</strong>：{count}</span>'
                for status, count in summary.items()
                if count
            )
            body = f"""
              <div class="artifact-main">
                <strong>{confirmed}/{len(group_items)} 已确认</strong>
                {pill("已确认" if confirmed == len(group_items) else "待审核" if summary.get("待审核", 0) else "需更新" if summary.get("需更新", 0) else "未设置")}
              </div>
              <div class="artifact-meta">{chips}</div>
              <div class="artifact-links">{"".join(artifact_link(item.path, root, item.task_id if item.task_id != "—" else rel(item.path, root)) for item in group_items)}</div>
            """
        cards.append(
            f"""
            <article class="artifact-summary-card {tone}">
              <div class="artifact-summary-head">
                <h3>{esc(kind)}</h3>
              </div>
              {body}
            </article>
            """
        )
    return '<div class="artifact-summary-board">' + "\n".join(cards) + "</div>"


def render_artifact_table(root: Path, items: list[Artifact]) -> str:
    if not items:
        return empty("暂无阶段产物。")
    rows = []
    for item in items:
        path = rel(item.path, root)
        rows.append(
            "<tr>"
            f"<td>{path_text(path)}</td>"
            f"<td>{esc(item.kind)}</td>"
            f"<td>{esc(item.task_id)}</td>"
            f"<td>{pill(item.status)}</td>"
            f"<td>{esc(item.reviewer)}</td>"
            f"<td>{esc(item.reviewed_at)}</td>"
            f"<td>{esc(item.revision_source)}</td>"
            "</tr>"
        )
    return table(["文件", "类型", "任务", "审核状态", "审核人", "审核时间", "修订来源"], rows)


def render_task_matrix(root: Path, tasks: dict[str, str]) -> str:
    if not tasks:
        return empty("暂无任务拆解。")
    cards = []
    for task_id, title in tasks.items():
        checkpoints = []
        for label, path in [
            ("规格", root / "output" / "specs" / f"{task_id}.md"),
            ("实现", root / "output" / "reports" / f"{task_id}.md"),
            ("测试", root / "output" / "test-reports" / f"{task_id}.md"),
        ]:
            fields = review_fields(path)
            if path.exists():
                checkpoints.append(
                    f"""
                    <a class="task-checkpoint {status_class(fields["状态"] or "未设置")}" href="#{esc(artifact_anchor(path, root))}">
                      <span>{esc(label)}</span>
                      {pill(fields["状态"] or "未设置")}
                    </a>
                    """
                )
            else:
                checkpoints.append(
                    f"""
                    <div class="task-checkpoint muted">
                      <span>{esc(label)}</span>
                      <strong>未生成</strong>
                    </div>
                    """
                )
        cards.append(
            f"""
            <article class="task-card">
              <div class="task-title">
                <strong>{esc(task_id)}</strong>
                <span>{esc(title)}</span>
              </div>
              <div class="task-checkpoints">
                {"".join(checkpoints)}
              </div>
            </article>
            """
        )
    return '<div class="task-progress-board">' + "\n".join(cards) + "</div>"


def render_issues(issues: list[Issue]) -> str:
    if not issues:
        return empty("暂无待决策问题。")
    cards = []
    for issue in issues:
        cards.append(
            f"""
            <article class="record-card {status_class(issue.status)}">
              <div class="record-head">
                <div>
                  <span class="eyebrow">{esc(issue.stage)}</span>
                  <h3>{esc(issue.issue_id)} — {esc(issue.title)}</h3>
                </div>
                {pill(issue.status)}
              </div>
              <p>{esc(issue.problem)}</p>
              <div class="record-grid">
                <div><span>AI 建议</span><strong>{esc(issue.suggestion)}</strong></div>
                <div><span>影响</span><strong>{esc(issue.impact)}</strong></div>
                <div><span>人工决策</span><strong>{esc(issue.decision)}</strong></div>
              </div>
            </article>
            """
        )
    return '<div class="record-list">' + "\n".join(cards) + "</div>"


def render_revisions(revisions: list[Revision]) -> str:
    if not revisions:
        return empty("暂无用户修订。")
    cards = []
    ordered = sorted(
        revisions,
        key=lambda item: (
            0 if item.bucket == "待处理" else 1,
            -int(item.revision_id.split("-")[1]) if "-" in item.revision_id and item.revision_id.split("-")[1].isdigit() else 0,
        ),
    )
    for revision in ordered:
        response = revision.result if revision.result and revision.result != "—" else "待处理，尚未收敛。"
        if revision.status == "阻塞" and revision.result == "—":
            response = "修订处理被阻塞，需要补充信息或先处理相关问题。"
        time_html = (
            f'<span class="time-chip">处理时间：{esc(revision.handled_at)}</span>'
            if revision.handled_at and revision.handled_at != "—"
            else ""
        )
        cards.append(
            f"""
            <article class="record-card {status_class(revision.status)}">
              <div class="record-head">
                <div>
                  <span class="eyebrow">{esc(revision.bucket)} · {esc(revision.kind)}</span>
                  <h3>{esc(revision.revision_id)} — {esc(revision.title)}</h3>
                </div>
                <div class="status-stack">{pill(revision.status)}{time_html}</div>
              </div>
              <div class="revision-dialog">
                <div class="bubble user">
                  <span>用户意见</span>
                  <p>{esc(revision.opinion)}</p>
                </div>
                <div class="bubble result {status_class(revision.status)}">
                  <span>处理结果</span>
                  <p>{esc(response)}</p>
                </div>
              </div>
              <div class="meta-tags">
                <span>目标：{esc(revision.target)}</span>
                <span>影响：{esc(revision.impact)}</span>
                <span>更新：{esc(revision.updated)}</span>
              </div>
            </article>
            """
        )
    return '<div class="record-list">' + "\n".join(cards) + "</div>"


def render_requirements(decisions: list[RequirementDecision]) -> str:
    if not decisions:
        return empty("暂无需求纳入决策表。")
    stats = requirement_stats(decisions)
    groups: list[tuple[str, str, list[RequirementDecision]]] = [
        ("待决策", "warn", []),
        ("纳入", "ok", []),
        ("暂不纳入", "muted", []),
        ("其他", "muted", []),
    ]
    grouped = {name: items for name, _, items in groups}
    for item in decisions:
        decision = item.decision or "未选择"
        if decision in {"待决策", "未选择"}:
            grouped["待决策"].append(item)
        elif decision == "纳入":
            grouped["纳入"].append(item)
        elif decision == "暂不纳入":
            grouped["暂不纳入"].append(item)
        else:
            grouped["其他"].append(item)

    stat_html = f"""
      <div class="requirement-stats">
        <div class="warn"><span>待决策</span><strong>{stats.get("待决策", 0) + stats.get("未选择", 0)}</strong></div>
        <div class="ok"><span>纳入</span><strong>{stats.get("纳入", 0)}</strong></div>
        <div class="muted"><span>暂不纳入</span><strong>{stats.get("暂不纳入", 0)}</strong></div>
      </div>
    """
    group_html = []
    for name, tone, items in groups:
        if not items:
            continue
        cards = []
        for item in items:
            decision = item.decision or "未选择"
            cards.append(
                f"""
                <article class="requirement-card {tone}">
                  <div class="requirement-id">{esc(item.req_id)}</div>
                  <div class="requirement-main">
                    <h3>{esc(item.title)}</h3>
                    <div class="requirement-meta">
                      <span>模块：{esc(item.module)}</span>
                      <span>来源：{esc(item.source)}</span>
                      <span>处理：{esc(decision)}</span>
                    </div>
                  </div>
                </article>
                """
            )
        group_html.append(
            f"""
            <section class="requirement-group {tone}">
              <div class="requirement-group-head">
                <h3>{esc(name)}</h3>
                <span>{len(items)} 项</span>
              </div>
              <div class="requirement-cards">{"".join(cards)}</div>
            </section>
            """
        )
    return '<div class="requirement-board">' + stat_html + "\n".join(group_html) + "</div>"


def requirement_stats(decisions: list[RequirementDecision]) -> dict[str, int]:
    stats = {"总数": len(decisions), "纳入": 0, "暂不纳入": 0, "待决策": 0, "未选择": 0}
    for item in decisions:
        decision = item.decision.strip()
        if decision in stats:
            stats[decision] += 1
        elif not decision:
            stats["未选择"] += 1
        else:
            stats.setdefault(decision, 0)
            stats[decision] += 1
    return stats


def render_project_overview(root: Path, context: str, requirements: list[RequirementDecision], platform: str, repo: str) -> str:
    status, missing = workspace_status(root)
    prds = prd_files(root)
    summary = requirement_summary(root, context)
    stats = requirement_stats(requirements)
    prd_items = "".join(f"<span>{path_text(rel(path, root))}</span>" for path in prds) if prds else "<span>暂无可识别 PRD 文件</span>"
    repo_html = path_text(repo) if repo and repo != "无" else "<strong>未配置</strong>"
    missing_html = (
        f"""
        <div class="missing-line">
          <span class="muted-text">缺失项</span>
          <div>{"".join(f"<span>{esc(item)}</span>" for item in missing)}</div>
        </div>
        """
        if missing
        else ""
    )
    return f"""
    <div class="context-grid">
      <article class="context-card summary-card">
        <span class="eyebrow">需求概要</span>
        <div class="summary-block">{esc(summary)}</div>
      </article>
      <aside class="context-card meta-card">
        <div class="meta-row"><span>工作空间</span>{pill(status)}</div>
        <div class="meta-row"><span>PRD</span><strong>{len(prds)} 份</strong></div>
        <div class="meta-row"><span>平台</span><strong>{esc(platform)}</strong></div>
        <div class="meta-row repo-row"><span>代码仓库</span><div class="meta-value">{repo_html}</div></div>
        <div class="req-stat-row">
          <span>需求</span>
          <strong>{stats.get("总数", 0)} 总数</strong>
          <strong>{stats.get("纳入", 0)} 纳入</strong>
          <strong>{stats.get("待决策", 0)} 待决策</strong>
        </div>
        {missing_html}
        <div class="prd-list"><span class="eyebrow">PRD 文件</span><div>{prd_items}</div></div>
      </aside>
    </div>
    """


def render_timeline_detail(detail: str) -> str:
    label = ""
    value = detail
    if "：" in detail:
        label, value = detail.split("：", 1)
    elif ":" in detail:
        label, value = detail.split(":", 1)
    label = label.strip()
    value = value.strip()
    if label and value:
        tone = " body" if label in {"问题", "内容", "说明", "结果", "处理", "决策", "日志"} else ""
        return f'<div class="timeline-detail{tone}"><span>{esc(label)}</span><p>{esc(value)}</p></div>'
    return f'<div class="timeline-detail body single"><p>{esc(detail)}</p></div>'


def render_timeline(entries: list[TimelineEntry], empty_message: str) -> str:
    if not entries:
        return empty(empty_message)
    groups: dict[str, list[TimelineEntry]] = {}
    for entry in entries:
        groups.setdefault(entry.date, []).append(entry)
    date_groups = []
    for date, date_entries in groups.items():
        items = []
        for entry in date_entries:
            detail = "".join(render_timeline_detail(item) for item in entry.details)
            detail_html = f'<div class="timeline-details">{detail}</div>' if detail else ""
            items.append(
                f"""
                <article class="timeline-item">
                  <div class="timeline-time"><time>{esc(entry.time)}</time></div>
                  <div class="timeline-body">
                    <h3>{esc(entry.title)}</h3>
                    {detail_html}
                  </div>
                </article>
                """
            )
        date_groups.append(
            f"""
            <section class="timeline-date-group">
              <div class="timeline-date-label">
                <h3>{esc(date)}</h3>
              </div>
              <div class="timeline-date-items">{"".join(items)}</div>
            </section>
            """
        )
    return '<div class="timeline">' + "\n".join(date_groups) + "</div>"


def render_inline_markdown(text: str) -> str:
    escaped = esc(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", escaped)
    return escaped


def is_table_separator(line: str) -> bool:
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    return bool(cells) and all(cell and set(cell) <= {"-", ":"} for cell in cells)


def table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def render_markdown_preview(text: str) -> str:
    lines = text.splitlines()
    html_parts: list[str] = []
    paragraph: list[str] = []
    list_items: list[str] = []
    quote_lines: list[str] = []
    in_code = False
    code_language = ""
    code_lines: list[str] = []
    index = 0

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            html_parts.append(f"<p>{render_inline_markdown(' '.join(paragraph))}</p>")
            paragraph = []

    def flush_list() -> None:
        nonlocal list_items
        if list_items:
            html_parts.append("<ul>" + "".join(f"<li>{render_inline_markdown(item)}</li>" for item in list_items) + "</ul>")
            list_items = []

    def flush_quote() -> None:
        nonlocal quote_lines
        if quote_lines:
            html_parts.append("<blockquote>" + "".join(f"<p>{render_inline_markdown(item)}</p>" for item in quote_lines) + "</blockquote>")
            quote_lines = []

    def flush_code() -> None:
        nonlocal code_language, code_lines
        code = "\n".join(code_lines)
        if code_language == "mermaid":
            html_parts.append(
                '<div class="diagram-card">'
                '<button class="diagram-open" type="button" aria-label="全屏查看图表">全屏查看</button>'
                '<div class="mermaid">' + esc(code) + "</div>"
                "</div>"
            )
        else:
            html_parts.append("<pre><code>" + esc(code) + "</code></pre>")
        code_language = ""
        code_lines = []

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if stripped.startswith("```"):
            flush_paragraph()
            flush_list()
            flush_quote()
            if in_code:
                flush_code()
                in_code = False
            else:
                in_code = True
                code_language = stripped[3:].strip().split(" ", 1)[0].lower()
            index += 1
            continue
        if in_code:
            code_lines.append(line)
            index += 1
            continue
        if not stripped:
            flush_paragraph()
            flush_list()
            flush_quote()
            index += 1
            continue
        quote = re.match(r"^>+\s?(.*)$", stripped)
        if quote:
            flush_paragraph()
            flush_list()
            quote_lines.append(quote.group(1).strip())
            index += 1
            continue
        if stripped.startswith("|") and index + 1 < len(lines) and lines[index + 1].strip().startswith("|") and is_table_separator(lines[index + 1]):
            flush_paragraph()
            flush_list()
            flush_quote()
            headers = table_cells(stripped)
            index += 2
            rows = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                rows.append(table_cells(lines[index].strip()))
                index += 1
            header_html = "".join(f"<th>{render_inline_markdown(cell)}</th>" for cell in headers)
            row_html = "".join(
                "<tr>" + "".join(f"<td>{render_inline_markdown(cell)}</td>" for cell in row) + "</tr>"
                for row in rows
            )
            html_parts.append(f'<div class="md-table-wrap"><table><thead><tr>{header_html}</tr></thead><tbody>{row_html}</tbody></table></div>')
            continue
        heading = re.match(r"^(#{1,4})\s+(.+)$", stripped)
        if heading:
            flush_paragraph()
            flush_list()
            flush_quote()
            level = min(len(heading.group(1)) + 1, 5)
            html_parts.append(f"<h{level}>{render_inline_markdown(heading.group(2))}</h{level}>")
            index += 1
            continue
        if stripped.startswith("- "):
            flush_paragraph()
            flush_quote()
            list_items.append(stripped[2:].strip())
            index += 1
            continue
        flush_list()
        flush_quote()
        paragraph.append(stripped)
        index += 1

    flush_paragraph()
    flush_list()
    flush_quote()
    if in_code:
        flush_code()
    return '<div class="artifact-markdown">' + "\n".join(html_parts) + "</div>"


def render_artifact_previews(root: Path, items: list[Artifact]) -> str:
    if not items:
        return empty("暂无可预览产物。")
    previews = []
    for item in items:
        content = render_markdown_preview(read_text(item.path))
        previews.append(
            f"""
            <details class="artifact-preview" id="{esc(artifact_anchor(item.path, root))}">
              <summary>
                <div class="artifact-preview-head">
                  <span>{esc(item.kind)}</span>
                  <strong>{path_text(rel(item.path, root))}</strong>
                </div>
                <div class="artifact-preview-state">{pill(item.status)}</div>
              </summary>
              {content}
            </details>
            """
        )
    return '<div class="artifact-preview-list">' + "\n".join(previews) + "</div>"


def table(headers: list[str], rows: list[str]) -> str:
    header_html = "".join(f"<th>{esc(item)}</th>" for item in headers)
    return f"""
    <div class="table-wrap">
      <table>
        <thead><tr>{header_html}</tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
    </div>
    """


def render_dashboard(root: Path) -> str:
    context_path = root / "CONTEXT.md"
    if not context_path.exists():
        raise SystemExit(f"missing CONTEXT.md in {root}")
    context = read_text(context_path)
    name = project_name(root, context)
    artifact_items = artifacts(root)
    issues = parse_issues(root)
    revisions = parse_revisions(root)
    tasks = parse_design_tasks(root)
    requirements = parse_requirement_decisions(root)
    journal = parse_timeline(root, "JOURNAL.md")
    changelog = parse_timeline(root, "CHANGELOG.md")
    stage = parse_context_field(context, "阶段")
    next_step = parse_context_field(context, "下一步")
    platform = parse_project_field(context, "平台")
    repo = parse_project_field(context, "代码仓库")
    pending_artifacts = len([item for item in artifact_items if item.status in {"待审核", "需修改"}])
    open_issues = len([item for item in issues if item.status != "已解决"])
    pending_revisions = len([item for item in revisions if item.bucket == "待处理"])
    undecided_requirements = len([item for item in requirements if item.decision in {"", "待决策"}])
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(name)}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f5fbff;
      --surface: #ffffff;
      --surface-soft: #f8fcff;
      --surface-tint: #eef8ff;
      --card-bg: #f8fcff;
      --card-inner-bg: #ffffff;
      --text: #111827;
      --muted: #5f6f86;
      --line: #d8e8f6;
      --accent: #0ea5e9;
      --accent-strong: #0284c7;
      --accent-border: #7dd3fc;
      --accent-soft: #e0f2fe;
      --ok: #059669;
      --ok-border: #86efac;
      --ok-soft: #ecfdf5;
      --warn: #d6a100;
      --warn-border: #fde047;
      --warn-soft: #fefce8;
      --danger: #dc2626;
      --danger-border: #fca5a5;
      --danger-soft: #fef2f2;
      --info-soft: #e0f2fe;
      --revision-user-bg: #eff9ff;
      --revision-user-border: #bae6fd;
      --revision-result-bg: #f0fdfa;
      --revision-result-border: #99f6e4;
      --radius: 8px;
      --radius-sm: 6px;
      --shadow: 0 18px 48px rgba(14, 116, 144, 0.10);
      --shadow-soft: 0 8px 22px rgba(2, 132, 199, 0.06);
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{
      margin: 0;
      background:
        linear-gradient(180deg, rgba(224, 242, 254, 0.76), rgba(245, 251, 255, 0) 360px),
        var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.5;
    }}
    a {{ color: var(--accent); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .shell {{ max-width: 1520px; margin: 0 auto; padding: 24px; }}
    .main-column {{
      min-width: 0;
    }}
    .hero {{
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      padding: 24px;
      box-shadow: var(--shadow);
    }}
    .hero-top {{
      display: grid;
      grid-template-columns: minmax(260px, 1fr) auto;
      gap: 20px;
      align-items: start;
    }}
    h1, h2, h3, p {{ margin-top: 0; }}
    h1 {{ font-size: 26px; margin-bottom: 8px; letter-spacing: 0; }}
    h2 {{ font-size: 18px; margin-bottom: 14px; letter-spacing: 0; }}
    h3 {{ font-size: 15px; margin-bottom: 6px; letter-spacing: 0; }}
    .muted-text, .subtle {{ color: var(--muted); }}
    .stage-line {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 16px; }}
    .chip {{
      display: inline-flex;
      align-items: center;
      min-height: 30px;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 4px 10px;
      background: var(--surface-soft);
      font-size: 13px;
      white-space: nowrap;
    }}
    .pipeline {{
      display: grid;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      gap: 18px;
      margin-top: 18px;
    }}
    .pipeline-step {{
      position: relative;
      display: flex;
      gap: 8px;
      align-items: flex-start;
      min-width: 0;
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background: var(--surface-soft);
      padding: 10px;
    }}
    .pipeline-step::after {{
      content: "";
      position: absolute;
      top: 50%;
      right: -15px;
      width: 12px;
      height: 12px;
      border-top: 2px solid var(--line);
      border-right: 2px solid var(--line);
      transform: translateY(-50%) rotate(45deg);
    }}
    .pipeline-step:last-child::after {{
      display: none;
    }}
    .pipeline-dot {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      flex: 0 0 24px;
      width: 24px;
      height: 24px;
      border-radius: 999px;
      border: 1px solid var(--line);
      color: var(--muted);
      background: var(--surface);
      font-size: 12px;
      font-weight: 700;
    }}
    .pipeline-step strong {{
      display: block;
      font-size: 13px;
      margin-bottom: 2px;
      white-space: nowrap;
    }}
    .pipeline-step span {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.35;
      overflow-wrap: anywhere;
    }}
    .pipeline-step.done {{
      background: var(--accent-soft);
      border-color: var(--accent-border);
    }}
    .pipeline-step.done::after {{
      border-color: var(--accent);
    }}
    .pipeline-step.done .pipeline-dot {{
      color: #ffffff;
      background: var(--accent);
      border-color: var(--accent);
    }}
    .pipeline-step.current {{
      background: var(--accent-soft);
      border-color: var(--accent-border);
    }}
    .pipeline-step.current::after {{
      border-color: var(--accent);
    }}
    .pipeline-step.current .pipeline-dot {{
      color: #ffffff;
      background: var(--accent);
      border-color: var(--accent);
    }}
    .pipeline-step.review {{
      background: var(--accent-soft);
      border-color: var(--accent-border);
    }}
    .pipeline-step.review::after {{
      border-color: var(--accent);
    }}
    .pipeline-step.review .pipeline-dot {{
      color: #ffffff;
      background: var(--accent);
      border-color: var(--accent);
    }}
    .pipeline-step.blocked {{
      background: var(--accent-soft);
      border-color: var(--accent-border);
    }}
    .pipeline-step.blocked::after {{
      border-color: var(--accent);
    }}
    .pipeline-step.blocked .pipeline-dot {{
      color: #ffffff;
      background: var(--accent);
      border-color: var(--accent);
    }}
    .pipeline-note {{
      margin-top: 8px;
      border: 1px solid var(--line);
      border-radius: var(--radius);
      padding: 8px 10px;
      color: var(--muted);
      background: var(--surface-soft);
      font-size: 13px;
    }}
    .pipeline-note.danger {{
      color: var(--danger);
      background: var(--surface);
      border-color: var(--danger-border);
    }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(3, minmax(150px, 1fr));
      gap: 10px;
      margin-top: 20px;
    }}
    .metric {{
      display: block;
      border: 1px solid var(--line);
      border-radius: var(--radius);
      padding: 12px;
      background: var(--card-bg);
      color: inherit;
      text-decoration: none;
      min-width: 0;
    }}
    a.metric:hover {{
      border-color: var(--accent-border);
      box-shadow: 0 6px 18px rgba(29, 78, 216, 0.10);
      text-decoration: none;
    }}
    .metric span {{ display: block; color: var(--muted); font-size: 12px; }}
    .metric strong {{ display: block; font-size: 22px; margin-top: 4px; overflow-wrap: anywhere; }}
    .page-layout {{
      display: grid;
      grid-template-columns: 220px minmax(0, 1fr);
      gap: 18px;
      align-items: start;
    }}
    .page-layout.outline-collapsed {{
      grid-template-columns: 52px minmax(0, 1fr);
    }}
    .outline {{
      position: sticky;
      top: 18px;
      align-self: start;
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background: var(--surface);
      padding: 10px;
      max-height: calc(100vh - 36px);
      overflow: auto;
      box-shadow: var(--shadow-soft);
    }}
    .outline-head {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      margin-bottom: 8px;
    }}
    .outline-title {{
      color: var(--muted);
      font-size: 13px;
      font-weight: 600;
      white-space: nowrap;
    }}
    .outline-toggle {{
      width: 30px;
      height: 30px;
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background: var(--surface-soft);
      color: var(--text);
      cursor: pointer;
      font-size: 16px;
      line-height: 1;
    }}
    .outline nav {{
      display: grid;
      gap: 4px;
    }}
    .outline a {{
      display: block;
      border-radius: 7px;
      padding: 8px 9px;
      color: var(--text);
      font-size: 14px;
      text-decoration: none;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .outline a:hover {{
      background: var(--surface-soft);
      text-decoration: none;
    }}
    .page-layout.outline-collapsed .outline {{
      padding: 10px;
    }}
    .page-layout.outline-collapsed .outline-title,
    .page-layout.outline-collapsed .outline a {{
      display: none;
    }}
    .page-layout.outline-collapsed .outline-head {{
      justify-content: center;
      margin-bottom: 0;
    }}
    .content-flow {{
      min-width: 0;
      margin-top: 18px;
    }}
    .panel {{
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      padding: 20px;
      margin-bottom: 18px;
      min-width: 0;
      scroll-margin-top: 18px;
      box-shadow: var(--shadow-soft);
    }}
    .panel.primary {{
      border-color: var(--line);
      background: var(--surface);
    }}
    .context-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }}
    .context-card {{
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background: var(--card-bg);
      padding: 16px;
      min-width: 0;
    }}
    .meta-card {{
      display: grid;
      gap: 8px;
      align-content: start;
    }}
    .meta-row, .req-stat-row {{
      display: flex;
      align-items: center;
      gap: 10px;
      min-width: 0;
      border-bottom: 1px solid var(--line);
      padding-bottom: 8px;
    }}
    .meta-row span, .req-stat-row span {{
      width: 72px;
      flex: 0 0 72px;
      color: var(--muted);
      font-size: 13px;
      white-space: nowrap;
    }}
    .meta-row strong, .req-stat-row strong {{
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      font-size: 14px;
    }}
    .repo-row {{
      align-items: flex-start;
    }}
    .meta-value {{
      min-width: 0;
      flex: 1;
      overflow-wrap: anywhere;
    }}
    .req-stat-row strong {{
      border: 1px solid var(--line);
      border-radius: 999px;
      background: var(--card-inner-bg);
      padding: 1px 8px;
      font-size: 12px;
    }}
    .missing-line {{
      display: flex;
      align-items: center;
      gap: 10px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--card-bg);
      padding: 9px 12px;
    }}
    .missing-line > span {{ white-space: nowrap; }}
    .missing-line div {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      min-width: 0;
    }}
    .missing-line div span {{
      border: 1px solid var(--line);
      border-radius: 999px;
      background: var(--card-inner-bg);
      padding: 1px 8px;
      font-size: 12px;
      white-space: nowrap;
    }}
    .prd-list {{
      display: grid;
      gap: 6px;
    }}
    .prd-list > div {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }}
    .summary-block {{
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      color: var(--text);
      font-size: 15px;
      line-height: 1.65;
      max-height: 360px;
      overflow: auto;
    }}
    .section-heading {{
      display: flex;
      justify-content: space-between;
      gap: 18px;
      align-items: start;
      margin-bottom: 18px;
      border-bottom: 1px solid var(--line);
      padding-bottom: 14px;
    }}
    .section-heading h2 {{ margin-bottom: 0; }}
    .section-heading p {{
      max-width: 560px;
      margin-bottom: 0;
      color: var(--muted);
      font-size: 14px;
      text-align: right;
    }}
    .todo-list {{ display: grid; gap: 12px; }}
    .todo-card {{
      display: grid;
      grid-template-columns: 128px minmax(0, 1fr);
      gap: 0;
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background: var(--card-bg);
      padding: 0;
      overflow: hidden;
      box-shadow: 0 8px 22px rgba(2, 132, 199, 0.04);
    }}
    .todo-type {{
      display: grid;
      align-content: start;
      gap: 6px;
      min-width: 0;
      border-right: 1px solid var(--line);
      padding: 14px 12px;
      background: var(--surface-tint);
    }}
    .todo-type strong {{
      color: var(--text);
      font-size: 13px;
      line-height: 1.25;
    }}
    .todo-type span {{
      color: var(--muted);
      font-size: 12px;
      line-height: 1.35;
      overflow-wrap: anywhere;
    }}
    .todo-main {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 16px;
      align-items: start;
      min-width: 0;
      padding: 16px;
    }}
    .todo-content {{
      display: grid;
      gap: 10px;
      min-width: 0;
    }}
    .todo-action {{
      display: flex;
      align-items: center;
      justify-content: flex-end;
      align-self: center;
      flex: 0 0 auto;
    }}
    .todo-action .todo-action-link {{
      flex: 0 0 88px;
      width: 88px;
      height: 36px;
      min-height: 0;
      justify-content: center;
      border-color: var(--accent);
      background: var(--accent);
      color: #ffffff;
      padding: 0;
      font-size: 13px;
      line-height: 1;
    }}
    .todo-action .todo-action-link:hover {{
      background: var(--accent-strong);
      border-color: var(--accent-strong);
    }}
    .todo-main h3 {{
      margin: 0;
      font-size: 15px;
      line-height: 1.45;
      overflow-wrap: anywhere;
    }}
    .todo-main p {{
      margin: 0;
      color: #1f2937;
      overflow-wrap: anywhere;
    }}
    .todo-meta {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 12px;
      align-items: stretch;
      border-top: 1px solid var(--line);
      padding-top: 12px;
    }}
    .todo-meta div {{
      display: grid;
      grid-template-rows: auto minmax(0, 1fr);
      align-items: start;
      min-width: 0;
      min-height: 74px;
      border: 1px solid var(--line);
      border-radius: var(--radius-sm);
      background: var(--card-inner-bg);
      padding: 10px;
    }}
    .todo-meta span {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 6px;
      white-space: nowrap;
    }}
    .todo-meta strong {{
      display: flex;
      align-items: flex-start;
      justify-content: flex-start;
      color: var(--text);
      font-size: 13px;
      font-weight: 600;
      line-height: 1.45;
      overflow-wrap: anywhere;
      text-align: left;
    }}
    .todo-meta .todo-meta-status {{
      align-items: center;
      justify-items: center;
      text-align: center;
    }}
    .todo-meta .todo-meta-status strong {{
      align-items: center;
      justify-content: center;
      text-align: center;
    }}
    .todo-meta .todo-meta-text strong {{
      max-height: 4.4em;
      overflow: auto;
      scrollbar-width: thin;
    }}
    .todo-meta .pill {{
      margin: 0 auto;
      width: auto;
    }}
    .requirement-board {{
      display: grid;
      gap: 14px;
    }}
    .requirement-stats {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
    }}
    .requirement-stats div {{
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background: var(--card-bg);
      padding: 12px;
    }}
    .requirement-stats div.ok {{ border-color: var(--ok-border); background: var(--card-bg); }}
    .requirement-stats div.warn {{ border-color: var(--warn-border); background: var(--card-bg); }}
    .requirement-stats div.muted {{ background: var(--card-bg); }}
    .requirement-stats span {{
      display: block;
      color: var(--muted);
      font-size: 12px;
    }}
    .requirement-stats strong {{
      display: block;
      margin-top: 2px;
      font-size: 22px;
    }}
    .requirement-group {{
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background: var(--card-bg);
      overflow: hidden;
    }}
    .requirement-group.ok {{ border-color: var(--ok-border); }}
    .requirement-group.warn {{ border-color: var(--warn-border); }}
    .requirement-group.muted {{ border-color: var(--line); }}
    .requirement-group-head {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      border-bottom: 1px solid var(--line);
      padding: 12px 14px;
      background: var(--surface-soft);
    }}
    .requirement-group.ok .requirement-group-head {{ background: var(--surface-tint); }}
    .requirement-group.warn .requirement-group-head {{ background: var(--surface-tint); }}
    .requirement-group.muted .requirement-group-head {{ background: var(--surface-tint); }}
    .requirement-group-head h3 {{
      margin: 0;
      font-size: 15px;
    }}
    .requirement-group-head span {{
      color: var(--muted);
      font-size: 12px;
      white-space: nowrap;
    }}
    .requirement-cards {{
      display: grid;
      gap: 0;
    }}
    .requirement-card {{
      display: grid;
      grid-template-columns: 96px minmax(0, 1fr);
      gap: 12px;
      min-width: 0;
      border-bottom: 1px solid var(--line);
      background: var(--card-inner-bg);
      padding: 14px;
    }}
    .requirement-card:last-child {{ border-bottom: 0; }}
    .requirement-id {{
      color: var(--accent);
      font-weight: 700;
      white-space: nowrap;
    }}
    .requirement-card.ok .requirement-id {{ color: var(--ok); }}
    .requirement-card.warn .requirement-id {{ color: var(--warn); }}
    .requirement-card.muted .requirement-id {{ color: var(--muted); }}
    .requirement-main {{
      display: grid;
      gap: 6px;
      min-width: 0;
    }}
    .requirement-main h3 {{
      margin: 0;
      font-size: 14px;
      overflow-wrap: anywhere;
    }}
    .requirement-meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }}
    .requirement-meta span {{
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--card-bg);
      color: var(--muted);
      padding: 2px 7px;
      font-size: 12px;
      overflow-wrap: anywhere;
    }}
    .task-progress-board {{
      display: grid;
      gap: 10px;
    }}
    .task-card {{
      display: grid;
      grid-template-columns: minmax(220px, 1fr) minmax(360px, 1.5fr);
      gap: 12px;
      align-items: center;
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background: var(--card-bg);
      padding: 14px;
      min-width: 0;
    }}
    .task-title {{
      display: grid;
      gap: 3px;
      min-width: 0;
    }}
    .task-title strong {{
      color: var(--accent);
      white-space: nowrap;
    }}
    .task-title span {{
      overflow-wrap: anywhere;
    }}
    .task-checkpoints {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
    }}
    .task-checkpoint {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
      min-width: 0;
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background: var(--card-inner-bg);
      padding: 8px;
      color: inherit;
      text-decoration: none;
    }}
    a.task-checkpoint:hover {{
      border-color: var(--accent-border);
      text-decoration: none;
    }}
    .task-checkpoint.ok {{ border-color: var(--ok-border); background: var(--card-inner-bg); }}
    .task-checkpoint.warn {{ border-color: var(--warn-border); background: var(--card-inner-bg); }}
    .task-checkpoint.danger {{ border-color: var(--danger-border); background: var(--card-inner-bg); }}
    .task-checkpoint span {{
      color: var(--muted);
      font-size: 12px;
      white-space: nowrap;
    }}
    .task-checkpoint strong {{
      color: var(--muted);
      font-size: 12px;
      white-space: nowrap;
    }}
    .record-list {{ display: grid; gap: 10px; }}
    .record-card {{
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background: var(--card-bg);
      padding: 14px;
    }}
    .record-card.ok,
    .record-card.warn,
    .record-card.danger {{ border-color: var(--line); }}
    .record-card p {{ margin-bottom: 10px; overflow-wrap: anywhere; }}
    .record-head {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: start;
      margin-bottom: 8px;
    }}
    .status-stack {{
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: 6px;
    }}
    .time-chip {{
      display: inline-flex;
      align-items: center;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: var(--card-inner-bg);
      color: var(--muted);
      padding: 2px 8px;
      font-size: 12px;
      white-space: nowrap;
    }}
    .record-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
    }}
    .record-grid div {{
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background: var(--card-inner-bg);
      padding: 8px;
      min-width: 0;
    }}
    .record-grid span {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 3px;
    }}
    .record-grid strong {{
      display: block;
      font-size: 13px;
      font-weight: 500;
      overflow-wrap: anywhere;
    }}
    .revision-dialog {{
      display: grid;
      gap: 8px;
      margin-top: 10px;
    }}
    .bubble {{
      border: 1px solid var(--line);
      border-radius: var(--radius);
      padding: 10px 12px;
      min-width: 0;
    }}
    .bubble span {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 4px;
    }}
    .bubble p {{
      margin: 0;
      overflow-wrap: anywhere;
    }}
    .bubble.user {{
      background: var(--revision-user-bg);
      border-color: var(--revision-user-border);
    }}
    .bubble.result.ok {{
      background: var(--revision-result-bg);
      border-color: var(--revision-result-border);
    }}
    .bubble.result.warn {{
      background: var(--warn-soft);
      border-color: var(--warn-border);
    }}
    .bubble.result.danger {{
      background: var(--danger-soft);
      border-color: var(--danger-border);
    }}
    .meta-tags {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-top: 10px;
    }}
    .meta-tags span {{
      border: 1px solid var(--line);
      border-radius: 999px;
      background: var(--card-inner-bg);
      color: var(--muted);
      padding: 2px 8px;
      font-size: 12px;
      overflow-wrap: anywhere;
    }}
    .artifact-summary-board {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 12px;
    }}
    .artifact-summary-card {{
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background: var(--card-bg);
      padding: 14px;
      min-width: 0;
    }}
    .artifact-summary-card.ok,
    .artifact-summary-card.warn,
    .artifact-summary-card.danger {{ border-color: var(--line); }}
    .artifact-summary-card.muted {{ border-color: var(--line); }}
    .artifact-summary-head {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 10px;
    }}
    .artifact-summary-head h3 {{
      margin: 0;
    }}
    .artifact-main {{
      display: flex;
      align-items: center;
      flex-wrap: wrap;
      gap: 10px;
      min-width: 0;
    }}
    .artifact-main strong {{
      font-size: 18px;
    }}
    .artifact-link {{
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      border: 1px solid var(--accent-border);
      border-radius: var(--radius-sm);
      background: var(--card-inner-bg);
      color: var(--accent);
      padding: 2px 8px;
      font-size: 12px;
      font-weight: 650;
      text-decoration: none;
      white-space: nowrap;
    }}
    .artifact-link:hover {{
      border-color: var(--accent-border);
      background: var(--accent-soft);
      text-decoration: none;
    }}
    .artifact-links {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-top: 10px;
    }}
    .artifact-meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-top: 8px;
    }}
    .artifact-meta span {{
      border: 1px solid var(--line);
      border-radius: 999px;
      background: var(--card-inner-bg);
      color: var(--muted);
      padding: 1px 7px;
      font-size: 12px;
    }}
    .artifact-preview-list {{
      display: grid;
      gap: 12px;
    }}
    .artifact-preview {{
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background: var(--card-bg);
      overflow: hidden;
      scroll-margin-top: 18px;
    }}
    .artifact-preview[open] {{
      border-color: var(--accent-border);
    }}
    .artifact-preview summary {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      padding: 14px 16px;
      cursor: pointer;
      background: var(--surface-tint);
    }}
    .artifact-preview-head {{
      display: grid;
      gap: 4px;
      min-width: 0;
    }}
    .artifact-preview-state {{
      flex: 0 0 auto;
    }}
    .artifact-preview summary span {{
      color: var(--muted);
      font-size: 12px;
      font-weight: 650;
    }}
    .artifact-preview summary strong {{
      min-width: 0;
      font-size: 13px;
      overflow-wrap: anywhere;
    }}
    .artifact-markdown {{
      display: grid;
      gap: 12px;
      padding: 20px;
      color: var(--text);
      font-size: 15px;
      line-height: 1.72;
    }}
    .artifact-markdown > :first-child {{ margin-top: 0; }}
    .artifact-markdown h2,
    .artifact-markdown h3,
    .artifact-markdown h4,
    .artifact-markdown h5 {{
      margin: 14px 0 0;
      line-height: 1.35;
      font-weight: 700;
      color: var(--text);
    }}
    .artifact-markdown h2 {{ font-size: 18px; }}
    .artifact-markdown h3 {{ font-size: 17px; }}
    .artifact-markdown h4 {{ font-size: 16px; }}
    .artifact-markdown h5 {{ font-size: 15px; }}
    .artifact-markdown h4,
    .artifact-markdown h5 {{
      padding-top: 4px;
    }}
    .artifact-markdown p {{
      margin: 0;
      overflow-wrap: anywhere;
    }}
    .artifact-markdown ul {{
      margin: 0;
      padding-left: 22px;
    }}
    .artifact-markdown blockquote {{
      display: grid;
      gap: 6px;
      margin: 0;
      border-left: 4px solid var(--accent-border);
      border-radius: 8px;
      background: var(--card-inner-bg);
      color: #536579;
      padding: 12px 14px;
    }}
    .artifact-markdown pre {{
      margin: 0;
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background: var(--surface-tint);
      padding: 12px;
    }}
    .artifact-markdown code {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 12px;
    }}
    .artifact-markdown .diagram-card {{
      position: relative;
      display: grid;
      margin: 0;
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background: var(--card-inner-bg);
      min-width: 0;
    }}
    .artifact-markdown .diagram-card .mermaid {{
      margin: 0;
      overflow-x: auto;
      padding: 16px;
      text-align: center;
    }}
    .diagram-open {{
      position: absolute;
      top: 10px;
      right: 10px;
      z-index: 1;
      border: 1px solid var(--accent-border);
      border-radius: var(--radius-sm);
      background: rgba(255, 255, 255, 0.92);
      color: var(--accent);
      padding: 4px 8px;
      font-size: 12px;
      font-weight: 650;
      cursor: pointer;
    }}
    .diagram-open:hover {{
      background: var(--accent-soft);
    }}
    .diagram-viewer {{
      position: fixed;
      inset: 0;
      z-index: 2000;
      display: none;
      background: rgba(12, 18, 28, 0.88);
      color: white;
    }}
    .diagram-viewer.open {{
      display: grid;
      grid-template-rows: auto 1fr;
    }}
    .diagram-viewer-toolbar {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 12px 16px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.16);
      background: rgba(12, 18, 28, 0.94);
    }}
    .diagram-viewer-title {{
      font-weight: 700;
    }}
    .diagram-viewer-actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .diagram-viewer-actions button {{
      border: 1px solid rgba(255, 255, 255, 0.28);
      border-radius: var(--radius-sm);
      background: rgba(255, 255, 255, 0.1);
      color: white;
      padding: 6px 10px;
      font-weight: 650;
      cursor: pointer;
    }}
    .diagram-viewer-actions button:hover {{
      background: rgba(255, 255, 255, 0.18);
    }}
    .diagram-stage {{
      position: relative;
      overflow: hidden;
      cursor: grab;
    }}
    .diagram-stage.dragging {{
      cursor: grabbing;
    }}
    .diagram-canvas {{
      position: absolute;
      top: 50%;
      left: 50%;
      transform-origin: center center;
      min-width: 240px;
      min-height: 160px;
      display: grid;
      place-items: center;
      border-radius: var(--radius);
      background: white;
      padding: 24px;
      color: var(--text);
    }}
    .diagram-canvas svg {{
      max-width: none;
      height: auto;
    }}
    .md-table-wrap {{
      overflow-x: auto;
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background: var(--card-inner-bg);
    }}
    .eyebrow {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 3px;
    }}
    .pill {{
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      border-radius: 999px;
      padding: 2px 8px;
      font-size: 12px;
      border: 1px solid var(--line);
      white-space: nowrap;
    }}
    .pill.ok {{ color: var(--ok); background: var(--card-inner-bg); border-color: var(--ok-border); }}
    .pill.warn {{ color: var(--warn); background: var(--warn-soft); border-color: var(--warn-border); }}
    .pill.danger {{ color: var(--danger); background: var(--card-inner-bg); border-color: var(--danger-border); }}
    .pill.muted {{ color: var(--muted); background: var(--surface-tint); }}
    .status-count strong {{
      font-weight: 650;
    }}
    .status-count.ok strong {{ color: var(--ok); }}
    .status-count.warn strong {{ color: var(--warn); }}
    .status-count.danger strong {{ color: var(--danger); }}
    .status-count.muted strong {{ color: var(--muted); }}
    .path {{
      display: inline-block;
      max-width: 100%;
      color: #1f2937;
      background: var(--surface-tint);
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 2px 6px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 12px;
      line-height: 1.45;
      white-space: normal;
      overflow-wrap: anywhere;
    }}
    .table-wrap {{ overflow-x: auto; border: 1px solid var(--line); border-radius: 8px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; background: var(--surface); }}
    th, td {{ border-bottom: 1px solid var(--line); padding: 10px; text-align: left; vertical-align: top; }}
    th {{ color: var(--muted); background: var(--surface-soft); font-weight: 600; white-space: nowrap; }}
    tr:last-child td {{ border-bottom: 0; }}
    .id-cell {{
      width: 96px;
      min-width: 96px;
      white-space: nowrap;
    }}
    .timeline {{ display: grid; gap: 24px; }}
    .timeline-date-group {{
      display: grid;
      grid-template-columns: 112px minmax(0, 1fr);
      gap: 12px;
      align-items: start;
    }}
    .timeline-date-label {{
      position: relative;
      align-self: stretch;
      display: flex;
      justify-content: center;
      min-height: 100%;
    }}
    .timeline-date-label h3 {{
      position: relative;
      z-index: 1;
      margin: 0;
      display: inline-flex;
      align-items: center;
      height: 28px;
      border: 1px solid var(--accent-border);
      border-radius: 999px;
      background: var(--card-inner-bg);
      color: var(--accent);
      padding: 0 10px;
      font-size: 13px;
      font-weight: 700;
      white-space: nowrap;
    }}
    .timeline-date-group:not(:last-child) .timeline-date-label::after {{
      content: "";
      position: absolute;
      top: 34px;
      left: 50%;
      bottom: -22px;
      border-left: 2px dashed var(--accent-border);
      transform: translateX(-50%);
    }}
    .timeline-date-group:not(:last-child) .timeline-date-label::before {{
      content: "";
      position: absolute;
      left: 50%;
      top: 34px;
      width: 8px;
      height: 8px;
      border-left: 2px solid var(--accent-border);
      border-top: 2px solid var(--accent-border);
      transform: translateX(-50%) rotate(45deg);
    }}
    .timeline-date-items {{
      display: grid;
      gap: 14px;
      min-width: 0;
    }}
    .timeline-item {{
      display: grid;
      grid-template-columns: 76px minmax(0, 1fr);
      gap: 14px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--card-bg);
      padding: 16px;
    }}
    .timeline-time {{
      display: flex;
      align-items: flex-start;
      justify-content: center;
    }}
    .timeline-time time {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 52px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: var(--card-inner-bg);
      color: var(--muted);
      font-size: 12px;
      font-weight: 650;
      line-height: 1;
      padding: 6px 8px;
      white-space: nowrap;
    }}
    .timeline-body {{
      min-width: 0;
    }}
    .timeline-item h3 {{
      margin: 0;
      font-size: 15px;
      line-height: 1.45;
      overflow-wrap: anywhere;
    }}
    .timeline-details {{
      display: grid;
      gap: 10px;
      margin-top: 14px;
    }}
    .timeline-detail {{
      display: grid;
      grid-template-columns: 72px minmax(0, 1fr);
      gap: 10px;
      align-items: start;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--card-inner-bg);
      padding: 10px 12px;
      min-width: 0;
    }}
    .timeline-detail.body {{
      grid-template-columns: 1fr;
      background: var(--card-inner-bg);
    }}
    .timeline-detail.body span {{
      color: var(--accent);
      font-weight: 700;
    }}
    .timeline-detail span {{
      color: var(--muted);
      font-size: 12px;
      font-weight: 650;
      min-width: 0;
      overflow-wrap: anywhere;
      word-break: break-word;
    }}
    .timeline-detail p {{
      margin: 0;
      color: #1f2937;
      font-size: 13px;
      min-width: 0;
      overflow-wrap: anywhere;
      word-break: break-word;
    }}
    .timeline-detail.single {{
      grid-template-columns: 1fr;
    }}
    .empty {{
      color: var(--muted);
      background: var(--card-bg);
      border: 1px dashed var(--line);
      border-radius: 8px;
      padding: 18px;
      margin-bottom: 0;
      text-align: center;
    }}
    @media (max-width: 960px) {{
      .shell {{ padding: 14px; }}
      .hero-top {{ grid-template-columns: 1fr; }}
      .metrics {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .pipeline {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .pipeline-step::after {{ display: none; }}
      .page-layout, .page-layout.outline-collapsed {{ grid-template-columns: 1fr; }}
      .outline {{ position: static; max-height: none; }}
      .page-layout.outline-collapsed .outline-title,
      .page-layout.outline-collapsed .outline a {{
        display: block;
      }}
      .page-layout.outline-collapsed .outline-head {{
        justify-content: space-between;
        margin-bottom: 8px;
      }}
      .context-grid {{ grid-template-columns: 1fr; }}
      .todo-card {{ grid-template-columns: 1fr; }}
      .todo-type {{
        border-right: 0;
        border-bottom: 1px solid var(--line);
      }}
      .todo-main {{ padding: 14px; }}
      .todo-main {{
        display: grid;
        grid-template-columns: 1fr;
      }}
      .todo-action {{
        justify-content: flex-start;
        align-self: start;
      }}
      .todo-meta {{
        grid-template-columns: 1fr;
        gap: 8px;
      }}
      .todo-meta div {{
        min-height: 0;
      }}
      .todo-meta .todo-meta-text strong {{
        max-height: none;
        overflow: visible;
      }}
      .requirement-stats {{ grid-template-columns: 1fr; }}
      .requirement-card {{ grid-template-columns: 1fr; }}
      .task-card {{ grid-template-columns: 1fr; }}
      .task-checkpoints {{ grid-template-columns: 1fr; }}
      .record-grid {{ grid-template-columns: 1fr; }}
      .timeline-date-group {{ grid-template-columns: 1fr; }}
      .timeline-date-label {{ min-height: auto; }}
      .timeline-date-group:not(:last-child) .timeline-date-label::after,
      .timeline-date-group:not(:last-child) .timeline-date-label::before {{ display: none; }}
      .timeline-item {{ grid-template-columns: 1fr; }}
      .timeline-time {{ justify-content: flex-start; }}
      .timeline-detail {{ grid-template-columns: 1fr; gap: 4px; }}
      .section-heading {{ display: block; }}
      .section-heading p {{ text-align: left; margin-top: 4px; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <div class="page-layout" id="pageLayout">
      <aside class="outline" aria-label="页面大纲">
        <div class="outline-head">
          <span class="outline-title">页面大纲</span>
          <button class="outline-toggle" id="outlineToggle" type="button" aria-label="展开或收起大纲">‹</button>
        </div>
        <nav>
          <a href="#context">项目上下文</a>
          <a href="#todos">人工待办</a>
          <a href="#issues">待决策问题</a>
          <a href="#tasks">任务进展</a>
          <a href="#artifacts">阶段产物状态</a>
          <a href="#artifact-content">产物内容</a>
          <a href="#requirements">需求纳入决策</a>
          <a href="#revisions">用户修订</a>
          <a href="#decisions">决策归档</a>
          <a href="#journal">工作日志</a>
        </nav>
      </aside>

      <div class="main-column">
        <header class="hero">
          <div class="hero-top">
            <div>
              <h1>{esc(name)}</h1>
            </div>
            <div class="muted-text">生成时间<br><strong>{esc(generated_at)}</strong></div>
          </div>
          {render_pipeline(stage, next_step, pending_artifacts, open_issues)}
          <div class="metrics">
            {metric("待决策问题", str(open_issues), "", "#issues")}
            {metric("待处理修订", str(pending_revisions), "", "#revisions")}
            {metric("待审核/需修改产物", str(pending_artifacts), "", "#artifacts")}
          </div>
        </header>

        <main class="content-flow">
        <section class="panel" id="context">
          {section_heading("项目上下文", "先确认项目目标和基础资料，再处理下面的待办。")}
          {render_project_overview(root, context, requirements, platform, repo)}
        </section>

        <section class="panel primary" id="todos">
          {section_heading("人工待办", "优先处理这里的内容；它们通常会阻塞下一步推进。")}
          {render_action_queue(root, artifact_items, issues, revisions)}
        </section>

        <section class="panel" id="issues">
          {section_heading("待决策问题", "需要人工拍板的事项，优先级高于普通审核。")}
          {render_issues(issues)}
        </section>

        <section class="panel" id="tasks">
          {section_heading("任务进展", "按任务查看规格、实现报告和测试报告的生成与确认情况。")}
          {render_task_matrix(root, tasks)}
        </section>

        <section class="panel" id="artifacts">
          {section_heading("阶段产物状态", "按阶段查看产物审核状态；路径仅用于定位，不直接跳转。")}
          {render_artifact_board(root, artifact_items)}
        </section>

        <section class="panel" id="artifact-content">
          {section_heading("产物内容", "主要阶段产物的 HTML 预览；点击上方入口会跳到对应内容。")}
          {render_artifact_previews(root, artifact_items)}
        </section>

        <section class="panel" id="requirements">
          {section_heading("需求纳入决策", "需求是否纳入、暂不纳入或仍待决策。")}
          {render_requirements(requirements)}
        </section>

        <section class="panel" id="revisions">
          {section_heading("用户修订", "用户提出的修改意见和收敛状态。")}
          {render_revisions(revisions)}
        </section>

        <section class="panel" id="decisions">
          {section_heading("决策归档", "已解决的人工决策记录，低频查看。")}
          {render_timeline(changelog, "暂无决策归档。")}
        </section>

        <section class="panel" id="journal">
          {section_heading("工作日志", "wf 已经执行过的动作记录。")}
          {render_timeline(journal, "暂无日志。")}
        </section>
        </main>
      </div>
    </div>
  </div>
  <div class="diagram-viewer" id="diagramViewer" aria-hidden="true">
    <div class="diagram-viewer-toolbar">
      <div class="diagram-viewer-title">图表查看</div>
      <div class="diagram-viewer-actions">
        <button id="diagramZoomOut" type="button">-</button>
        <button id="diagramZoomReset" type="button">重置</button>
        <button id="diagramZoomIn" type="button">+</button>
        <button id="diagramClose" type="button">关闭</button>
      </div>
    </div>
    <div class="diagram-stage" id="diagramStage">
      <div class="diagram-canvas" id="diagramCanvas"></div>
    </div>
  </div>
  <script>
    const pageLayout = document.getElementById('pageLayout');
    const outlineToggle = document.getElementById('outlineToggle');
    outlineToggle.addEventListener('click', () => {{
      pageLayout.classList.toggle('outline-collapsed');
      outlineToggle.textContent = pageLayout.classList.contains('outline-collapsed') ? '›' : '‹';
    }});
    function openArtifactTarget() {{
      if (!location.hash) return;
      const target = document.querySelector(location.hash);
      if (target && target.matches('details.artifact-preview')) {{
        target.open = true;
      }}
    }}
    window.addEventListener('hashchange', openArtifactTarget);
    openArtifactTarget();

    const diagramViewer = document.getElementById('diagramViewer');
    const diagramStage = document.getElementById('diagramStage');
    const diagramCanvas = document.getElementById('diagramCanvas');
    const diagramClose = document.getElementById('diagramClose');
    const diagramZoomIn = document.getElementById('diagramZoomIn');
    const diagramZoomOut = document.getElementById('diagramZoomOut');
    const diagramZoomReset = document.getElementById('diagramZoomReset');
    const diagramState = {{ scale: 1, x: 0, y: 0, dragging: false, startX: 0, startY: 0, originX: 0, originY: 0 }};

    function applyDiagramTransform() {{
      diagramCanvas.style.transform = `translate(calc(-50% + ${{diagramState.x}}px), calc(-50% + ${{diagramState.y}}px)) scale(${{diagramState.scale}})`;
    }}

    function resetDiagramTransform() {{
      diagramState.scale = 1;
      diagramState.x = 0;
      diagramState.y = 0;
      applyDiagramTransform();
    }}

    function openDiagramViewer(source) {{
      const diagram = source.closest('.diagram-card')?.querySelector('.mermaid');
      if (!diagram) return;
      diagramCanvas.innerHTML = '';
      const rendered = diagram.querySelector('svg');
      diagramCanvas.appendChild((rendered || diagram).cloneNode(true));
      diagramViewer.classList.add('open');
      diagramViewer.setAttribute('aria-hidden', 'false');
      document.body.style.overflow = 'hidden';
      resetDiagramTransform();
    }}

    function closeDiagramViewer() {{
      diagramViewer.classList.remove('open');
      diagramViewer.setAttribute('aria-hidden', 'true');
      document.body.style.overflow = '';
      diagramCanvas.innerHTML = '';
    }}

    function zoomDiagram(delta) {{
      diagramState.scale = Math.min(4, Math.max(0.25, diagramState.scale + delta));
      applyDiagramTransform();
    }}

    document.querySelectorAll('.diagram-open').forEach((button) => {{
      button.addEventListener('click', () => openDiagramViewer(button));
    }});
    diagramClose.addEventListener('click', closeDiagramViewer);
    diagramZoomIn.addEventListener('click', () => zoomDiagram(0.2));
    diagramZoomOut.addEventListener('click', () => zoomDiagram(-0.2));
    diagramZoomReset.addEventListener('click', resetDiagramTransform);
    diagramStage.addEventListener('wheel', (event) => {{
      event.preventDefault();
      zoomDiagram(event.deltaY < 0 ? 0.12 : -0.12);
    }}, {{ passive: false }});
    diagramStage.addEventListener('pointerdown', (event) => {{
      diagramState.dragging = true;
      diagramState.startX = event.clientX;
      diagramState.startY = event.clientY;
      diagramState.originX = diagramState.x;
      diagramState.originY = diagramState.y;
      diagramStage.classList.add('dragging');
      diagramStage.setPointerCapture(event.pointerId);
    }});
    diagramStage.addEventListener('pointermove', (event) => {{
      if (!diagramState.dragging) return;
      diagramState.x = diagramState.originX + event.clientX - diagramState.startX;
      diagramState.y = diagramState.originY + event.clientY - diagramState.startY;
      applyDiagramTransform();
    }});
    diagramStage.addEventListener('pointerup', (event) => {{
      diagramState.dragging = false;
      diagramStage.classList.remove('dragging');
      diagramStage.releasePointerCapture(event.pointerId);
    }});
    diagramStage.addEventListener('pointercancel', () => {{
      diagramState.dragging = false;
      diagramStage.classList.remove('dragging');
    }});
    diagramViewer.addEventListener('click', (event) => {{
      if (event.target === diagramViewer) closeDiagramViewer();
    }});
    window.addEventListener('keydown', (event) => {{
      if (event.key === 'Escape' && diagramViewer.classList.contains('open')) closeDiagramViewer();
    }});
  </script>
  <script type="module">
    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
    mermaid.initialize({{
      startOnLoad: true,
      securityLevel: 'strict',
      theme: 'neutral'
    }});
  </script>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workspace", nargs="?", default=".")
    parser.add_argument("--output", help="output html path; defaults to <workspace>/dashboard.html")
    args = parser.parse_args()

    root = Path(args.workspace).resolve()
    output = Path(args.output).resolve() if args.output else root / "dashboard.html"
    output.write_text(render_dashboard(root), encoding="utf-8")
    print(f"rendered {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
