"""Generated human-readable views owned by the deterministic core."""

from __future__ import annotations

import html
from typing import Any

DASHBOARD_FILENAME = "dashboard.html"
STAGE_LABELS = {
    "analysis": "需求分析",
    "design": "技术设计",
    "specification": "规格生成",
    "implementation": "代码实现",
    "testing": "测试生成",
    "completed": "完成",
}
STAGES = tuple(STAGE_LABELS)


def render_memory(memory: dict[str, Any], decisions: dict[str, Any]) -> str:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in memory["items"]:
        if item["status"] == "active":
            grouped.setdefault(item["type"], []).append(item)

    lines = ["# Project Memory", ""]
    for memory_type in sorted(grouped):
        heading = " ".join(memory_type.splitlines())
        lines.extend((f"## {heading}", ""))
        for item in sorted(grouped[memory_type], key=lambda value: value["id"]):
            content = " ".join(item["content"].splitlines())
            lines.append(f"- [{item['id']}] {content} (source: {item['source']})")
        lines.append("")

    lines.extend(("## Confirmed Decisions", ""))
    if decisions["items"]:
        for decision in decisions["items"]:
            decision_text = " ".join(decision["decision"].splitlines())
            lines.append(
                f"- [{decision['id']}] {decision_text} "
                f"(question: {decision['question_id']})"
            )
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def render_dashboard(
    *,
    project: dict[str, Any],
    state: dict[str, Any],
    requirements: dict[str, Any],
    tasks: dict[str, Any],
    artifacts: dict[str, Any],
    questions: dict[str, Any],
    decisions: dict[str, Any],
    memory: dict[str, Any],
    events: list[dict[str, Any]],
    artifact_bodies: dict[str, str],
    next_action: str,
    health_issues: list[dict[str, Any]],
) -> str:
    stage_index = STAGES.index(state["current_stage"])
    stage_markup = []
    for index, stage in enumerate(STAGES):
        status = "done" if index < stage_index else "current" if index == stage_index else "future"
        stage_markup.append(
            f'<li class="stage {status}"><span>{index + 1}</span>{_escape(STAGE_LABELS[stage])}</li>'
        )

    requirement_rows = [
        (item["id"], item["title"], item["disposition"], ", ".join(item["sources"]))
        for item in requirements["items"]
    ]
    task_rows = [
        (
            item["id"],
            item["title"],
            item["status"],
            ", ".join(item["requirements"]),
            ", ".join(item["depends_on"]) or "-",
        )
        for item in tasks["items"]
    ]
    artifact_rows = [
        (
            item["id"],
            item["stage"],
            item["status"],
            str(item["revision"]),
            item["path"],
        )
        for item in artifacts["items"]
    ]
    open_questions = [item for item in questions["items"] if item["status"] == "open"]
    active_memory = [item for item in memory["items"] if item["status"] == "active"]

    previews = []
    for artifact in artifacts["items"]:
        body = artifact_bodies.get(artifact["id"], "Artifact content is unavailable.")
        previews.append(
            "<details>"
            f"<summary>{_escape(artifact['id'])} · r{artifact['revision']} · "
            f"{_escape(artifact['status'])}</summary>"
            f"<pre>{_escape(body)}</pre>"
            "</details>"
        )

    recent_events = list(reversed(events[-12:]))
    event_markup = "".join(
        "<li>"
        f"<strong>{_escape(event['type'])}</strong>"
        f"<span>{_escape(event['event_id'])} · {_escape(event['created_at'])}</span>"
        "</li>"
        for event in recent_events
    ) or '<li class="empty">暂无事件</li>'
    question_markup = "".join(
        "<li>"
        f"<strong>{_escape(item['id'])} · {_escape(item['question'])}</strong>"
        f"<span>{_escape(item['reason'])}</span>"
        "</li>"
        for item in open_questions
    ) or '<li class="empty">无阻塞问题</li>'
    decision_markup = "".join(
        "<li>"
        f"<strong>{_escape(item['id'])}</strong>"
        f"<span>{_escape(item['decision'])}</span>"
        "</li>"
        for item in reversed(decisions["items"])
    ) or '<li class="empty">暂无确认决策</li>'
    memory_markup = "".join(
        "<li>"
        f"<strong>{_escape(item['id'])} · {_escape(item['type'])}</strong>"
        f"<span>{_escape(item['content'])}</span>"
        "</li>"
        for item in active_memory
    ) or '<li class="empty">暂无长期记忆</li>'
    review_markup = "".join(
        f"<li><strong>{_escape(reference)}</strong></li>"
        for reference in state["pending_reviews"]
    ) or '<li class="empty">无待审核产物</li>'
    health_markup = "".join(
        "<li>"
        f"<strong>{_escape(item['type'])}</strong>"
        f"<span>{_escape(item['message'])}</span>"
        "</li>"
        for item in health_issues
    ) or '<li class="empty">未发现健康问题</li>'

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_escape(project['name'])} · AIWorkFlow</title>
<style>
:root {{ color-scheme: light; --ink:#17202a; --muted:#667085; --line:#d9dee7; --paper:#ffffff; --wash:#f4f6f8; --green:#147d64; --blue:#2463a8; --amber:#a15c00; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--wash); color:var(--ink); font:14px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; letter-spacing:0; }}
header {{ background:#17202a; color:#fff; padding:28px max(24px,calc((100vw - 1180px)/2)); }}
header h1 {{ margin:0 0 6px; font-size:24px; letter-spacing:0; }} header p {{ margin:0; color:#c7d0db; }}
main {{ max-width:1180px; margin:0 auto; padding:24px; }}
.summary {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:1px; border:1px solid var(--line); background:var(--line); }}
.metric {{ background:var(--paper); padding:16px; min-width:0; }} .metric b {{ display:block; font-size:22px; }} .metric span {{ color:var(--muted); }}
.pipeline {{ list-style:none; display:grid; grid-template-columns:repeat(6,minmax(0,1fr)); padding:0; margin:24px 0; border:1px solid var(--line); background:var(--paper); }}
.stage {{ padding:14px 10px; color:var(--muted); border-right:1px solid var(--line); white-space:normal; }} .stage:last-child {{ border:0; }}
.stage span {{ display:inline-grid; place-items:center; width:24px; height:24px; margin-right:7px; border:1px solid var(--line); border-radius:50%; }}
.stage.done {{ color:var(--green); }} .stage.current {{ color:var(--blue); font-weight:700; box-shadow:inset 0 -3px var(--blue); }}
.grid {{ display:grid; grid-template-columns:minmax(0,2fr) minmax(280px,1fr); gap:20px; align-items:start; }}
.action {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:1px; margin:0 0 20px; border:1px solid var(--line); background:var(--line); }}
.action div {{ min-width:0; padding:12px; background:var(--paper); }} .action b,.action span {{ display:block; overflow-wrap:anywhere; }} .action span {{ color:var(--muted); font-size:12px; }}
section {{ margin-bottom:20px; }} h2 {{ margin:0 0 10px; font-size:17px; }}
.panel {{ background:var(--paper); border:1px solid var(--line); padding:16px; }}
table {{ width:100%; border-collapse:collapse; background:var(--paper); }} th,td {{ text-align:left; vertical-align:top; padding:10px; border:1px solid var(--line); overflow-wrap:anywhere; }} th {{ background:#eef1f4; font-weight:600; }}
ul.list {{ list-style:none; margin:0; padding:0; }} .list li {{ padding:10px 0; border-bottom:1px solid var(--line); }} .list li:last-child {{ border:0; }} .list strong,.list span {{ display:block; overflow-wrap:anywhere; }} .list span {{ color:var(--muted); margin-top:3px; }}
details {{ background:var(--paper); border:1px solid var(--line); margin-bottom:8px; }} summary {{ cursor:pointer; padding:12px; font-weight:600; }} pre {{ margin:0; border-top:1px solid var(--line); padding:14px; overflow:auto; white-space:pre-wrap; overflow-wrap:anywhere; font:13px/1.55 ui-monospace,SFMono-Regular,Menlo,monospace; }}
.empty {{ color:var(--muted); }}
@media (max-width:800px) {{ main {{ padding:14px; }} .summary,.action {{ grid-template-columns:repeat(2,minmax(0,1fr)); }} .pipeline {{ grid-template-columns:repeat(2,minmax(0,1fr)); }} .stage {{ border-bottom:1px solid var(--line); }} .grid {{ grid-template-columns:1fr; }} table {{ display:block; overflow-x:auto; }} }}
</style>
</head>
<body>
<header><h1>{_escape(project['name'])}</h1><p>{_escape(project['platform'])} · {_escape(project['project_id'])} · {_escape(state['current_stage'])}/{_escape(state['mode'])}</p></header>
<main>
<div class="summary">
<div class="metric"><b>{len(requirements['items'])}</b><span>需求</span></div>
<div class="metric"><b>{len(tasks['items'])}</b><span>任务</span></div>
<div class="metric"><b>{len(artifacts['items'])}</b><span>产物</span></div>
<div class="metric"><b>{len(open_questions)}</b><span>阻塞问题</span></div>
</div>
<ol class="pipeline">{''.join(stage_markup)}</ol>
<div class="action">
<div><span>下一步</span><b>{_escape(next_action)}</b></div>
<div><span>当前任务</span><b>{_escape(state['active_item'] or '-')}</b></div>
<div><span>活动 Work</span><b>{_escape(state['active_work'] or '-')}</b></div>
<div><span>待审核</span><b>{len(state['pending_reviews'])}</b></div>
</div>
<div class="grid"><div>
<section><h2>需求追踪</h2>{_table(("ID","标题","状态","来源"), requirement_rows)}</section>
<section><h2>任务追踪</h2>{_table(("ID","标题","状态","需求","依赖"), task_rows)}</section>
<section><h2>产物</h2>{_table(("ID","阶段","状态","Revision","路径"), artifact_rows)}</section>
<section><h2>产物预览</h2>{''.join(previews) or '<div class="panel empty">暂无产物</div>'}</section>
</div><aside>
<section class="panel"><h2>阻塞问题</h2><ul class="list">{question_markup}</ul></section>
<section class="panel"><h2>待审核</h2><ul class="list">{review_markup}</ul></section>
<section class="panel"><h2>健康检查</h2><ul class="list">{health_markup}</ul></section>
<section class="panel"><h2>确认决策</h2><ul class="list">{decision_markup}</ul></section>
<section class="panel"><h2>长期记忆</h2><ul class="list">{memory_markup}</ul></section>
<section class="panel"><h2>最近事件</h2><ul class="list">{event_markup}</ul></section>
</aside></div>
</main>
</body>
</html>
"""


def _table(headers: tuple[str, ...], rows: list[tuple[str, ...]]) -> str:
    head = "".join(f"<th>{_escape(value)}</th>" for value in headers)
    if rows:
        body = "".join(
            "<tr>" + "".join(f"<td>{_escape(value)}</td>" for value in row) + "</tr>"
            for row in rows
        )
    else:
        body = f'<tr><td class="empty" colspan="{len(headers)}">暂无数据</td></tr>'
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _escape(value: Any) -> str:
    return html.escape(str(value), quote=True)
