"""Generated human-readable view of active project memory."""

from __future__ import annotations

from typing import Any


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
            if item["evidence"]:
                refs = ", ".join(
                    f"{evidence['path']}#{evidence['symbol']}"
                    for evidence in item["evidence"]
                )
                lines.append(f"  Evidence: {refs}")
            if item["rationale"]:
                lines.append(f"  Rationale: {' '.join(item['rationale'].splitlines())}")
            if item["validation"]:
                lines.append(f"  Validation: {' '.join(item['validation'].splitlines())}")
        lines.append("")

    lines.extend(("## Current Decisions", ""))
    current_decisions = [
        decision for decision in decisions["items"] if decision["status"] == "active"
    ]
    if current_decisions:
        for decision in current_decisions:
            decision_text = " ".join(decision["decision"].splitlines())
            lines.append(
                f"- [{decision['id']}] {decision_text} "
                f"(question: {decision['question_id']})"
            )
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)
