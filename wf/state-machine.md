# AIWorkFlow 状态机

## 状态定义

| 状态 | 含义 |
|---|---|
| `not_initialized` | 尚未创建 AIWorkFlow 工作空间 |
| `initialized` | 工作空间已创建，下一步是需求分析 |
| `requirements_analyzed` | `output/analysis.md` 已生成且审核确认，下一步是技术设计 |
| `design_ready` | `output/design.md` 已生成且审核确认，下一步是规格生成 |
| `specs_ready` | `output/design.md` 中每个任务都有对应规格文件且审核确认，下一步是代码实现 |
| `implementation_in_progress` | 部分任务已实现，仍有实现或测试工作 |
| `implementation_done` | 所有实现任务完成，下一步是测试 |
| `tests_done` | 所有任务均有测试记录 |
| `blocked_by_decision` | 需要人工决策后才能安全继续 |
| `blocked_by_missing_input` | 缺少必要输入或工作空间文件 |
| `blocked_by_inconsistent_state` | 工作空间状态与产物不一致 |

## 事件定义

| 事件 | 产生来源 |
|---|---|
| `workspace_initialized` | `wf-init` |
| `analysis_completed` | 运行时在 `output/analysis.md` 审核确认后产生 |
| `design_completed` | 运行时在 `output/design.md` 审核确认后产生 |
| `specs_generated` | 运行时在所有目标规格审核确认后产生 |
| `task_implemented` | 运行时在 `output/report-T-XXX.md` 审核确认后产生 |
| `all_tasks_implemented` | 运行时扫描任务后产生 |
| `tests_generated` | 运行时在 `output/test-report-T-XXX.md` 审核确认后产生 |
| `all_tests_completed` | 运行时扫描测试记录后产生 |
| `decision_required` | 任意能力 |
| `decision_resolved` | 运行时处理人工决策 |
| `guard_failed` | 门禁检查 |
| `input_fixed` | 用户补齐缺失输入或文件 |
| `state_fixed` | 用户修正不一致状态或产物 |

## 主流程转移

| 当前状态 | 事件 | 新状态 | 下一步 |
|---|---|---|---|
| `not_initialized` | `workspace_initialized` | `initialized` | `analyze-requirements` |
| `initialized` | `analysis_completed` | `requirements_analyzed` | `design-solution` |
| `requirements_analyzed` | `design_completed` | `design_ready` | `generate-specs` |
| `design_ready` | `specs_generated` | `specs_ready` | `implement-code` |
| `specs_ready` | `task_implemented` | `implementation_in_progress` | `implement-code` 或 `generate-tests` |
| `specs_ready` | `all_tasks_implemented` | `implementation_done` | `generate-tests` |
| `implementation_in_progress` | `all_tasks_implemented` | `implementation_done` | `generate-tests` |
| `implementation_in_progress` | `tests_generated` | `implementation_in_progress` | `implement-code` 或 `generate-tests` |
| `implementation_done` | `tests_generated` | `implementation_done` | `generate-tests` |
| `implementation_done` | `all_tests_completed` | `tests_done` | `status` |

## 阻塞转移

| 当前状态 | 事件 | 新状态 |
|---|---|---|
| 任意活动状态 | `decision_required` | `blocked_by_decision` |
| 任意活动状态 | 缺输入导致的 `guard_failed` | `blocked_by_missing_input` |
| 任意活动状态 | 状态不一致导致的 `guard_failed` | `blocked_by_inconsistent_state` |

进入阻塞状态时，`CONTEXT.md` 的下一步必须写为：

| 阻塞状态 | 下一步 |
|---|---|
| `blocked_by_decision` | `resolve-decision` |
| `blocked_by_missing_input` | `fix-workspace` |
| `blocked_by_inconsistent_state` | `fix-workspace` |

## 审核等待

阶段能力生成或实质修订产物后，不产生主流程完成事件，`CONTEXT.md` 的阶段保持为生成前的活动状态，下一步写为 `review-artifact`。

| 生成或修订的产物 | 保持阶段 | 下一步 |
|---|---|---|
| `output/analysis.md` | `initialized` | `review-artifact` |
| `output/design.md` | `requirements_analyzed` | `review-artifact` |
| `output/specs/T-XXX.md` | `design_ready` | `review-artifact` |
| `output/report-T-XXX.md` | `specs_ready` 或 `implementation_in_progress` | `review-artifact` |
| `output/test-report-T-XXX.md` | `implementation_in_progress` 或 `implementation_done` | `review-artifact` |

用户确认目标产物后，运行时先校验产物契约；校验通过后将审核状态写为 `已确认`，再产生对应主流程事件。校验失败时不得确认：可修订问题写入 `REVISIONS.md` 并保持 `review-artifact`；需要人工决策的问题写入 `ISSUES.md` 并进入 `blocked_by_decision`。

进入 `review-artifact` 时，`CONTEXT.md` 的 `待处理产物` 必须列出全部审核状态为 `待审核` 或 `需修改` 的阶段产物。多个待处理产物存在且用户未指定目标时，运行时必须先询问目标产物。

## 阻塞解除

阻塞解除后，运行时必须重新扫描产物事实恢复活动状态，不得盲目信任 `CONTEXT.md` 或历史记录中的旧状态。

| 当前状态 | 解除事件 | 恢复规则 |
|---|---|---|
| `blocked_by_decision` | `decision_resolved` | 重新扫描产物，恢复到满足当前产物集合的最高活动状态 |
| `blocked_by_missing_input` | `input_fixed` | 重新执行门禁，门禁通过后恢复到满足当前产物集合的最高活动状态 |
| `blocked_by_inconsistent_state` | `state_fixed` | 重新执行一致性检查，检查通过后恢复到满足当前产物集合的最高活动状态 |

恢复活动状态时按以下优先级判断：

1. 所有任务均已实现且均已测试，对应 `output/report-T-XXX.md` 和 `output/test-report-T-XXX.md` 审核状态均为 `已确认` → `tests_done`，下一步 `status`。
2. 所有任务均已实现，且 `output/report-T-XXX.md` 审核状态均为 `已确认`，但仍有未测试任务 → `implementation_done`，下一步 `generate-tests`。
3. 存在已确认的实现报告，且仍有未实现或未测试任务 → `implementation_in_progress`，下一步 `implement-code` 或 `generate-tests`。
4. `output/design.md` 中每个任务都有对应规格文件，且所有规格文件审核状态均为 `已确认` → `specs_ready`，下一步 `implement-code`。
5. `output/design.md` 审核状态为 `已确认` → `design_ready`，下一步 `generate-specs`。
6. `output/analysis.md` 审核状态为 `已确认` → `requirements_analyzed`，下一步 `design-solution`。
7. 仅完成初始化 → `initialized`，下一步 `analyze-requirements`。

存在未确认产物时，不得按产物存在性恢复到下一阶段；应保持在产物所属阶段，并提示用户审核、修订或确认。

如果阻塞原因只是 `CONTEXT.md` 状态快照与产物事实不一致，运行时应优先通过 `rebuild_context.py` 重建快照，再重新执行校验。校验仍失败时不得继续阶段能力。
