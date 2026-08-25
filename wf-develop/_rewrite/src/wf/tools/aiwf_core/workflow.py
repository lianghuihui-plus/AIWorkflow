"""Deterministic workflow operations over the workspace store."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Mapping, Sequence

from .artifacts import (
    artifact_identity,
    find_artifact,
    invalidate_downstream,
    reconcile_requirements,
    reconcile_tasks,
    replace_artifact,
    semantic_result_hash,
    sha256_content,
    validate_result_manifest,
    verify_artifact_integrity,
)
from .context import build_work, copy_successor_work, validate_work
from .initialization import prepare_initialization
from .model import AIWorkflowError, CommandRequest, SCHEMA_VERSION, next_id, now_iso
from .render import render_memory
from .repository import inspect_repository
from .review import advance_after_approval, apply_memory_delta, approve_indexes
from .storage import WorkspaceStore, json_bytes, sha256_bytes


class WorkflowEngine:
    def __init__(self, workspace: Path | str) -> None:
        self.store = WorkspaceStore(workspace)

    def bootstrap(self, project: Mapping[str, Any]) -> None:
        self.store.bootstrap(project)

    def initialize(
        self,
        *,
        name: str,
        platform: str,
        prd_paths: Sequence[str],
        code_repository: str | None = None,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        prepared = prepare_initialization(
            workspace=self.store.root,
            name=name,
            platform=platform,
            prd_paths=prd_paths,
            code_repository=code_repository,
            project_id=project_id,
        )
        self.store.bootstrap(prepared.project, prd_files=prepared.prd_files)
        return self.inspect()

    def recover(self) -> list[str]:
        with self.store.lock(exclusive=True):
            return self.store.recover_locked()

    def prepare_work(
        self,
        *,
        goal: str | None = None,
        active_item: str | None = None,
        inputs: Sequence[str] | None = None,
        depends_on: Sequence[str] = (),
        sources: Sequence[str] | None = None,
        stage_guide: str | None = None,
        constraints: Sequence[str] | None = None,
        instruction: str = "",
    ) -> dict[str, Any]:
        with self.store.lock(exclusive=True):
            self.store.recover_locked()
            state = self.store.read_json("state.json")
            if state["mode"] == "working":
                return self._read_work(
                    state["active_work"],
                    expected_hash=state["active_work_sha256"],
                )
            if state["mode"] != "ready" or state["current_stage"] == "completed":
                raise AIWorkflowError(
                    code="invalid_state_transition",
                    message="Current workflow state cannot prepare work.",
                    exit_code=6,
                    details={"stage": state["current_stage"], "mode": state["mode"]},
                )

            stage = state["current_stage"]
            facts: dict[str, Any] | None = None
            repository_context: dict[str, Any] | None = None
            if goal is None:
                active_item = self._default_active_item(stage, active_item)
                defaults = self._default_work_context(
                    stage,
                    active_item=active_item,
                    instruction=instruction,
                )
                goal = defaults["goal"]
                inputs = defaults["inputs"]
                depends_on = defaults["depends_on"]
                sources = defaults["sources"]
                stage_guide = defaults["stage_guide"]
                constraints = defaults["constraints"]
                facts = defaults.get("facts")
                repository_context = defaults.get("repository_context")
            inputs = list(inputs or ())
            sources = list(sources or ())
            constraints = list(constraints or ())
            stage_guide = stage_guide or ""
            self._validate_active_item(stage, active_item)
            self._validate_dependencies(depends_on)
            for path in [*inputs, *sources]:
                self.store.safe_path(path)

            work_id = self._next_work_id()
            work = build_work(
                work_id=work_id,
                stage=stage,
                active_item=active_item,
                goal=goal,
                inputs=list(inputs),
                depends_on=list(depends_on),
                sources=list(sources),
                stage_guide=stage_guide,
                constraints=list(constraints),
                facts=facts,
                repository_context=repository_context,
            )
            updated_state = dict(state)
            work_bytes = json_bytes(work)
            updated_state.update(
                {
                    "mode": "working",
                    "active_item": active_item,
                    "active_work": work_id,
                    "active_work_sha256": sha256_content(work_bytes),
                    "updated_at": now_iso(),
                }
            )
            changes: dict[str, bytes | None] = {
                self._work_path(work_id, "work.json"): work_bytes,
                ".aiwf/state.json": json_bytes(updated_state),
            }

            artifact = find_artifact(self.store.read_json("artifacts.json"), work["artifact"]["id"])
            if artifact is not None:
                if artifact["status"] == "approved":
                    raise AIWorkflowError(
                        code="artifact_already_approved",
                        message="Approved artifacts require an explicit revision request.",
                        exit_code=6,
                        details={"artifact_id": artifact["id"]},
                    )
                verify_artifact_integrity(self.store.root, artifact)
                changes[work["draft_output"]] = self.store.safe_path(artifact["path"]).read_bytes()
                changes[work["result_output"]] = self.store.safe_path(artifact["result_path"]).read_bytes()

            request_digest = self._digest({"work": work})
            self.store.commit_locked(
                changes,
                event_type="work_prepared",
                event_data={"work_id": work_id, "stage": stage, "active_item": active_item},
                command_key=f"prepare:{work_id}",
                request_digest=request_digest,
            )
            return work

    def _default_active_item(self, stage: str, requested: str | None) -> str | None:
        if stage in {"analysis", "design"}:
            if requested is not None:
                raise AIWorkflowError(
                    code="invalid_active_item",
                    message=f"Stage '{stage}' does not accept a task id.",
                    exit_code=4,
                )
            return None
        if stage == "implementation":
            return self._next_implementation_task(requested)
        if stage == "testing":
            return self._next_testing_task(requested)
        if stage != "specification":
            return requested
        tasks = self.store.read_json("tasks.json")["items"]
        eligible = [item for item in tasks if item["status"] in {"planned", "stale"}]
        if requested is not None:
            if not any(item["id"] == requested for item in eligible):
                raise AIWorkflowError(
                    code="task_not_ready",
                    message="Requested task is not ready for specification.",
                    exit_code=6,
                    details={"id": requested, "stage": stage},
                )
            return requested
        if not eligible:
            raise AIWorkflowError(
                code="no_pending_task",
                message="No task is ready for specification.",
                exit_code=6,
                details={"stage": stage},
            )
        return min(item["id"] for item in eligible)

    def _next_implementation_task(self, requested: str | None) -> str:
        tasks = self.store.read_json("tasks.json")["items"]
        by_id = {item["id"]: item for item in tasks}
        eligible = [
            item
            for item in tasks
            if item["status"] in {"in_progress", "stale"}
            and all(
                by_id[dependency]["status"] in {"implemented", "tested"}
                for dependency in item["depends_on"]
            )
        ]
        return self._select_task(eligible, requested, stage="implementation")

    def _next_testing_task(self, requested: str | None) -> str:
        tasks = self.store.read_json("tasks.json")["items"]
        eligible = [item for item in tasks if item["status"] in {"implemented", "stale"}]
        return self._select_task(eligible, requested, stage="testing")

    def _select_task(
        self,
        eligible: Sequence[dict[str, Any]],
        requested: str | None,
        *,
        stage: str,
    ) -> str:
        if requested is not None:
            if not any(item["id"] == requested for item in eligible):
                raise AIWorkflowError(
                    code="task_not_ready",
                    message=f"Requested task is not ready for {stage}.",
                    exit_code=6,
                    details={"id": requested, "stage": stage},
                )
            return requested
        if not eligible:
            raise AIWorkflowError(
                code="no_pending_task",
                message=f"No task is ready for {stage}.",
                exit_code=6,
                details={"stage": stage},
            )
        return min(item["id"] for item in eligible)

    def _default_work_context(
        self,
        stage: str,
        *,
        active_item: str | None,
        instruction: str,
    ) -> dict[str, Any]:
        project = self.store.read_json("project.json")
        if stage == "analysis":
            context = {
                "goal": "理解全部 PRD，形成可审核并能支撑技术设计的整体需求分析。",
                "inputs": [
                    ".aiwf/project.json",
                    *project["prd_files"],
                    ".aiwf/requirements.json",
                ],
                "sources": list(project["prd_files"]),
                "depends_on": [],
                "stage_guide": "references/stages/analysis.md",
                "constraints": [
                    "区分已知事实、合理推断和待用户决策事项。",
                    "只有缺少答案会阻止安全推进时才创建阻塞问题。",
                    "只写任务包指定的草稿和结果文件。",
                ],
            }
        elif stage == "design":
            analysis = self._approved_artifact("analysis")
            context = {
                "goal": "基于已确认需求形成可实施的整体技术设计与任务拆分。",
                "inputs": [
                    ".aiwf/project.json",
                    ".aiwf/requirements.json",
                    analysis["path"],
                ],
                "sources": [analysis["path"]],
                "depends_on": [f"analysis@{analysis['approved_revision']}"],
                "stage_guide": "references/stages/design.md",
                "constraints": [
                    "设计必须引用已确认需求，不重新解释或扩大业务范围。",
                    "任务拆分表达实现边界和依赖，不预写机械测试步骤。",
                    "只写任务包指定的草稿和结果文件。",
                ],
            }
        elif stage == "specification":
            analysis = self._approved_artifact("analysis")
            design = self._approved_artifact("design")
            task = next(
                item
                for item in self.store.read_json("tasks.json")["items"]
                if item["id"] == active_item
            )
            context = {
                "goal": f"为 {task['id']}（{task['title']}）生成可直接指导实现的任务规格。",
                "inputs": [analysis["path"], design["path"]],
                "sources": [analysis["path"], design["path"]],
                "depends_on": [
                    f"analysis@{analysis['approved_revision']}",
                    f"design@{design['approved_revision']}",
                ],
                "stage_guide": "references/stages/specification.md",
                "facts": self._task_facts(task),
                "constraints": [
                    "规格范围不得超出当前 active item。",
                    "明确行为与边界，但不规定测试代码的具体实现。",
                    "只写任务包指定的草稿和结果文件。",
                ],
            }
        elif stage == "implementation":
            design = self._approved_artifact("design")
            specification = self._approved_artifact(f"{active_item}-spec")
            task = self._task(active_item)
            dependency_artifacts = [
                self._approved_artifact(f"{dependency}-implementation")
                for dependency in task["depends_on"]
            ]
            context = {
                "goal": f"按照已批准规格实现 {task['id']}（{task['title']}），并记录实际验证结果。",
                "inputs": [specification["path"], design["path"]],
                "sources": [specification["path"], design["path"]],
                "depends_on": [
                    f"{specification['id']}@{specification['approved_revision']}",
                    *[
                        f"{artifact['id']}@{artifact['approved_revision']}"
                        for artifact in dependency_artifacts
                    ],
                ],
                "stage_guide": "references/stages/implementation.md",
                "facts": self._task_facts(task),
                "repository_context": inspect_repository(project["code_repository"]),
                "constraints": [
                    "保护任务开始前已经存在的代码仓库改动。",
                    "只处理当前 active item，不提交或清理版本控制状态。",
                    "只写任务包指定的报告草稿、结果文件和任务范围内代码。",
                ],
            }
        elif stage == "testing":
            specification = self._approved_artifact(f"{active_item}-spec")
            implementation = self._approved_artifact(f"{active_item}-implementation")
            task = self._task(active_item)
            context = {
                "goal": f"基于真实实现为 {task['id']}（{task['title']}）补充并执行必要测试。",
                "inputs": [specification["path"], implementation["path"]],
                "sources": [implementation["path"], specification["path"]],
                "depends_on": [
                    f"{implementation['id']}@{implementation['approved_revision']}"
                ],
                "stage_guide": "references/stages/testing.md",
                "facts": self._task_facts(task),
                "repository_context": inspect_repository(project["code_repository"]),
                "constraints": [
                    "测试设计基于真实实现和仓库现有测试模式。",
                    "保护任务开始前已经存在的代码仓库改动。",
                    "只写任务包指定的报告草稿、结果文件和任务范围内代码。",
                ],
            }
        else:
            raise AIWorkflowError(
                code="stage_not_implemented",
                message=f"Automatic task context for stage '{stage}' is not connected yet.",
                exit_code=3,
                details={"stage": stage, "phase": 6},
            )
        goal = context["goal"]
        if instruction.strip():
            goal = f"{goal} 当前用户补充要求：{instruction.strip()}"
        return {**context, "goal": goal}

    def _task(self, task_id: str | None) -> dict[str, Any]:
        task = next(
            (
                item
                for item in self.store.read_json("tasks.json")["items"]
                if item["id"] == task_id
            ),
            None,
        )
        if task is None:
            raise AIWorkflowError(
                code="unknown_task_id",
                message="Task does not exist.",
                exit_code=4,
                details={"id": task_id},
            )
        return task

    def _task_facts(self, task: dict[str, Any]) -> dict[str, Any]:
        requirement_by_id = {
            item["id"]: item for item in self.store.read_json("requirements.json")["items"]
        }
        return {
            "task": task,
            "requirements": [requirement_by_id[item_id] for item_id in task["requirements"]],
        }

    def _approved_artifact(self, artifact_id: str) -> dict[str, Any]:
        artifact = find_artifact(self.store.read_json("artifacts.json"), artifact_id)
        if (
            artifact is None
            or artifact["status"] != "approved"
            or artifact["approved_revision"] is None
        ):
            raise AIWorkflowError(
                code="unavailable_dependency",
                message="Required upstream artifact is not approved.",
                exit_code=6,
                details={"artifact_id": artifact_id},
            )
        verify_artifact_integrity(self.store.root, artifact)
        return artifact

    def submit_work(self, work_id: str) -> dict[str, Any]:
        command_key = f"submit:{work_id}"
        with self.store.lock(exclusive=True):
            self.store.recover_locked()
            existing_event = self.store.find_event(command_key)
            if existing_event is not None:
                shutil.rmtree(self.store.data_root / "work" / work_id, ignore_errors=True)
                return dict(existing_event["data"])
            if self.store.find_event(f"question:{work_id}") is not None:
                raise AIWorkflowError(
                    code="work_already_terminated",
                    message="Blocked work cannot be submitted.",
                    exit_code=6,
                    details={"work_id": work_id},
                )

            state = self.store.read_json("state.json")
            if state["mode"] != "working" or state["active_work"] != work_id:
                raise AIWorkflowError(
                    code="invalid_state_transition",
                    message="Only the active work can be submitted.",
                    exit_code=6,
                    details={"work_id": work_id},
                )
            work = self._read_work(work_id, expected_hash=state["active_work_sha256"])
            draft_path = self.store.safe_path(work["draft_output"])
            result_path = self.store.safe_path(work["result_output"])
            try:
                draft_bytes = draft_path.read_bytes()
                raw_result_bytes = result_path.read_bytes()
                raw_result = json.loads(raw_result_bytes.decode("utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
                raise AIWorkflowError(
                    code="incomplete_work",
                    message="Work draft and result manifest must both be valid files.",
                    exit_code=4,
                    details={"work_id": work_id},
                ) from error
            if not draft_bytes.strip():
                raise AIWorkflowError(
                    code="incomplete_work",
                    message="Semantic artifact draft cannot be empty.",
                    exit_code=4,
                    details={"work_id": work_id},
                )

            result = validate_result_manifest(
                work["stage"], raw_result, active_item=work["active_item"]
            )
            requirements = self.store.read_json("requirements.json")
            tasks = self.store.read_json("tasks.json")
            artifacts = self.store.read_json("artifacts.json")
            artifact_id = work["artifact"]["id"]
            current_artifact = find_artifact(artifacts, artifact_id)
            if current_artifact is not None:
                verify_artifact_integrity(self.store.root, current_artifact)
            revision = 1 if current_artifact is None else current_artifact["revision"] + 1

            if work["stage"] == "analysis":
                requirements, result = reconcile_requirements(
                    requirements, result, revision=revision
                )
            elif work["stage"] == "design":
                tasks, result = reconcile_tasks(
                    tasks, requirements, result, revision=revision
                )
            result = {
                **result,
                "artifact_id": artifact_id,
                "artifact_type": work["artifact"]["type"],
                "revision": revision,
                "depends_on": list(work["depends_on"]),
                "sources": list(work["sources"]),
            }
            normalized_result_bytes = json_bytes(result)
            work_snapshot_bytes = json_bytes(work)

            invalidated: list[str] = []
            semantic_changed = False
            if current_artifact is not None:
                current_result = self.store.read_json_path(current_artifact["result_path"])
                semantic_changed = semantic_result_hash(current_result) != semantic_result_hash(result)
            if (
                current_artifact is not None
                and current_artifact["approved_revision"] is not None
                and (
                    current_artifact["content_sha256"] != sha256_content(draft_bytes)
                    or semantic_changed
                )
            ):
                artifacts, invalidated = invalidate_downstream(
                    artifacts,
                    artifact_id=artifact_id,
                    revision=current_artifact["approved_revision"],
                )
                tasks = self._mark_tasks_stale(tasks, invalidated, work["stage"])

            timestamp = now_iso()
            registered = {
                "id": artifact_id,
                "type": work["artifact"]["type"],
                "stage": work["stage"],
                "active_item": work["active_item"],
                "path": work["artifact"]["output"],
                "result_path": f".aiwf/results/{artifact_id}/{revision}.json",
                "work_path": f".aiwf/history/{artifact_id}/{revision}.work.json",
                "content_sha256": sha256_content(draft_bytes),
                "result_sha256": sha256_content(normalized_result_bytes),
                "work_sha256": sha256_content(work_snapshot_bytes),
                "status": "review",
                "revision": revision,
                "approved_revision": (
                    current_artifact["approved_revision"] if current_artifact is not None else None
                ),
                "depends_on": list(work["depends_on"]),
                "sources": list(work["sources"]),
                "updated_at": timestamp,
            }
            artifacts = replace_artifact(artifacts, registered)
            reviewed_ref = f"{artifact_id}@{revision}"
            updated_state = dict(state)
            updated_state.update(
                {
                    "mode": "review",
                    "active_work": None,
                    "active_work_sha256": None,
                    "pending_reviews": [reviewed_ref],
                    "blocking_questions": [],
                    "updated_at": timestamp,
                }
            )
            changes: dict[str, bytes | None] = {
                ".aiwf/requirements.json": json_bytes(requirements),
                ".aiwf/tasks.json": json_bytes(tasks),
                ".aiwf/artifacts.json": json_bytes(artifacts),
                ".aiwf/state.json": json_bytes(updated_state),
                registered["path"]: draft_bytes,
                registered["result_path"]: normalized_result_bytes,
                registered["work_path"]: work_snapshot_bytes,
            }
            if current_artifact is not None:
                changes[
                    f".aiwf/history/{artifact_id}/{current_artifact['revision']}.md"
                ] = self.store.safe_path(current_artifact["path"]).read_bytes()

            request_digest = sha256_bytes(draft_bytes + b"\0" + raw_result_bytes)
            additional_events: list[tuple[str, Mapping[str, Any]]] = []
            if invalidated:
                additional_events.append(
                    (
                        "downstream_invalidated",
                        {"source": reviewed_ref, "artifacts": invalidated},
                    )
                )
            event = self.store.commit_locked(
                changes,
                event_type="artifact_submitted",
                event_data={
                    "work_id": work_id,
                    "artifact_id": artifact_id,
                    "revision": revision,
                    "invalidated": invalidated,
                },
                command_key=command_key,
                request_digest=request_digest,
                additional_events=additional_events,
            )
            shutil.rmtree(self.store.data_root / "work" / work_id, ignore_errors=True)
            return dict(event["data"])

    def review_artifact(
        self,
        artifact_id: str,
        revision: int,
        *,
        outcome: str,
        feedback: str = "",
    ) -> dict[str, Any]:
        if outcome == "changes_requested":
            return self._request_changes(
                artifact_id,
                revision,
                feedback=feedback,
                command_prefix="review",
            )
        if outcome != "approved":
            raise AIWorkflowError(
                code="invalid_review_outcome",
                message="Review outcome must be approved or changes_requested.",
                exit_code=4,
            )
        command_key = f"review:{artifact_id}@{revision}:approved"
        request_digest = self._digest(
            {"artifact_id": artifact_id, "revision": revision, "outcome": outcome}
        )
        with self.store.lock(exclusive=True):
            self.store.recover_locked()
            existing_event = self.store.find_event(command_key)
            if existing_event is not None:
                return dict(existing_event["data"])
            self._reject_conflicting_review(artifact_id, revision, command_key)
            state = self.store.read_json("state.json")
            artifacts = self.store.read_json("artifacts.json")
            artifact = find_artifact(artifacts, artifact_id)
            reviewed_ref = f"{artifact_id}@{revision}"
            if (
                artifact is None
                or artifact["revision"] != revision
                or artifact["status"] != "review"
                or reviewed_ref not in state["pending_reviews"]
            ):
                raise AIWorkflowError(
                    code="invalid_state_transition",
                    message="Artifact revision is not awaiting review.",
                    exit_code=6,
                    details={"artifact_id": artifact_id, "revision": revision},
                )
            verify_artifact_integrity(self.store.root, artifact)
            result = self.store.read_json_path(artifact["result_path"])
            memory = apply_memory_delta(
                self.store.read_json("memory.json"),
                result["memory_delta"],
                source=reviewed_ref,
            )
            requirements, tasks = approve_indexes(
                stage=artifact["stage"],
                revision=revision,
                active_item=artifact["active_item"],
                requirements=self.store.read_json("requirements.json"),
                tasks=self.store.read_json("tasks.json"),
            )
            approved_artifact = dict(artifact)
            approved_artifact.update(
                {
                    "status": "approved",
                    "approved_revision": revision,
                    "updated_at": now_iso(),
                }
            )
            artifacts = replace_artifact(artifacts, approved_artifact)
            updated_state, stage_advanced = advance_after_approval(
                state,
                artifacts,
                tasks,
                stage=artifact["stage"],
                reviewed_ref=reviewed_ref,
            )
            decisions = self.store.read_json("decisions.json")
            changes = {
                ".aiwf/artifacts.json": json_bytes(artifacts),
                ".aiwf/requirements.json": json_bytes(requirements),
                ".aiwf/tasks.json": json_bytes(tasks),
                ".aiwf/memory.json": json_bytes(memory),
                ".aiwf/memory.md": render_memory(memory, decisions).encode("utf-8"),
                ".aiwf/state.json": json_bytes(updated_state),
            }
            additional_events: list[tuple[str, Mapping[str, Any]]] = []
            if stage_advanced:
                additional_events.append(
                    (
                        "stage_advanced",
                        {
                            "from": state["current_stage"],
                            "to": updated_state["current_stage"],
                        },
                    )
                )
            event = self.store.commit_locked(
                changes,
                event_type="artifact_approved",
                event_data={
                    "artifact_id": artifact_id,
                    "revision": revision,
                    "stage": artifact["stage"],
                    "current_stage": updated_state["current_stage"],
                },
                command_key=command_key,
                request_digest=request_digest,
                additional_events=additional_events,
            )
            return dict(event["data"])

    def request_revision(self, artifact_id: str, *, feedback: str) -> dict[str, Any]:
        with self.store.lock(exclusive=False):
            if self.store.has_pending_transactions():
                raise AIWorkflowError(
                    code="needs_recovery",
                    message="Workspace has an incomplete transaction.",
                    exit_code=6,
                )
            artifact = find_artifact(self.store.read_json("artifacts.json"), artifact_id)
            if artifact is None:
                raise AIWorkflowError(
                    code="unknown_artifact",
                    message="Cannot revise an unknown artifact.",
                    exit_code=4,
                    details={"artifact_id": artifact_id},
                )
            revision = artifact["revision"]
        return self._request_changes(
            artifact_id,
            revision,
            feedback=feedback,
            command_prefix="revise",
        )

    def open_questions(
        self,
        work_id: str,
        questions: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        command_key = f"question:{work_id}"
        request_digest = self._digest({"questions": list(questions)})
        with self.store.lock(exclusive=True):
            self.store.recover_locked()
            existing_event = self.store.find_event(command_key)
            if existing_event is not None:
                if existing_event["request_digest"] != request_digest:
                    raise AIWorkflowError(
                        code="idempotency_conflict",
                        message="Question set changed for an already terminated work.",
                        exit_code=6,
                    )
                return dict(existing_event["data"])
            if self.store.find_event(f"submit:{work_id}") is not None:
                raise AIWorkflowError(
                    code="work_already_terminated",
                    message="Submitted work cannot open blocking questions.",
                    exit_code=6,
                )
            if not questions:
                raise AIWorkflowError(
                    code="invalid_questions",
                    message="At least one blocking question is required.",
                    exit_code=4,
                )
            state = self.store.read_json("state.json")
            if state["mode"] != "working" or state["active_work"] != work_id:
                raise AIWorkflowError(
                    code="invalid_state_transition",
                    message="Only active work can open blocking questions.",
                    exit_code=6,
                )
            work = self._read_work(work_id, expected_hash=state["active_work_sha256"])
            question_document = self.store.read_json("questions.json")
            existing_ids = [item["id"] for item in question_document["items"]]
            created: list[dict[str, Any]] = []
            timestamp = now_iso()
            for raw_question in questions:
                question = self._normalize_question(raw_question)
                question_id = next_id("question", existing_ids)
                existing_ids.append(question_id)
                created.append(
                    {
                        "id": question_id,
                        **question,
                        "stage": work["stage"],
                        "active_item": work["active_item"],
                        "work_id": work_id,
                        "status": "open",
                        "decision_id": None,
                        "created_at": timestamp,
                    }
                )
            updated_questions = {
                "schema_version": SCHEMA_VERSION,
                "items": [*question_document["items"], *created],
            }
            updated_work = dict(work)
            updated_work["status"] = "blocked"
            updated_work_bytes = json_bytes(updated_work)
            updated_state = dict(state)
            updated_state.update(
                {
                    "mode": "blocked",
                    "blocking_questions": [item["id"] for item in created],
                    "active_work_sha256": sha256_content(updated_work_bytes),
                    "updated_at": timestamp,
                }
            )
            event = self.store.commit_locked(
                {
                    ".aiwf/questions.json": json_bytes(updated_questions),
                    self._work_path(work_id, "work.json"): updated_work_bytes,
                    ".aiwf/state.json": json_bytes(updated_state),
                },
                event_type="question_opened",
                event_data={"work_id": work_id, "question_ids": updated_state["blocking_questions"]},
                command_key=command_key,
                request_digest=request_digest,
            )
            return dict(event["data"])

    def decide(self, question_id: str, decision: str) -> dict[str, Any]:
        if not decision.strip():
            raise AIWorkflowError(
                code="invalid_decision",
                message="Decision text cannot be empty.",
                exit_code=4,
            )
        command_key = f"decide:{question_id}"
        request_digest = self._digest({"question_id": question_id, "decision": decision})
        with self.store.lock(exclusive=True):
            self.store.recover_locked()
            existing_event = self.store.find_event(command_key)
            if existing_event is not None:
                if existing_event["request_digest"] != request_digest:
                    raise AIWorkflowError(
                        code="idempotency_conflict",
                        message="Question already has a different recorded decision.",
                        exit_code=6,
                    )
                return dict(existing_event["data"])
            questions = self.store.read_json("questions.json")
            question = next((item for item in questions["items"] if item["id"] == question_id), None)
            if question is None or question["status"] != "open":
                raise AIWorkflowError(
                    code="invalid_state_transition",
                    message="Question is not open for a decision.",
                    exit_code=6,
                    details={"question_id": question_id},
                )
            state = self.store.read_json("state.json")
            if state["mode"] != "blocked":
                raise AIWorkflowError(
                    code="invalid_state_transition",
                    message="Decisions can only resolve the blocked active work.",
                    exit_code=6,
                )
            if question_id not in state["blocking_questions"]:
                raise AIWorkflowError(
                    code="invalid_state_transition",
                    message="Question is not blocking the active work.",
                    exit_code=6,
                )
            decisions = self.store.read_json("decisions.json")
            decision_id = next_id("decision", [item["id"] for item in decisions["items"]])
            timestamp = now_iso()
            decision_item = {
                "id": decision_id,
                "question_id": question_id,
                "decision": decision,
                "impact": list(question["impact"]),
                "created_at": timestamp,
            }
            updated_decisions = {
                "schema_version": SCHEMA_VERSION,
                "items": [*decisions["items"], decision_item],
            }
            updated_question_items = []
            for item in questions["items"]:
                if item["id"] == question_id:
                    item = {**item, "status": "resolved", "decision_id": decision_id}
                updated_question_items.append(item)
            updated_questions = {
                "schema_version": SCHEMA_VERSION,
                "items": updated_question_items,
            }
            remaining = [item for item in state["blocking_questions"] if item != question_id]
            updated_state = dict(state)
            updated_state["blocking_questions"] = remaining
            updated_state["updated_at"] = timestamp
            changes: dict[str, bytes | None] = {
                ".aiwf/questions.json": json_bytes(updated_questions),
                ".aiwf/decisions.json": json_bytes(updated_decisions),
                ".aiwf/memory.md": render_memory(
                    self.store.read_json("memory.json"), updated_decisions
                ).encode("utf-8"),
            }
            successor_work_id: str | None = None
            previous_work_id = state["active_work"]
            if not remaining:
                previous_work = self._read_work(
                    previous_work_id,
                    expected_hash=state["active_work_sha256"],
                )
                successor_work_id = self._next_work_id()
                successor = copy_successor_work(previous_work, work_id=successor_work_id)
                successor_bytes = json_bytes(successor)
                changes[self._work_path(successor_work_id, "work.json")] = successor_bytes
                for source_name, target_name in (
                    (previous_work["draft_output"], successor["draft_output"]),
                    (previous_work["result_output"], successor["result_output"]),
                ):
                    source_path = self.store.safe_path(source_name)
                    if source_path.is_file():
                        changes[target_name] = source_path.read_bytes()
                updated_state.update(
                    {
                        "mode": "working",
                        "active_work": successor_work_id,
                        "active_work_sha256": sha256_content(successor_bytes),
                    }
                )
            changes[".aiwf/state.json"] = json_bytes(updated_state)
            event = self.store.commit_locked(
                changes,
                event_type="decision_recorded",
                event_data={
                    "question_id": question_id,
                    "decision_id": decision_id,
                    "successor_work_id": successor_work_id,
                },
                command_key=command_key,
                request_digest=request_digest,
            )
            if successor_work_id is not None and previous_work_id is not None:
                shutil.rmtree(
                    self.store.data_root / "work" / previous_work_id,
                    ignore_errors=True,
                )
            return dict(event["data"])

    def inspect(self) -> dict[str, Any]:
        with self.store.lock(exclusive=False):
            if self.store.has_pending_transactions():
                return {"status": "needs_recovery", "workspace": str(self.store.root)}
            documents = {name: self.store.read_json(name) for name in (
                "project.json",
                "state.json",
                "requirements.json",
                "tasks.json",
                "artifacts.json",
                "decisions.json",
                "questions.json",
                "memory.json",
            )}
            issues: list[dict[str, Any]] = []
            for artifact in documents["artifacts.json"]["items"]:
                try:
                    verify_artifact_integrity(self.store.root, artifact)
                except AIWorkflowError as error:
                    issues.append(
                        {
                            "level": "error",
                            "type": error.code,
                            "message": error.message,
                            "details": error.details,
                        }
                    )
            project = documents["project.json"]
            state = documents["state.json"]
            for prd_path in project["prd_files"]:
                try:
                    path = self.store.safe_path(prd_path)
                except AIWorkflowError as error:
                    issues.append(
                        {
                            "level": "error",
                            "type": error.code,
                            "message": error.message,
                            "details": error.details,
                        }
                    )
                    continue
                if not path.is_file():
                    issues.append(
                        {
                            "level": "error",
                            "type": "prd_missing",
                            "message": "Configured PRD copy is missing.",
                            "details": {"path": prd_path},
                        }
                    )
            repository = project["code_repository"]
            if repository is not None and not Path(repository).is_dir():
                issues.append(
                    {
                        "level": "warning",
                        "type": "code_repository_unavailable",
                        "message": "Configured code repository is not accessible.",
                        "details": {"path": repository},
                    }
                )
            artifacts_by_ref = {
                f"{item['id']}@{item['revision']}": item
                for item in documents["artifacts.json"]["items"]
            }
            for reference in state["pending_reviews"]:
                artifact = artifacts_by_ref.get(reference)
                if artifact is None or artifact["status"] != "review":
                    issues.append(
                        {
                            "level": "error",
                            "type": "pending_review_mismatch",
                            "message": "Pending review does not match the artifact registry.",
                            "details": {"reference": reference},
                        }
                    )
            open_questions = {
                item["id"]: item
                for item in documents["questions.json"]["items"]
                if item["status"] == "open"
            }
            for question_id in state["blocking_questions"]:
                if question_id not in open_questions:
                    issues.append(
                        {
                            "level": "error",
                            "type": "blocking_question_mismatch",
                            "message": "Blocking question is not open in the question registry.",
                            "details": {"question_id": question_id},
                        }
                    )
            if state["active_work"] is not None:
                try:
                    self._read_work(
                        state["active_work"],
                        expected_hash=state["active_work_sha256"],
                    )
                except AIWorkflowError as error:
                    issues.append(
                        {
                            "level": "error",
                            "type": error.code,
                            "message": error.message,
                            "details": error.details,
                        }
                    )
            requirement_ids = {item["id"] for item in documents["requirements.json"]["items"]}
            task_ids = {item["id"] for item in documents["tasks.json"]["items"]}
            for task in documents["tasks.json"]["items"]:
                unknown_requirements = sorted(set(task["requirements"]) - requirement_ids)
                unknown_dependencies = sorted(set(task["depends_on"]) - task_ids)
                if unknown_requirements or unknown_dependencies:
                    issues.append(
                        {
                            "level": "error",
                            "type": "task_reference_mismatch",
                            "message": "Task index contains unresolved references.",
                            "details": {
                                "task_id": task["id"],
                                "requirements": unknown_requirements,
                                "dependencies": unknown_dependencies,
                            },
                        }
                    )
            pending_review_items = [
                artifacts_by_ref[reference]
                for reference in state["pending_reviews"]
                if reference in artifacts_by_ref
            ]
            blocking_question_items = [
                open_questions[question_id]
                for question_id in state["blocking_questions"]
                if question_id in open_questions
            ]
            return {
                "status": "ok" if not issues else "issues_found",
                "workspace": str(self.store.root),
                "project": project,
                "state": state,
                "next_action": self._next_action(state),
                "counts": {
                    "prd_files": len(project["prd_files"]),
                    "requirements": len(documents["requirements.json"]["items"]),
                    "tasks": len(documents["tasks.json"]["items"]),
                    "artifacts": len(documents["artifacts.json"]["items"]),
                    "open_questions": len(open_questions),
                    "decisions": len(documents["decisions.json"]["items"]),
                    "memory_entries": sum(
                        item["status"] == "active" for item in documents["memory.json"]["items"]
                    ),
                },
                "pending_reviews": pending_review_items,
                "blocking_questions": blocking_question_items,
                "issues": issues,
            }

    def _next_action(self, state: dict[str, Any]) -> str:
        if state["mode"] == "review":
            return "review"
        if state["mode"] == "blocked":
            return "decide"
        if state["mode"] == "working":
            return "resume"
        return {
            "analysis": "analyze_requirements",
            "design": "design_solution",
            "specification": "generate_specification",
            "implementation": "implement_code",
            "testing": "generate_tests",
            "completed": "completed",
        }[state["current_stage"]]

    def _request_changes(
        self,
        artifact_id: str,
        revision: int,
        *,
        feedback: str,
        command_prefix: str,
    ) -> dict[str, Any]:
        if not feedback.strip():
            raise AIWorkflowError(
                code="invalid_feedback",
                message="Change feedback cannot be empty.",
                exit_code=4,
            )
        command_key = f"{command_prefix}:{artifact_id}@{revision}:changes_requested"
        request_digest = self._digest(
            {"artifact_id": artifact_id, "revision": revision, "feedback": feedback}
        )
        with self.store.lock(exclusive=True):
            self.store.recover_locked()
            existing_event = self.store.find_event(command_key)
            if existing_event is not None:
                if existing_event["request_digest"] != request_digest:
                    raise AIWorkflowError(
                        code="idempotency_conflict",
                        message="Revision feedback changed for an existing request.",
                        exit_code=6,
                    )
                return dict(existing_event["data"])
            state = self.store.read_json("state.json")
            artifacts = self.store.read_json("artifacts.json")
            artifact = find_artifact(artifacts, artifact_id)
            if artifact is None or artifact["revision"] != revision:
                raise AIWorkflowError(
                    code="unknown_artifact",
                    message="Artifact revision does not exist.",
                    exit_code=4,
                    details={"artifact_id": artifact_id, "revision": revision},
                )
            if command_prefix == "review":
                reviewed_ref = f"{artifact_id}@{revision}"
                if artifact["status"] != "review" or reviewed_ref not in state["pending_reviews"]:
                    raise AIWorkflowError(
                        code="invalid_state_transition",
                        message="Artifact is not awaiting review feedback.",
                        exit_code=6,
                    )
                self._reject_conflicting_review(artifact_id, revision, command_key)
            elif state["mode"] != "ready":
                raise AIWorkflowError(
                    code="invalid_state_transition",
                    message="Approved artifact revisions require a ready workspace.",
                    exit_code=6,
                )
            verify_artifact_integrity(self.store.root, artifact)
            previous_work = self.store.read_json_path(artifact["work_path"])
            validate_work(previous_work)
            work_id = self._next_work_id()
            successor = copy_successor_work(
                previous_work,
                work_id=work_id,
                feedback=feedback,
            )
            updated_artifact = {**artifact, "status": "changes_requested", "updated_at": now_iso()}
            artifacts = replace_artifact(artifacts, updated_artifact)
            updated_state = dict(state)
            updated_state.update(
                {
                    "current_stage": artifact["stage"],
                    "mode": "working",
                    "active_item": artifact["active_item"],
                    "active_work": work_id,
                    "active_work_sha256": sha256_content(json_bytes(successor)),
                    "pending_reviews": [],
                    "blocking_questions": [],
                    "updated_at": now_iso(),
                }
            )
            event = self.store.commit_locked(
                {
                    ".aiwf/artifacts.json": json_bytes(artifacts),
                    ".aiwf/state.json": json_bytes(updated_state),
                    self._work_path(work_id, "work.json"): json_bytes(successor),
                    successor["draft_output"]: self.store.safe_path(artifact["path"]).read_bytes(),
                    successor["result_output"]: self.store.safe_path(artifact["result_path"]).read_bytes(),
                },
                event_type="changes_requested",
                event_data={
                    "artifact_id": artifact_id,
                    "revision": revision,
                    "work_id": work_id,
                    "feedback": feedback,
                },
                command_key=command_key,
                request_digest=request_digest,
            )
            return dict(event["data"])

    def _read_work(
        self,
        work_id: str | None,
        *,
        expected_hash: str | None = None,
    ) -> dict[str, Any]:
        if work_id is None:
            raise AIWorkflowError(
                code="invalid_state",
                message="Workflow state does not identify active work.",
                exit_code=4,
            )
        path = self.store.safe_path(self._work_path(work_id, "work.json"))
        try:
            content = path.read_bytes()
            value = json.loads(content.decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise AIWorkflowError(
                code="work_drift",
                message="Active work metadata cannot be read.",
                exit_code=7,
                details={"work_id": work_id},
            ) from error
        if expected_hash is not None and sha256_content(content) != expected_hash:
            raise AIWorkflowError(
                code="work_drift",
                message="Active work metadata changed outside the workflow.",
                exit_code=7,
                details={"work_id": work_id},
            )
        return validate_work(value)

    def _next_work_id(self) -> str:
        existing: list[str] = []
        for event in self.store.read_events():
            data = event.get("data", {})
            for field_name in ("work_id", "successor_work_id"):
                value = data.get(field_name) if isinstance(data, dict) else None
                if isinstance(value, str):
                    existing.append(value)
        work_root = self.store.data_root / "work"
        if work_root.is_dir():
            existing.extend(path.name for path in work_root.iterdir() if path.is_dir())
        return next_id("work", existing)

    def _validate_active_item(self, stage: str, active_item: str | None) -> None:
        artifact_identity(stage, active_item)
        if active_item is None:
            return
        tasks = self.store.read_json("tasks.json")
        task = next((item for item in tasks["items"] if item["id"] == active_item), None)
        if task is None or task["status"] in {"deferred", "withdrawn"}:
            raise AIWorkflowError(
                code="unknown_task_id",
                message="Active item is not an available task.",
                exit_code=4,
                details={"id": active_item},
            )
        allowed_statuses = {
            "specification": {"planned", "stale"},
            "implementation": {"in_progress", "stale"},
            "testing": {"implemented", "stale"},
        }
        if stage in allowed_statuses and task["status"] not in allowed_statuses[stage]:
            raise AIWorkflowError(
                code="task_not_ready",
                message="Task status does not allow work in the current stage.",
                exit_code=6,
                details={"id": active_item, "status": task["status"], "stage": stage},
            )

    def _validate_dependencies(self, dependencies: Sequence[str]) -> None:
        artifacts = self.store.read_json("artifacts.json")
        for reference in dependencies:
            try:
                artifact_id, raw_revision = reference.rsplit("@", 1)
                revision = int(raw_revision)
            except (ValueError, AttributeError) as error:
                raise AIWorkflowError(
                    code="invalid_dependency",
                    message="Artifact dependency must use artifact@revision.",
                    exit_code=4,
                    details={"reference": reference},
                ) from error
            artifact = find_artifact(artifacts, artifact_id)
            if (
                artifact is None
                or artifact["status"] != "approved"
                or artifact["approved_revision"] != revision
            ):
                raise AIWorkflowError(
                    code="unavailable_dependency",
                    message="Artifact dependency is not an approved revision.",
                    exit_code=4,
                    details={"reference": reference},
                )

    def _mark_tasks_stale(
        self,
        tasks: dict[str, Any],
        invalidated: Sequence[str],
        source_stage: str,
    ) -> dict[str, Any]:
        items = [dict(item) for item in tasks["items"]]
        if source_stage == "analysis" and invalidated:
            for item in items:
                if item["status"] not in {"deferred", "withdrawn"}:
                    item["status"] = "stale"
        elif source_stage != "design":
            affected_ids = {
                "-".join(artifact_id.split("-")[:2]) for artifact_id in invalidated
            }
            for item in items:
                if item["id"] in affected_ids:
                    item["status"] = "stale"
        return {"schema_version": SCHEMA_VERSION, "items": items}

    def _normalize_question(self, raw_question: Mapping[str, Any]) -> dict[str, Any]:
        required_strings = ("question", "reason", "recommendation")
        normalized: dict[str, Any] = {}
        for field_name in required_strings:
            value = raw_question.get(field_name)
            if not isinstance(value, str) or not value.strip():
                raise AIWorkflowError(
                    code="invalid_questions",
                    message=f"Question field '{field_name}' must be non-empty.",
                    exit_code=4,
                )
            normalized[field_name] = value
        impact = raw_question.get("impact")
        if not isinstance(impact, list) or any(
            not isinstance(item, str) or not item for item in impact
        ):
            raise AIWorkflowError(
                code="invalid_questions",
                message="Question impact must be an array of strings.",
                exit_code=4,
            )
        normalized["impact"] = list(impact)
        return normalized

    def _reject_conflicting_review(
        self,
        artifact_id: str,
        revision: int,
        command_key: str,
    ) -> None:
        prefix = f"review:{artifact_id}@{revision}:"
        for event in self.store.read_events():
            existing_key = event.get("command_key")
            if isinstance(existing_key, str) and existing_key.startswith(prefix) and existing_key != command_key:
                raise AIWorkflowError(
                    code="review_conflict",
                    message="Artifact revision already has a different review outcome.",
                    exit_code=6,
                    details={"artifact_id": artifact_id, "revision": revision},
                )

    def _work_path(self, work_id: str, filename: str) -> str:
        return f".aiwf/work/{work_id}/{filename}"

    def _digest(self, value: Any) -> str:
        return sha256_bytes(
            json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
        )


def execute(request: CommandRequest) -> dict[str, Any]:
    engine = WorkflowEngine(request.workspace)
    if request.command == "init":
        return engine.initialize(
            name=request.options.get("name", request.workspace.name),
            platform=request.options["platform"],
            prd_paths=request.options["prd"],
            code_repository=request.options.get("code_repository"),
            project_id=request.options.get("project_id"),
        )
    if request.command == "status":
        return engine.inspect()
    if request.command == "prepare":
        return engine.prepare_work(
            active_item=request.options.get("task_id"),
            instruction=request.options.get("instruction", ""),
        )
    if request.command == "submit":
        return engine.submit_work(request.options["work_id"])
    if request.command == "review":
        return engine.review_artifact(
            request.options["artifact_id"],
            request.options["revision"],
            outcome=request.options["outcome"],
            feedback=request.options.get("feedback", ""),
        )
    if request.command == "question":
        try:
            questions = json.loads(request.options["items_json"])
        except (TypeError, json.JSONDecodeError) as error:
            raise AIWorkflowError(
                code="invalid_questions",
                message="Blocking questions must be a valid JSON array.",
                exit_code=2,
            ) from error
        if not isinstance(questions, list):
            raise AIWorkflowError(
                code="invalid_questions",
                message="Blocking questions must be a valid JSON array.",
                exit_code=2,
            )
        return engine.open_questions(request.options["work_id"], questions)
    if request.command == "decide":
        return engine.decide(request.options["question_id"], request.options["decision"])
    raise AIWorkflowError(
        code="command_not_implemented",
        message=f"Command '{request.command}' is not connected before its implementation phase.",
        exit_code=3,
        details={
            "command": request.command,
            "phase": 4,
            "workspace": str(request.workspace),
        },
    )
