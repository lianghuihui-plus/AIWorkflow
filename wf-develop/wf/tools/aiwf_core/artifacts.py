"""Artifact paths, result manifests, indexes, and dependency invalidation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .model import (
    AIWorkflowError,
    ID_PATTERNS,
    MEMORY_OPERATIONS,
    REQUIREMENT_DISPOSITIONS,
    SCHEMA_VERSION,
    fail_schema,
    next_id,
    require_list,
    require_mapping,
    require_string,
    require_string_list,
)

ARTIFACT_TYPES = (
    "analysis",
    "design",
    "specification",
    "implementation_report",
    "test_report",
)
STAGE_ARTIFACT_TYPES = {
    "analysis": "analysis",
    "design": "design",
    "specification": "specification",
    "implementation": "implementation_report",
    "testing": "test_report",
}


def sha256_content(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def semantic_result_hash(result: dict[str, Any]) -> str:
    ignored = {"artifact_id", "artifact_type", "revision"}
    semantic = {key: value for key, value in result.items() if key not in ignored}
    payload = json.dumps(
        semantic,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256_content(payload)


def artifact_identity(stage: str, active_item: str | None) -> tuple[str, str, str]:
    if stage == "analysis":
        return "analysis", "analysis", "artifacts/analysis.md"
    if stage == "design":
        return "design", "design", "artifacts/design.md"
    if active_item is None or not ID_PATTERNS["task"].fullmatch(active_item):
        raise AIWorkflowError(
            code="invalid_active_item",
            message=f"Stage '{stage}' requires a task id.",
            exit_code=4,
        )
    if stage == "specification":
        return f"{active_item}-spec", "specification", f"artifacts/specs/{active_item}.md"
    if stage == "implementation":
        return (
            f"{active_item}-implementation",
            "implementation_report",
            f"artifacts/reports/{active_item}.md",
        )
    if stage == "testing":
        return f"{active_item}-test", "test_report", f"artifacts/tests/{active_item}.md"
    raise AIWorkflowError(
        code="invalid_stage",
        message=f"Stage '{stage}' cannot produce an artifact.",
        exit_code=4,
    )


def result_schema(stage: str) -> dict[str, Any]:
    string = {"type": "string", "minLength": 1}
    string_array = {"type": "array", "items": string, "uniqueItems": True}
    memory_delta = {
        "type": "array",
        "items": {
            "type": "object",
            "required": ["operation", "type", "content"],
            "properties": {
                "operation": {"enum": list(MEMORY_OPERATIONS)},
                "type": string,
                "content": string,
                "target_id": {"type": ["string", "null"], "pattern": r"^M-\d{3,}$"},
            },
            "allOf": [
                {
                    "if": {
                        "properties": {"operation": {"const": "add"}},
                        "required": ["operation"],
                    },
                    "then": {"properties": {"target_id": {"type": "null"}}},
                    "else": {
                        "required": ["target_id"],
                        "properties": {
                            "target_id": {
                                "type": "string",
                                "pattern": r"^M-\d{3,}$",
                            }
                        },
                    },
                }
            ],
            "additionalProperties": False,
        },
    }
    properties: dict[str, Any] = {
        "schema_version": {"const": SCHEMA_VERSION},
        "stage": {"const": stage},
        "memory_delta": memory_delta,
    }
    required = ["schema_version", "stage", "memory_delta"]
    if stage == "analysis":
        properties["requirements"] = {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["title", "summary", "sources", "disposition"],
                "properties": {
                    "id": {"type": ["string", "null"], "pattern": r"^REQ-\d{3,}$"},
                    "title": string,
                    "summary": string,
                    "sources": string_array,
                    "disposition": {"enum": ["proposed", "deferred"]},
                },
                "additionalProperties": False,
            },
        }
        required.append("requirements")
    elif stage == "design":
        properties["tasks"] = {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["key", "title", "requirements", "depends_on"],
                "properties": {
                    "key": string,
                    "id": {"type": ["string", "null"], "pattern": r"^T-\d{3,}$"},
                    "title": string,
                    "requirements": string_array,
                    "depends_on": string_array,
                },
                "additionalProperties": False,
            },
        }
        required.append("tasks")
    elif stage == "specification":
        properties["task_id"] = {"type": "string", "pattern": r"^T-\d{3,}$"}
        required.append("task_id")
    elif stage == "implementation":
        properties.update(
            {
                "task_id": {"type": "string", "pattern": r"^T-\d{3,}$"},
                "changed_files": string_array,
                "validation_summary": {"type": "string"},
            }
        )
        required.extend(("task_id", "changed_files", "validation_summary"))
    elif stage == "testing":
        properties.update(
            {
                "task_id": {"type": "string", "pattern": r"^T-\d{3,}$"},
                "test_files": string_array,
                "execution": {
                    "type": "object",
                    "required": ["command", "exit_code", "summary"],
                    "properties": {
                        "command": {"type": ["string", "null"]},
                        "exit_code": {"type": ["integer", "null"]},
                        "summary": {"type": "string"},
                    },
                    "additionalProperties": False,
                },
                "uncovered": string_array,
            }
        )
        required.extend(("task_id", "test_files", "execution", "uncovered"))
    else:
        raise AIWorkflowError(
            code="invalid_stage",
            message=f"Stage '{stage}' has no result schema.",
            exit_code=4,
        )
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": required,
        "properties": properties,
        "additionalProperties": False,
    }


def result_template(stage: str, active_item: str | None) -> dict[str, Any]:
    template: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "stage": stage,
        "memory_delta": [],
    }
    if stage == "analysis":
        template["requirements"] = []
    elif stage == "design":
        template["tasks"] = []
    elif stage == "specification":
        template["task_id"] = active_item
    elif stage == "implementation":
        template.update(
            {"task_id": active_item, "changed_files": [], "validation_summary": ""}
        )
    elif stage == "testing":
        template.update(
            {
                "task_id": active_item,
                "test_files": [],
                "execution": {"command": None, "exit_code": None, "summary": ""},
                "uncovered": [],
            }
        )
    else:
        result_schema(stage)
    return template


def validate_result_manifest(stage: str, value: Any, *, active_item: str | None) -> dict[str, Any]:
    document = f"{stage} result manifest"
    data = require_mapping(value, document)
    if data.get("schema_version") != SCHEMA_VERSION:
        fail_schema(document, "unsupported schema_version")
    if data.get("stage") != stage:
        fail_schema(document, f"stage must be '{stage}'")
    _validate_memory_delta(data.get("memory_delta"), document)

    if stage == "analysis":
        _validate_requirement_results(data.get("requirements"), document)
    elif stage == "design":
        _validate_task_results(data.get("tasks"), document)
    elif stage == "specification":
        _validate_task_id(data.get("task_id"), active_item, document)
    elif stage == "implementation":
        _validate_task_id(data.get("task_id"), active_item, document)
        require_string_list(data.get("changed_files"), document, "changed_files")
        require_string(data.get("validation_summary"), document, "validation_summary", empty=True)
    elif stage == "testing":
        _validate_task_id(data.get("task_id"), active_item, document)
        require_string_list(data.get("test_files"), document, "test_files")
        execution = require_mapping(data.get("execution"), document)
        command = execution.get("command")
        if command is not None and not isinstance(command, str):
            fail_schema(document, "execution.command must be a string or null")
        exit_code = execution.get("exit_code")
        if exit_code is not None and not isinstance(exit_code, int):
            fail_schema(document, "execution.exit_code must be an integer or null")
        require_string(execution.get("summary"), document, "execution.summary", empty=True)
        require_string_list(data.get("uncovered"), document, "uncovered")
    else:
        fail_schema(document, f"unsupported stage '{stage}'")
    return data


def reconcile_requirements(
    current: dict[str, Any],
    result: dict[str, Any],
    *,
    revision: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    existing = {item["id"]: dict(item) for item in current["items"]}
    used_ids: set[str] = set()
    normalized_results: list[dict[str, Any]] = []
    known_ids = list(existing)

    for raw_item in result["requirements"]:
        item = dict(raw_item)
        item_id = item.get("id")
        if item_id is None:
            item_id = next_id("requirement", known_ids)
            known_ids.append(item_id)
        elif item_id not in existing:
            raise AIWorkflowError(
                code="unknown_requirement_id",
                message="Existing requirement ids must be provided by prepare.",
                exit_code=4,
                details={"id": item_id},
            )
        if item_id in used_ids:
            raise AIWorkflowError(
                code="duplicate_requirement_id",
                message="Requirement id appears more than once in the result manifest.",
                exit_code=4,
                details={"id": item_id},
            )
        used_ids.add(item_id)
        normalized = {
            "id": item_id,
            "title": item["title"],
            "summary": item["summary"],
            "disposition": item.get("disposition", "proposed"),
            "sources": list(item["sources"]),
            "origin_revision": revision,
        }
        existing[item_id] = normalized
        normalized_results.append(dict(normalized))

    for item_id, item in existing.items():
        if item_id not in used_ids:
            item["disposition"] = "withdrawn"

    normalized_manifest = dict(result)
    normalized_manifest["requirements"] = normalized_results
    index = {"schema_version": SCHEMA_VERSION, "items": sorted(existing.values(), key=lambda item: item["id"])}
    return index, normalized_manifest


def reconcile_tasks(
    current: dict[str, Any],
    requirements: dict[str, Any],
    result: dict[str, Any],
    *,
    revision: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    existing = {item["id"]: dict(item) for item in current["items"]}
    requirement_ids = {
        item["id"]
        for item in requirements["items"]
        if item["disposition"] == "accepted"
    }
    known_ids = list(existing)
    used_ids: set[str] = set()
    key_to_id: dict[str, str] = {}

    for raw_item in result["tasks"]:
        item_id = raw_item.get("id")
        if item_id is None:
            item_id = next_id("task", known_ids)
            known_ids.append(item_id)
        elif item_id not in existing:
            raise AIWorkflowError(
                code="unknown_task_id",
                message="Existing task ids must be provided by prepare.",
                exit_code=4,
                details={"id": item_id},
            )
        if item_id in used_ids:
            raise AIWorkflowError(
                code="duplicate_task_id",
                message="Task id appears more than once in the result manifest.",
                exit_code=4,
                details={"id": item_id},
            )
        used_ids.add(item_id)
        key_to_id[raw_item["key"]] = item_id

    normalized_results: list[dict[str, Any]] = []
    for raw_item in result["tasks"]:
        item_id = key_to_id[raw_item["key"]]
        unknown_requirements = sorted(set(raw_item["requirements"]) - requirement_ids)
        if unknown_requirements:
            raise AIWorkflowError(
                code="unknown_requirement_reference",
                message="Task references unavailable requirements.",
                exit_code=4,
                details={"ids": unknown_requirements},
            )
        dependencies: list[str] = []
        for dependency in raw_item["depends_on"]:
            dependency_id = key_to_id.get(dependency, dependency)
            if dependency_id not in used_ids:
                raise AIWorkflowError(
                    code="unknown_task_dependency",
                    message="Task dependency must remain active in the current design revision.",
                    exit_code=4,
                    details={"dependency": dependency},
                )
            dependencies.append(dependency_id)
        normalized = {
            "id": item_id,
            "title": raw_item["title"],
            "requirements": list(raw_item["requirements"]),
            "depends_on": dependencies,
            "status": "proposed",
            "origin_revision": revision,
        }
        existing[item_id] = normalized
        normalized_results.append({**normalized, "key": raw_item["key"]})

    for item_id, item in existing.items():
        if item_id not in used_ids:
            item["status"] = "withdrawn"
    _validate_dependency_graph(existing)

    normalized_manifest = dict(result)
    normalized_manifest["tasks"] = normalized_results
    index = {"schema_version": SCHEMA_VERSION, "items": sorted(existing.values(), key=lambda item: item["id"])}
    return index, normalized_manifest


def find_artifact(artifacts: dict[str, Any], artifact_id: str) -> dict[str, Any] | None:
    return next((item for item in artifacts["items"] if item["id"] == artifact_id), None)


def replace_artifact(artifacts: dict[str, Any], artifact: dict[str, Any]) -> dict[str, Any]:
    items = [dict(item) for item in artifacts["items"] if item["id"] != artifact["id"]]
    items.append(artifact)
    items.sort(key=lambda item: item["id"])
    return {"schema_version": SCHEMA_VERSION, "items": items}


def invalidate_downstream(
    artifacts: dict[str, Any],
    *,
    artifact_id: str,
    revision: int,
) -> tuple[dict[str, Any], list[str]]:
    items = [dict(item) for item in artifacts["items"]]
    invalidated: list[str] = []
    frontier = {f"{artifact_id}@{revision}"}
    while frontier:
        next_frontier: set[str] = set()
        for item in items:
            if item["id"] == artifact_id or item["status"] == "stale":
                continue
            if frontier.intersection(item["depends_on"]):
                item["status"] = "stale"
                invalidated.append(item["id"])
                next_frontier.add(f"{item['id']}@{item['revision']}")
        frontier = next_frontier
    return {"schema_version": SCHEMA_VERSION, "items": items}, invalidated


def verify_artifact_integrity(root: Path, artifact: dict[str, Any]) -> None:
    checks = (
        (artifact["path"], artifact["content_sha256"]),
        (artifact["result_path"], artifact["result_sha256"]),
        (artifact["work_path"], artifact["work_sha256"]),
    )
    for relative_path, expected_hash in checks:
        relative = Path(relative_path)
        path = (root / relative).resolve(strict=False)
        if relative.is_absolute() or ".." in relative.parts or not path.is_relative_to(root.resolve()):
            raise AIWorkflowError(
                code="artifact_drift",
                message="Registered artifact path resolves outside the workspace.",
                exit_code=7,
                details={"artifact_id": artifact["id"], "path": relative_path},
            )
        try:
            actual_hash = sha256_content(path.read_bytes())
        except OSError as error:
            raise AIWorkflowError(
                code="artifact_drift",
                message="Registered artifact file is missing.",
                exit_code=7,
                details={"artifact_id": artifact["id"], "path": relative_path},
            ) from error
        if actual_hash != expected_hash:
            raise AIWorkflowError(
                code="artifact_drift",
                message="Registered artifact content changed outside the workflow.",
                exit_code=7,
                details={"artifact_id": artifact["id"], "path": relative_path},
            )


def _validate_requirement_results(value: Any, document: str) -> None:
    items = require_list(value, document, "requirements")
    for raw_item in items:
        item = require_mapping(raw_item, document)
        item_id = item.get("id")
        if item_id is not None and (
            not isinstance(item_id, str) or not ID_PATTERNS["requirement"].fullmatch(item_id)
        ):
            fail_schema(document, "requirement id must be a valid REQ id or null")
        require_string(item.get("title"), document, "title")
        require_string(item.get("summary"), document, "summary")
        require_string_list(item.get("sources"), document, "sources")
        disposition = item.get("disposition", "proposed")
        if disposition not in {"proposed", "deferred"}:
            fail_schema(document, f"invalid submitted disposition '{disposition}'")


def _validate_task_results(value: Any, document: str) -> None:
    items = require_list(value, document, "tasks")
    if not items:
        fail_schema(document, "tasks must contain at least one executable task")
    keys: set[str] = set()
    for raw_item in items:
        item = require_mapping(raw_item, document)
        key = require_string(item.get("key"), document, "key")
        if key in keys:
            fail_schema(document, f"duplicate task key '{key}'")
        keys.add(key)
        item_id = item.get("id")
        if item_id is not None and (
            not isinstance(item_id, str) or not ID_PATTERNS["task"].fullmatch(item_id)
        ):
            fail_schema(document, "task id must be a valid task id or null")
        require_string(item.get("title"), document, "title")
        require_string_list(item.get("requirements"), document, "requirements")
        require_string_list(item.get("depends_on"), document, "depends_on")


def _validate_memory_delta(value: Any, document: str) -> None:
    items = require_list(value, document, "memory_delta")
    for raw_item in items:
        item = require_mapping(raw_item, document)
        operation = item.get("operation")
        if operation not in MEMORY_OPERATIONS:
            fail_schema(document, f"invalid memory operation '{operation}'")
        require_string(item.get("type"), document, "memory type")
        require_string(item.get("content"), document, "memory content")
        target_id = item.get("target_id")
        if operation == "add" and target_id is not None:
            fail_schema(document, "add memory operation cannot have target_id")
        if operation != "add" and (
            not isinstance(target_id, str) or not ID_PATTERNS["memory"].fullmatch(target_id)
        ):
            fail_schema(document, f"{operation} memory operation requires target_id")


def _validate_task_id(value: Any, active_item: str | None, document: str) -> None:
    task_id = require_string(value, document, "task_id")
    if task_id != active_item:
        fail_schema(document, "task_id must match the active item")


def _validate_dependency_graph(tasks: dict[str, dict[str, Any]]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str) -> None:
        if task_id in visited:
            return
        if task_id in visiting:
            raise AIWorkflowError(
                code="task_dependency_cycle",
                message="Task dependency graph contains a cycle.",
                exit_code=4,
                details={"task_id": task_id},
            )
        visiting.add(task_id)
        for dependency in tasks[task_id]["depends_on"]:
            if dependency in tasks:
                visit(dependency)
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in tasks:
        visit(task_id)
