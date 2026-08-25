"""Generated human-readable views owned by the deterministic core."""

from __future__ import annotations

from typing import Any

DASHBOARD_FILENAME = "dashboard.html"


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
