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
from datetime import datetime
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

VALID_REVIEW = {"待审核", "需修改", "需更新", "已确认"}
REVIEW_RE = re.compile(r"^- 状态：(.+?)\s*$", re.MULTILINE)
REVIEW_FIELD_RE = re.compile(r"^- (状态|审核人|审核时间|修订来源)：(.*?)\s*$", re.MULTILINE)
TASK_RE = re.compile(r"\bT-\d{3}\b")
Q_RE = re.compile(r"\bQ-\d{3}\b")
R_RE = re.compile(r"\bR-\d{3}\b")
REQ_RE = re.compile(r"\bREQ-\d{3}\b")
PRD_RE = re.compile(r"\bPRD-\d{2}\b")
ISSUE_HEADING_RE = re.compile(r"(?m)^### (Q-\d{3})\b.*$")
REVISION_HEADING_RE = re.compile(r"(?m)^### (R-\d{3})\b.*$")
REQ_DETAIL_HEADING_RE = re.compile(r"(?m)^#### (REQ-\d{3})\b.*$")
TASK_DETAIL_HEADING_RE = re.compile(r"(?m)^### (T-\d{3})\b.*$")
SPEC_CHANGE_HEADING_RE = re.compile(r"(?m)^### 修改点 (\d+)：")
DEVIATION_HEADING_RE = re.compile(r"(?m)^### 偏离 (\d+)\b")
JOURNAL_DATE_RE = re.compile(r"^## (\d{4}-\d{2}-\d{2})\s*$")
JOURNAL_ENTRY_RE = re.compile(r"^### (\d{2}):(\d{2})\b")
DATE_HEADING_RE = re.compile(r"^## (\d{4}-\d{2}-\d{2})\s*$")
TIME_ENTRY_RE = re.compile(r"^### (\d{2}):(\d{2})\b")
CHANGELOG_ISSUE_TITLE_RE = re.compile(r"(?m)^### (Q-\d{3})\b")
TEST_REPORT_REQUIRED_SECTIONS = [
    "审核状态",
    "任务范围",
    "已生成单元测试",
    "未生成单元测试",
    "辅助验证记录",
    "结论",
]
TEST_REPORT_BLOCKING_STATUSES = {"阻塞", "待补充", "已生成，未通过"}
VALID_REQUIREMENT_DECISIONS = {"纳入", "暂不纳入", "待决策"}
DESIGN_REQUIRED_TASK_FIELDS = [
    "技术目标",
    "关联需求",
    "依赖",
    "模块架构",
    "接口/方法定义",
    "数据结构",
    "设计约束",
    "影响范围",
]
ACTION_IMPACT_ALIASES = {
    "design-solution": ["output/analysis.md", "analysis", "需求分析", "后续设计", "技术设计"],
    "generate-specs": [
        "output/analysis.md",
        "output/design.md",
        "analysis",
        "design",
        "需求分析",
        "技术方案",
        "技术设计",
        "规格生成",
    ],
    "implement-code": [
        "output/analysis.md",
        "output/design.md",
        "output/specs/",
        "analysis",
        "design",
        "spec",
        "需求分析",
        "技术方案",
        "规格",
        "实现",
        "T-",
    ],
    "generate-tests": [
        "output/specs/",
        "output/reports/",
        "output/design.md",
        "spec",
        "report",
        "规格",
        "代码报告",
        "实现报告",
        "测试",
        "T-",
    ],
}
ANALYSIS_UNRESOLVED_PATTERNS = [
    "待确认",
    "不明确",
    "是否",
    "可能",
    "以外部文档为准",
    "需产品确认",
    "需后端确认",
    "需埋点确认",
    "后续细化",
    "口径",
    "字段缺失",
    "范围不清",
]
DESIGN_VIEW_REASON_PATTERNS = [
    "不适用",
    "无代码仓库",
    "纯配置",
    "纯文案",
    "纯样式",
    "纯资源",
    "无法确定",
    "不涉及",
]
DESIGN_INTERFACE_BEHAVIOR_PATTERNS = [
    "兼容",
    "兜底",
    "异常",
    "幂等",
    "去重",
    "分支",
    "空参数",
    "无参",
    "返回空",
    "阈值",
    "状态切换",
    "重试",
    "降级",
]
DESIGN_INTERFACE_UNCHANGED_PATTERNS = [
    "未变化",
    "无变化",
    "无改动",
    "不改动",
    "复用现有",
    "调用现有",
    "已有接口",
]
DESIGN_INTERFACE_CHANGE_HINTS = [
    "新增",
    "修改",
    "变更",
    "调整",
    "改造",
    "签名",
    "职责变化",
]


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


