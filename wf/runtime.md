# AIWorkFlow 运行时规则

## 作用

`runtime.md` 定义所有 AIWorkFlow 操作都必须遵守的通用运行规则。能力契约只描述“产出什么、如何产出”；运行时负责“如何读取状态、如何更新产物、如何审计一致性”。

## 工作空间识别

当前目录存在 `CONTEXT.md` 时，即视为 AIWorkFlow 工作空间。

如果存在 `CONTEXT.md`，但缺少 `AGENT.md`、`ISSUES.md`、`REVISIONS.md`、`JOURNAL.md`、`CHANGELOG.md`、`prd/` 或 `output/`，则视为不完整工作空间。此时必须先输出修复建议，不得继续执行会改变状态的工作。

## 必须加载的上下文

任何需求分析、技术设计、规格生成、代码实现、测试生成、决策处理或状态推进操作前，必须按顺序读取：

1. 工作空间 `AGENT.md`
2. 工作空间 `CONTEXT.md`
3. 工作空间 `ISSUES.md`
4. 工作空间 `REVISIONS.md`
5. `JOURNAL.md` 中最近相关记录
6. `guards.md`
7. 当前动作需要的能力契约和产物契约

## 事务模型

每次会改变工作空间状态的操作都视为一次工作流事务：

1. 读取当前状态。
2. 检查 `REVISIONS.md` 是否存在待处理修订；若存在，优先执行修订收敛。
3. 执行门禁检查。
4. 选择 `capabilities/` 中的一个能力；处理人工决策或修订收敛时不选择能力，改为执行对应运行时流程。
5. 执行能力、决策处理或修订收敛。
6. 写入能力产物、决策归档或修订归档。
7. 根据产物审核状态和 `state-machine.md` 更新 `CONTEXT.md`。
8. 必要时写入或解决 `ISSUES.md`。
9. 追加 `JOURNAL.md`。
10. 输出本次结果和下一步建议。

如果执行过程中发现必须由人工决策的问题，则写入 `ISSUES.md` 和 `JOURNAL.md`，并将 `CONTEXT.md` 更新为 `blocked_by_decision` / `resolve-decision` 后停止。不得在同一次事务中继续推进到下一个能力。

如果门禁失败是缺少必要输入或工作空间文件，则将 `CONTEXT.md` 更新为 `blocked_by_missing_input` / `fix-workspace`。如果门禁失败是状态与产物矛盾，则将 `CONTEXT.md` 更新为 `blocked_by_inconsistent_state` / `fix-workspace`。

## 问题处理

当不确定项会影响行为、文件选择、任务范围或产物内容时，必须写入 `ISSUES.md`。如果能力契约明确列出某类不确定项，Agent 不得替用户擅自决定。

每个问题必须包含：

- 问题
- AI 建议
- 影响
- 提出来源和日期
- 空的人工决策字段
- 状态

当用户对 `Q-XXX` 给出决策后，运行时负责执行决策、归档到 `CHANGELOG.md`、从 `ISSUES.md` 删除该问题，并追加 `JOURNAL.md`。

处理决策前必须确认：

- `Q-XXX` 在 `ISSUES.md` 中存在且编号唯一。
- 该问题包含非空 `人工决策`。
- 决策影响的产物或代码范围可识别。

处理完成后产生 `decision_resolved` 事件，并按 `state-machine.md` 的阻塞解除规则重新扫描产物恢复活动状态。

## 用户修订处理

用户通过对话提出明确产物修订时，运行时必须先把修订写入 `REVISIONS.md` 的 `## 待处理`，再执行收敛。

每次执行 `wf` 时，如果 `REVISIONS.md` 中存在状态为 `待处理` 的修订，必须优先处理修订：

1. 读取目标产物和对应 `contracts/*.md`。
2. 按用户意见修改目标产物。
3. 判断并同步受影响的下游产物；不能安全同步时写入 `ISSUES.md`。
4. 将修订条目从 `## 待处理` 移动到 `## 已处理`，状态改为 `已处理`，补充处理结果、更新产物和处理时间。
5. 追加 `JOURNAL.md`。

如果修订无法处理：

- 需要人工决策时，写入 `ISSUES.md`，保留修订条目并标记 `阻塞`，将 `CONTEXT.md` 更新为 `blocked_by_decision` / `resolve-decision`。
- 缺少必要输入或工作空间文件时，保留修订条目并标记 `阻塞`，将 `CONTEXT.md` 更新为 `blocked_by_missing_input` / `fix-workspace`。
- 产物或状态不一致时，保留修订条目并标记 `阻塞`，将 `CONTEXT.md` 更新为 `blocked_by_inconsistent_state` / `fix-workspace`。