def task_detail_blocks(text: str) -> list[tuple[str, str]]:
    body = section(text, "任务详情")
    matches = list(TASK_DETAIL_HEADING_RE.finditer(body))
    blocks: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        blocks.append((match.group(1), body[match.start() : end]))
    return blocks


def bold_field_block(block: str, label: str) -> str:
    pattern = rf"(?ms)^\*\*{re.escape(label)}：\*\*\s*\n(.*?)(?=\n\*\*[^*\n]+：\*\*|\n### |\Z)"
    match = re.search(pattern, block)
    return match.group(1).strip() if match else ""


def bold_field_exists(block: str, label: str) -> bool:
    return bool(re.search(rf"(?m)^\*\*{re.escape(label)}：\*\*", block))


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


def table_task_ids(text: str, heading: str) -> list[str]:
    body = section(text, heading)
    ids: list[str] = []
    for line in body.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and TASK_RE.fullmatch(cells[0]):
            ids.append(cells[0])
    return ids


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


def table_number_values(text: str, heading: str) -> list[str]:
    return [value for value in table_column_values(text, heading, 0) if value.isdigit()]


def table_first_column_values(text: str, heading: str) -> list[str]:
    return table_column_values(text, heading, 0)


def table_row_cells(text: str, heading: str) -> list[list[str]]:
    body = section(text, heading)
    rows: list[list[str]] = []
    for line in body.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not cells or cells[0] in {"ID", "任务", "#"} or set(cells[0]) <= {"-", " "}:
            continue
        rows.append(cells)
    return rows


def test_report_blocking_statuses(text: str) -> list[str]:
    statuses: list[str] = []
    for heading in ["已生成单元测试", "未生成单元测试"]:
        for cells in table_row_cells(text, heading):
            if len(cells) >= 5 and cells[4] in TEST_REPORT_BLOCKING_STATUSES:
                statuses.append(cells[4])
    return statuses


def review_status(path: Path) -> str | None:
    if not path.exists():
        return None
    match = REVIEW_RE.search(read_text(path))
    return match.group(1).strip() if match else None


def review_fields(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    return {key: value.strip() for key, value in REVIEW_FIELD_RE.findall(read_text(path))}


def parse_review_time(value: str) -> datetime | None:
    value = value.strip()
    if not value:
        return None
    for fmt in ["%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"]:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


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


def task_ids_from_artifacts(root: Path) -> list[str]:
    ids: set[str] = set(parse_design_tasks(root))
    for dirname in ["specs", "reports", "test-reports"]:
        for path in (root / "output" / dirname).glob("T-*.md"):
            ids.add(path.stem)
    return sorted(ids)


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


def id_number(item: str) -> int:
    return int(item.split("-", 1)[1])


def numeric_value(item: str) -> int:
    return int(item)


def section_has_placeholder_with_entries(text: str, heading: str, entry_pattern: re.Pattern[str]) -> bool:
    body = section(text, heading)
    return bool(entry_pattern.search(body) and re.search(r"(?m)^暂无\s*$", body))


def section_has_none_with_entries(text: str, heading: str, entry_pattern: re.Pattern[str]) -> bool:
    body = section(text, heading)
    return bool(entry_pattern.search(body) and re.search(r"(?m)^无\s*$", body))


def section_has_none_with_list_items(text: str, heading: str) -> bool:
    body = section(text, heading)
    return bool(re.search(r"(?m)^-\s+", body) and re.search(r"(?m)^无\s*$", body))


def table_has_placeholder_with_entries(text: str, heading: str) -> bool:
    values = table_first_column_values(text, heading)
    return "—" in values and any(value.isdigit() for value in values)


def has_heading(text: str, heading: str) -> bool:
    return bool(re.search(rf"(?m)^## {re.escape(heading)}\s*$", text))


def ordered_ids(path: Path, heading: str, pattern: re.Pattern[str]) -> list[str]:
    if not path.exists():
        return []
    return pattern.findall(section(read_text(path), heading))


def validate_ordered_items(
    issues: list[Issue],
    ids: list[str],
    file: str,
    typ: str,
    message: str,
    suggestion: str,
    *,
    level: str = "fail",
) -> None:
    if ids != sorted(ids, key=id_number):
        add(issues, level, typ, file, message, suggestion)


def validate_ordered_numbers(
    issues: list[Issue],
    ids: list[str],
    file: str,
    typ: str,
    message: str,
    suggestion: str,
    *,
    level: str = "fail",
) -> None:
    if ids != sorted(ids, key=numeric_value):
        add(issues, level, typ, file, message, suggestion)


def validate_date_archive(
    path: Path,
    root: Path,
    issues: list[Issue],
    *,
    name: str,
    empty_section_level: str = "warn",
    extra_entry_re: re.Pattern[str] | None = None,
) -> None:
    if not path.exists():
        return
    dates: list[str] = []
    current_date = ""
    entries_by_date: dict[str, list[tuple[int, int]]] = {}
    has_entries_by_date: dict[str, bool] = {}
    unexpected_entries = False
    for line in read_text(path).splitlines():
        date_match = DATE_HEADING_RE.match(line)
        if date_match:
            current_date = date_match.group(1)
            dates.append(current_date)
            entries_by_date.setdefault(current_date, [])
            has_entries_by_date.setdefault(current_date, False)
            continue
        entry_match = TIME_ENTRY_RE.match(line)
        if entry_match:
            if not current_date:
                unexpected_entries = True
                continue
            entries_by_date.setdefault(current_date, []).append((int(entry_match.group(1)), int(entry_match.group(2))))
            has_entries_by_date[current_date] = True
            continue
        if extra_entry_re and extra_entry_re.match(line):
            if not current_date:
                unexpected_entries = True
                continue
            has_entries_by_date[current_date] = True
    file = rel(path, root)
    if unexpected_entries:
        add(
            issues,
            "fail",
            f"{name}_entry_without_date",
            file,
            "存在未归属到日期标题下的归档条目",
            "将每条 ### HH:MM 归档放到对应 ## YYYY-MM-DD 日期章节下",
        )
    if len(dates) != len(set(dates)):
        add(
            issues,
            "fail",
            f"{name}_duplicate_date",
            file,
            "日期章节重复",
            "合并同一天的归档到唯一日期章节",
        )
    if dates != sorted(dates):
        add(
            issues,
            "fail",
            f"{name}_date_order_invalid",
            file,
            "日期章节必须按 YYYY-MM-DD 升序排列",
            "新日期只能追加到文件末尾；已有日期只在该日期章节内追加",
        )
    for date, entries in entries_by_date.items():
        if not has_entries_by_date.get(date):
            add(
                issues,
                empty_section_level,
                f"{name}_empty_date_section",
                file,
                f"{date} 日期章节没有任何条目",
                "不要在已有日期标题和其日志之间插入新日期；将空日期章节删除或补回对应条目",
            )
        if entries != sorted(entries):
            add(
                issues,
                "warn",
                f"{name}_time_order_invalid",
                file,
                f"{date} 日期章节内条目时间不是升序",
                "同一天的新条目应追加到该日期章节末尾",
            )


def validate_revisions_structure(root: Path, issues: list[Issue]) -> None:
    path = root / "REVISIONS.md"
    if not path.exists():
        return
    for heading in ["待处理", "已处理"]:
        ids = ordered_ids(path, heading, REVISION_HEADING_RE)
        validate_ordered_items(
            issues,
            ids,
            "REVISIONS.md",
            "revision_order_invalid",
            f"{heading} 修订条目必须按 R-XXX 升序排列",
            "按修订编号升序整理该章节，新增条目追加到正确编号位置",
        )
        if section_has_placeholder_with_entries(read_text(path), heading, REVISION_HEADING_RE):
            add(
                issues,
                "fail",
                "revision_placeholder_with_entries",
                "REVISIONS.md",
                f"{heading} 同时存在修订条目和“暂无”占位",
                "有条目时删除“暂无”；无条目时保留单独的“暂无”",
            )


def validate_journal_structure(root: Path, issues: list[Issue]) -> None:
    validate_date_archive(root / "JOURNAL.md", root, issues, name="journal", empty_section_level="fail")


def validate_issues_structure(root: Path, issues: list[Issue]) -> None:
    path = root / "ISSUES.md"
    if not path.exists():
        return
    text = read_text(path)
    for heading in ["分析阶段", "设计阶段", "实现阶段", "测试阶段"]:
        ids = ordered_ids(path, heading, ISSUE_HEADING_RE)
        validate_ordered_items(
            issues,
            ids,
            "ISSUES.md",
            "issue_order_invalid",
            f"{heading} 问题条目必须按 Q-XXX 升序排列",
            "新问题写入对应阶段中按编号升序的正确位置",
        )
        if section_has_placeholder_with_entries(text, heading, ISSUE_HEADING_RE):
            add(
                issues,
                "fail",
                "issue_placeholder_with_entries",
                "ISSUES.md",
                f"{heading} 同时存在问题条目和“暂无”占位",
                "有问题条目时删除“暂无”；无条目时保留单独的“暂无”",
            )


def validate_changelog_structure(root: Path, issues: list[Issue]) -> None:
    path = root / "CHANGELOG.md"
    validate_date_archive(
        path,
        root,
        issues,
        name="changelog",
        empty_section_level="warn",
        extra_entry_re=CHANGELOG_ISSUE_TITLE_RE,
    )
    if not path.exists():
        return
    for issue_id in CHANGELOG_ISSUE_TITLE_RE.findall(read_text(path)):
        add(
            issues,
            "fail",
            "changelog_invalid_entry_heading",
            "CHANGELOG.md",
            f"归档条目标题不能使用 {issue_id} 开头",
            f"改为 `### HH:MM — {{决策摘要}}（来自 ISSUES.md {issue_id}）`",
        )


def validate_analysis_structure(root: Path, issues: list[Issue]) -> None:
    path = root / "output" / "analysis.md"
    if not path.exists():
        return
    text = read_text(path)
    file = rel(path, root)
    table_ids = [match.group(0) for value in table_column_values(text, "功能需求", 0) if (match := REQ_RE.fullmatch(value))]
    detail_ids = REQ_DETAIL_HEADING_RE.findall(section(text, "功能需求"))
    validate_ordered_items(
        issues,
        table_ids,
        file,
        "analysis_requirement_table_order_invalid",
        "需求纳入决策表必须按 REQ-XXX 升序排列",
        "新增需求行按编号插入，不要插到表格顶部",
        level="warn",
    )
    validate_ordered_items(
        issues,
        detail_ids,
        file,
        "analysis_requirement_detail_order_invalid",
        "需求详情必须按 REQ-XXX 升序排列",
        "新增需求详情按编号插入，不要插到详情顶部",
        level="warn",
    )
    prd_ids = [match.group(0) for value in table_column_values(text, "文件清单", 0) if (match := PRD_RE.fullmatch(value))]
    validate_ordered_items(
        issues,
        prd_ids,
        file,
        "analysis_prd_file_order_invalid",
        "PRD 文件清单必须按 PRD-XX 升序排列",
        "按文件名顺序分配 PRD 编号，并按编号升序列出",
        level="warn",
    )
    validate_analysis_requirement_decisions(text, file, review_status(path), issues)
    validate_analysis_unresolved_phrases(text, file, issues)


def validate_analysis_requirement_decisions(
    text: str,
    file: str,
    status: str | None,
    issues: list[Issue],
) -> None:
    unresolved: list[str] = []
    invalid: list[str] = []
    for cells in table_row_cells(text, "功能需求"):
        if len(cells) < 5 or not REQ_RE.fullmatch(cells[0]):
            continue
        decision = cells[4].strip()
        if not decision or decision == "待决策":
            unresolved.append(cells[0])
        elif decision not in VALID_REQUIREMENT_DECISIONS:
            invalid.append(f"{cells[0]}={decision}")
    if status == "已确认" and unresolved:
        add(
            issues,
            "fail",
            "analysis_confirmed_with_unresolved_requirement_decisions",
            file,
            f"需求分析已确认，但需求纳入决策表仍有未完成决策：{', '.join(unresolved)}",
            "用户确认前必须将每条需求处理方式填写为 `纳入` 或 `暂不纳入`；`待决策` 需求需先写入并处理 ISSUES.md",
        )
    if status == "已确认" and invalid:
        add(
            issues,
            "fail",
            "analysis_confirmed_with_invalid_requirement_decisions",
            file,
            f"需求分析已确认，但需求纳入决策表存在非法处理方式：{', '.join(invalid)}",
            "处理方式只能是 `纳入`、`暂不纳入` 或 `待决策`；确认前不得保留非法值",
        )


def validate_analysis_unresolved_phrases(text: str, file: str, issues: list[Issue]) -> None:
    body = "\n".join(section(text, heading) for heading in ["需求概要", "功能需求"])
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped or Q_RE.search(stripped):
            continue
        matched = [pattern for pattern in ANALYSIS_UNRESOLVED_PATTERNS if pattern in stripped]
        if not matched:
            continue
        add(
            issues,
            "warn",
            "analysis_unresolved_phrase",
            file,
            f"需求分析正文疑似包含未决策内容：{stripped[:80]}",
            "将影响后续设计、规格或实现的存疑点写入 ISSUES.md，并在正文中只引用对应 Q-XXX",
        )
        return


def validate_design_structure(root: Path, issues: list[Issue]) -> None:
    path = root / "output" / "design.md"
    if not path.exists():
        return
    text = read_text(path)
    file = rel(path, root)
    table_ids = [match.group(0) for value in table_column_values(text, "任务总览", 0) if (match := TASK_RE.fullmatch(value))]
    detail_ids = TASK_DETAIL_HEADING_RE.findall(section(text, "任务详情"))
    validate_ordered_items(
        issues,
        table_ids,
        file,
        "design_task_table_order_invalid",
        "任务总览必须按 T-XXX 升序排列",
        "新增任务行按编号插入，不要插到表格顶部",
        level="warn",
    )
    validate_ordered_items(
        issues,
        detail_ids,
        file,
        "design_task_detail_order_invalid",
        "任务详情必须按 T-XXX 升序排列",
        "新增任务详情按编号插入，不要插到详情顶部",
        level="warn",
    )
    validate_design_view(text, file, issues)
    validate_design_task_detail_fields(text, file, review_status(path), issues)
    validate_design_interface_definitions(text, file, issues)


def validate_design_view(text: str, file: str, issues: list[Issue]) -> None:
    body = section(text, "设计视图")
    if not body:
        add(
            issues,
            "warn",
            "design_view_missing",
            file,
            "技术方案缺少设计视图",
            "按 contracts/design.md 增加 `## 设计视图`，提供 Mermaid 图或明确不适用原因",
        )
        return
    has_mermaid_block = bool(re.search(r"(?ms)^```mermaid\s*\n.+?\n```", body))
    has_reason = any(pattern in body for pattern in DESIGN_VIEW_REASON_PATTERNS)
    if "mermaid" in body.lower() and not has_mermaid_block:
        add(
            issues,
            "warn",
            "design_view_mermaid_fence_invalid",
            file,
            "设计视图中的 Mermaid 图未使用合法 fenced code block",
            "使用 ```mermaid 开始、``` 结束，确保 dashboard.html 可以渲染图形",
        )
    if not has_mermaid_block and not has_reason:
        add(
            issues,
            "warn",
            "design_view_without_mermaid_or_reason",
            file,
            "设计视图缺少 Mermaid 图或明确不适用原因",
            "补充任务依赖图、类关系图、交互图等 Mermaid 图；确实不适用时写明原因",
        )


def validate_design_task_detail_fields(text: str, file: str, status: str | None, issues: list[Issue]) -> None:
    level = "fail" if status == "已确认" else "warn"
    missing_type = "design_confirmed_missing_required_task_field" if status == "已确认" else "design_missing_required_task_field"
    legacy_type = "design_uses_legacy_requirement_summary"
    for task_id, block in task_detail_blocks(text):
        missing = [field for field in DESIGN_REQUIRED_TASK_FIELDS if not bold_field_exists(block, field)]
        if missing:
            add(
                issues,
                level,
                missing_type,
                file,
                f"{task_id} 任务详情缺少必需字段：{', '.join(missing)}",
                "按 contracts/design.md 补齐技术目标、关联需求、依赖、模块架构、接口/方法定义、数据结构、设计约束和影响范围",
            )
        if bold_field_exists(block, "需求摘要"):
            add(
                issues,
                level,
                legacy_type,
                file,
                f"{task_id} 任务详情仍使用旧字段：需求摘要",
                "将 `需求摘要` 改为 `技术目标`，只描述本任务可验证的技术结果",
            )


def validate_design_interface_definitions(text: str, file: str, issues: list[Issue]) -> None:
    for task_id, block in task_detail_blocks(text):
        body = bold_field_block(block, "接口/方法定义")
        if not body:
            continue
        for line in body.splitlines():
            stripped = line.strip()
            if not stripped or stripped in {"无", "- 无", "暂无", "- 暂无"}:
                continue
            if any(pattern in stripped for pattern in DESIGN_INTERFACE_BEHAVIOR_PATTERNS):
                add(
                    issues,
                    "warn",
                    "design_interface_contains_behavior_detail",
                    file,
                    f"{task_id} 的接口/方法定义疑似包含行为规则：{stripped[:80]}",
                    "接口/方法定义只保留本次需求新增、修改、签名变化或职责变化的文件、签名、职责、入参和出参；分支、兼容、兜底、异常、幂等、去重等写入模块架构、数据结构或设计约束",
                )
                return
            has_unchanged_marker = any(pattern in stripped for pattern in DESIGN_INTERFACE_UNCHANGED_PATTERNS)
            has_change_hint = any(pattern in stripped for pattern in DESIGN_INTERFACE_CHANGE_HINTS)
            if has_unchanged_marker and not has_change_hint:
                add(
                    issues,
                    "warn",
                    "design_interface_contains_unchanged_item",
                    file,
                    f"{task_id} 的接口/方法定义疑似列入未变化接口：{stripped[:80]}",
                    "接口/方法定义只列本次需求相关且有变化的接口/方法；未变化的既有接口、复用调用和上下游依赖放入模块架构或影响范围说明",
                )
                return


def validate_stage_artifact_structure(root: Path, issues: list[Issue]) -> None:
    validate_analysis_structure(root, issues)
    validate_design_structure(root, issues)
    for spec in sorted((root / "output" / "specs").glob("T-*.md")):
        ids = SPEC_CHANGE_HEADING_RE.findall(read_text(spec))
        validate_ordered_numbers(
            issues,
            ids,
            rel(spec, root),
            "spec_change_order_invalid",
            "规格修改点必须按序号升序排列",
            "新增修改点追加到末尾并使用下一个序号",
            level="warn",
        )
    for report in sorted((root / "output" / "reports").glob("T-*.md")):
        text = read_text(report)
        ids = DEVIATION_HEADING_RE.findall(text)
        change_ids = table_number_values(text, "修改清单")
        validate_ordered_numbers(
            issues,
            change_ids,
            rel(report, root),
            "code_report_change_list_order_invalid",
            "修改清单序号必须按升序排列",
            "新增修改记录追加到表格末尾并使用下一个序号",
            level="warn",
        )
        validate_ordered_numbers(
            issues,
            ids,
            rel(report, root),
            "code_report_deviation_order_invalid",
            "偏离条目必须按序号升序排列",
            "新增偏离追加到末尾并使用下一个序号",
            level="warn",
        )
        if section_has_none_with_entries(text, "偏离说明", DEVIATION_HEADING_RE):
            add(
                issues,
                "fail",
                "code_report_deviation_none_with_entries",
                rel(report, root),
                "偏离说明同时存在“无”和偏离条目",
                "无偏离时只写“无”；存在偏离条目时删除“无”",
            )
    for report in sorted((root / "output" / "test-reports").glob("T-*.md")):
        text = read_text(report)
        file = rel(report, root)
        if not re.search(r"(?m)^# 单元测试报告 — T-\d{3}\b", text):
            add(
                issues,
                "fail",
                "test_report_title_invalid",
                file,
                "测试报告标题必须使用“# 单元测试报告 — T-XXX {任务标题}”",
                "按 contracts/test-report.md 更新测试报告标题",
            )
        for heading in TEST_REPORT_REQUIRED_SECTIONS:
            if not has_heading(text, heading):
                add(
                    issues,
                    "fail",
                    "test_report_missing_section",
                    file,
                    f"测试报告缺少章节：{heading}",
                    "按 contracts/test-report.md 补齐单元测试报告结构",
                )
        for heading, typ, message in [
            ("已生成单元测试", "test_report_generated_order_invalid", "已生成单元测试序号必须按升序排列"),
            ("未生成单元测试", "test_report_not_generated_order_invalid", "未生成单元测试序号必须按升序排列"),
            ("辅助验证记录", "test_report_verification_order_invalid", "辅助验证记录序号必须按升序排列"),
        ]:
            ids = table_number_values(text, heading)
            validate_ordered_numbers(
                issues,
                ids,
                file,
                typ,
                message,
                "新增条目追加到表格末尾并使用下一个序号",
                level="warn",
            )
            if table_has_placeholder_with_entries(text, heading):
                add(
                    issues,
                    "fail",
                    "test_report_placeholder_with_entries",
                    file,
                    f"{heading} 同时存在占位行和真实条目",
                    "存在真实条目时删除 `—` 占位行",
                )
        legacy_sections = [heading for heading in ["测试清单", "未覆盖行为"] if has_heading(text, heading)]
        if legacy_sections:
            add(
                issues,
                "fail",
                "test_report_legacy_section",
                file,
                f"测试报告仍使用旧章节：{', '.join(legacy_sections)}",
                "改为 `已生成单元测试`、`未生成单元测试`、`辅助验证记录` 和 `结论`",
            )
        blocking_statuses = test_report_blocking_statuses(text)
        if review_status(report) == "已确认" and blocking_statuses:
            add(
                issues,
                "fail",
                "test_report_confirmed_with_blocking_status",
                file,
                f"测试报告已确认但仍存在阻塞或未通过状态：{', '.join(sorted(set(blocking_statuses)))}",
                "先通过修订或决策流程收敛测试报告，再确认测试完成",
            )


def add_stale_downstream_issue(root: Path, issues: list[Issue], upstream: Path, downstream: Path, reason: str) -> None:
    add(
        issues,
        "fail",
        "stale_downstream_artifact",
        rel(downstream, root),
        f"{rel(downstream, root)} 已确认，但上游 {rel(upstream, root)} {reason}",
        "运行 wf/tools/invalidate_downstream.py 标记下游产物为需更新，并重建 CONTEXT.md",
    )


def downstream_is_stale(root: Path, upstream: Path, downstream: Path) -> str:
    upstream_status = review_status(upstream)
    downstream_status = review_status(downstream)
    if downstream_status != "已确认" or not upstream.exists() or not downstream.exists():
        return ""
    if upstream_status != "已确认":
        return f"当前状态为 {upstream_status or '未设置'}"
    upstream_time = parse_review_time(review_fields(upstream).get("审核时间", ""))
    downstream_time = parse_review_time(review_fields(downstream).get("审核时间", ""))
    if upstream_time and downstream_time and upstream_time > downstream_time:
        return "审核时间晚于下游产物"
    return ""


def validate_downstream_freshness(root: Path, issues: list[Issue]) -> None:
    output = root / "output"
    for task_id in task_ids_from_artifacts(root):
        spec = output / "specs" / f"{task_id}.md"
        report = report_path(root, task_id)
        test_report = test_report_path(root, task_id)
        for downstream in [report, test_report]:
            reason = downstream_is_stale(root, spec, downstream)
            if reason:
                add_stale_downstream_issue(root, issues, spec, downstream, reason)
        reason = downstream_is_stale(root, report, test_report)
        if reason:
            add_stale_downstream_issue(root, issues, report, test_report, reason)


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


def issue_impacts_action(root: Path, action: str | None, impact: str, context_stage: str) -> bool:
    if action in {None, "resolve-decision", "fix-workspace", "status"}:
        return False
    if context_stage == "blocked_by_decision":
        return True
    aliases = list(ACTION_IMPACT_ALIASES.get(action, []))
    if action == "review-artifact":
        aliases.extend(item.split("（", 1)[0] for item in pending_artifacts(root))
    normalized = impact.lower()
    return any(alias and alias.lower() in normalized for alias in aliases)


def validate_open_issues(root: Path, issues: list[Issue], action: str | None, context_stage: str) -> None:
    for qid, block in issue_blocks(root):
        if issue_resolved(block):
            continue
        title = block.splitlines()[0].strip("# ").strip() if block.splitlines() else qid
        impact = issue_field(block, "影响")
        direct = issue_impacts_action(root, action, impact, context_stage)
        add(
            issues,
            "fail" if direct else "warn",
            "blocking_open_issue" if direct else "open_issue",
            "ISSUES.md",
            f"存在待决策问题：{title}",
            "先处理对应 Q-XXX，再推进当前动作" if direct else "处理对应 Q-XXX 后再推进受影响的下游动作",
        )


def validate(root: Path, action: str | None = None, target: str | None = None) -> dict:
    issues: list[Issue] = []
    required = ["CONTEXT.md", "AGENT.md", "ISSUES.md", "REVISIONS.md", "JOURNAL.md", "CHANGELOG.md"]
    for item in required:
        if not (root / item).exists():
            add(issues, "fail", "missing_workspace_file", item, f"缺少 {item}", "补齐工作空间文件后重新执行 wf")
    for item in ["prd", "output", "output/specs", "output/reports", "output/test-reports"]:
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
        spec_ids = [item.split(" ", 1)[0] for item in parse_list_block(context, "规格") if TASK_RE.match(item)]
        validate_ordered_items(
            issues,
            spec_ids,
            "CONTEXT.md",
            "context_spec_order_invalid",
            "CONTEXT.md 规格索引必须按 T-XXX 升序排列",
            "执行 rebuild-context 重建状态快照",
        )
        code_ids = table_task_ids(context, "代码产出")
        validate_ordered_items(
            issues,
            code_ids,
            "CONTEXT.md",
            "context_code_output_order_invalid",
            "CONTEXT.md 代码产出表必须按 T-XXX 升序排列",
            "执行 rebuild-context 重建状态快照",
        )
        test_ids = table_task_ids(context, "测试记录")
        validate_ordered_items(
            issues,
            test_ids,
            "CONTEXT.md",
            "context_test_record_order_invalid",
            "CONTEXT.md 测试记录表必须按 T-XXX 升序排列",
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
    validate_issues_structure(root, issues)
    validate_revisions_structure(root, issues)
    validate_journal_structure(root, issues)
    validate_changelog_structure(root, issues)
    if action != "resolve-decision":
        validate_open_issues(root, issues, action, stage)
    validate_stage_artifact_structure(root, issues)
    validate_downstream_freshness(root, issues)

    tasks = parse_design_tasks(root)
    for task_id in tasks:
        spec = root / "output" / "specs" / f"{task_id}.md"
        if not spec.exists():
            add(issues, "warn", "missing_spec", rel(spec, root), f"{task_id} 缺少规格文件")

    context_done = parse_table_tasks(context, "代码产出")
    for task_id, value in context_done.items():
        if "已完成" in value:
            report = report_path(root, task_id)
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
            test_report = test_report_path(root, task_id)
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
            spec = output / "specs" / f"{task_id}.md"
            report = report_path(root, task_id)
            test_report = test_report_path(root, task_id)
            if review_status(report) == "已确认" and review_status(test_report) != "已确认":
                if review_status(spec) != "已确认":
                    add(
                        issues,
                        "fail",
                        "missing_confirmed_spec_for_tests",
                        rel(spec, root),
                        f"{task_id} 已实现但规格不存在或未确认，不能生成测试",
                        "先生成并确认对应规格，再执行 generate-tests",
                    )
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