修订收敛成功后，目标产物审核状态必须回到 `待审核`，`修订来源` 填写已处理的 `R-XXX`，`CONTEXT.md` 下一步保持 `review-artifact`。修订阻塞时，目标产物审核状态保持 `需修改`，`修订来源` 填写阻塞的 `R-XXX`。

## 人工审核

每个阶段产物生成或实质更新后，运行时必须将该产物的 `## 审核状态` 写为 `待审核`，并停止推进下一阶段。

产物进入 `待审核` 后，运行时必须更新 `CONTEXT.md`：

- 阶段保持为生成前的活动状态。
- 下一步写为 `review-artifact`。
- 不产生 `analysis_completed`、`design_completed`、`specs_generated`、`task_implemented` 或 `tests_generated`。

用户可以通过两种方式完成审核：

- 明确确认产物通过：运行时先按目标产物契约执行完整校验；校验通过后，将该产物审核状态改为 `已确认`，填写审核人和审核时间，然后根据 `state-machine.md` 产生对应完成事件。
- 提出修改意见：运行时将该产物审核状态改为 `需修改`，把修改意见写入 `REVISIONS.md`，`CONTEXT.md` 下一步保持 `review-artifact`，再按用户修订处理流程收敛。

确认前校验失败时，不得将审核状态改为 `已确认`：

- 产物结构或内容可由明确修订解决时，写入 `REVISIONS.md`，目标产物审核状态改为 `需修改`，`CONTEXT.md` 下一步保持 `review-artifact`。
- 失败原因需要人工决策时，写入 `ISSUES.md`，将 `CONTEXT.md` 更新为 `blocked_by_decision` / `resolve-decision`。
- 失败原因是缺输入或状态不一致时，进入对应的 `blocked_by_missing_input` 或 `blocked_by_inconsistent_state`。

审核通过后才允许产生以下事件：

- `output/analysis.md` 已确认 → `analysis_completed`
- `output/design.md` 已确认 → `design_completed`
- `output/design.md` 中每个任务都有对应 `output/specs/T-XXX.md`，且全部规格已确认 → `specs_generated`
- `output/report-T-XXX.md` 已确认 → 先更新 `CONTEXT.md` 的 `## 代码产出`，再产生 `task_implemented`
- `output/test-report-T-XXX.md` 已确认 → 先更新 `CONTEXT.md` 的 `## 测试记录`，再产生 `tests_generated`

## `CONTEXT.md` 更新

`CONTEXT.md` 中的阶段、下一步、任务完成状态、代码产出状态和测试状态，只能由运行时根据状态机更新。

能力只生成或修订产物，不直接产生完成事件。完成事件只能由运行时在对应产物审核状态为 `已确认` 后产生，并根据 `state-machine.md` 映射为状态变化。

当 `CONTEXT.md` 的下一步是 `review-artifact` 时，运行时不得再次执行生成能力。它只能执行以下动作：

- 用户明确确认产物通过时，执行人工审核确认流程。
- 用户提出修改意见时，写入 `REVISIONS.md` 并执行修订收敛。
- 用户没有给出确认或修订时，输出待审核产物清单和下一步提示，不落盘。

任何扫描或事件处理结束后，如果仍存在审核状态为 `待审核` 或 `需修改` 的阶段产物，`CONTEXT.md` 下一步必须保持 `review-artifact`，不得写为下游能力。

`task_implemented` 后，运行时必须扫描 `CONTEXT.md` 规格索引和 `output/report-T-XXX.md`：

- 如果所有真实任务均已完成，且对应报告存在并已确认，产生 `all_tasks_implemented`。
- 否则保持 `implementation_in_progress`，下一步根据剩余未实现任务或未测试任务写为 `implement-code` 或 `generate-tests`。

`tests_generated` 后，运行时必须扫描 `CONTEXT.md` 测试记录和 `output/test-report-T-XXX.md`：

- 如果所有真实任务均已实现且均已测试，对应报告和测试报告均存在并已确认，产生 `all_tests_completed`。
- 如果所有真实任务均已实现，但仍有未测试任务，保持 `implementation_done`，下一步继续 `generate-tests`。
- 如果仍有未实现任务，保持 `implementation_in_progress`，下一步根据剩余未实现任务或未测试任务写为 `implement-code` 或 `generate-tests`。

## `JOURNAL.md` 更新

每次会改变状态的事务都必须追加 `JOURNAL.md`。条目应包含：

- 能力或运行时动作
- 目标任务或问题编号
- 创建或修改的文件和产物
- 新增或解决的问题数量
- 下一步建议

## `CHANGELOG.md` 更新

`CHANGELOG.md` 只用于归档已解决的人工决策，不作为普通活动日志。

## 上游产物修改规则

下游能力不得静默改写上游产物。实现阶段发现规格或设计错误时，应在报告中记录偏离；如果需要人工决策，则同时写入 `ISSUES.md`。
