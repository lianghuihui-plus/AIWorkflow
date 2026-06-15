# AIWorkFlow 运行时规则

## 作用

`runtime.md` 定义所有 AIWorkFlow 操作都必须遵守的通用运行规则。能力契约只描述“产出什么、如何产出”；运行时负责“如何读取状态、如何更新产物、如何审计一致性”。

## 工作空间识别

当前目录存在 `CONTEXT.md` 时，即视为 AIWorkFlow 工作空间。

如果存在 `CONTEXT.md`，但缺少 `AGENT.md`、`ISSUES.md`、`REVISIONS.md`、`JOURNAL.md`、`CHANGELOG.md`、`prd/` 或 `output/`，则视为不完整工作空间。此时必须先输出修复建议，不得继续执行会改变状态的工作。

## 事务内读取策略

任何需求分析、技术设计、规格生成、代码实现、测试生成、决策处理或状态推进操作，都必须按“最小识别上下文 + 按动作补读”的方式读取文件。

每次 `wf` 执行视为一个事务。事务内应维护已读文件集合：

- 文件路径
- 读取用途
- 是否在本事务内被修改、重建或判定失效

入口阶段只读取识别状态和目标动作所需的最小上下文：

1. 工作空间 `AGENT.md`
2. 工作空间 `CONTEXT.md`
3. 工作空间 `ISSUES.md` 摘要；处理指定 `Q-XXX` 时读取目标问题完整内容
4. 工作空间 `REVISIONS.md` 摘要；处理指定 `R-XXX` 时读取目标修订完整内容
5. `JOURNAL.md` 中最近相关记录

入口阶段不默认读取完整 `output/`、全部 `capabilities/`、全部 `contracts/`、完整 `runtime.md`、完整 `state-machine.md` 或完整 `guards.md`。进入具体动作后，只补读该动作需要且尚未读取的能力、契约、目标产物和代码文件。

同一事务中，如果文件已经读取且未被本事务修改、重建或判定失效，后续步骤必须复用已读内容，不重复读取。以下情况必须重新读取相关文件：

- `rebuild_context.py` 更新了 `CONTEXT.md`。
- Agent 写入或修改了 `ISSUES.md`、`REVISIONS.md`、`CHANGELOG.md` 或阶段产物。
- Agent 追加了 `JOURNAL.md`，且后续输出依赖最新日志内容。
- 用户在对话中说明已手动修改某个文件。
- `tools/validate.py` 输出与已读内容冲突。
- 进入下一次 `wf` 事务或新会话。

确定性结构检查优先通过当前 skill 目录下的 `tools/validate.py` 执行。Agent 不应为了状态检查和门禁判断读取全量 `output/` 产物；校验器输出通过后，只读取当前动作目标产物、异常定位文件以及必要契约。

`runtime.md`、`state-machine.md`、`guards.md` 只在需要解释事务规则、状态迁移或补充语义门禁时读取。如果这些文件已经在当前事务中读取且未被修改，不重复读取。

## 按动作补读清单

以下清单表示进入动作后需要补读的文件；已在当前事务中读取且未失效的文件不重复读取。

| 动作 | 补读文件 |
|---|---|
| `analyze-requirements` | `capabilities/analyze-requirements.md`、`contracts/analysis.md`、`contracts/review-status.md`、`prd/*` |
| `design-solution` | `capabilities/design-solution.md`、`contracts/design.md`、`contracts/review-status.md`、`output/analysis.md`、必要代码仓库结构 |
| `generate-specs` | `capabilities/generate-specs.md`、`contracts/spec.md`、`contracts/review-status.md`、`output/analysis.md`、`output/design.md`、必要代码仓库结构 |
| `implement-code` | `capabilities/implement-code.md`、`contracts/spec.md`、`contracts/code-report.md`、`contracts/review-status.md`、目标 `output/specs/T-XXX.md`、`output/design.md` 中对应任务、`output/analysis.md` 中关联需求、相关源码 |
| `generate-tests` | `capabilities/generate-tests.md`、`contracts/test-report.md`、`contracts/review-status.md`、目标 `output/specs/T-XXX.md`、目标 `output/reports/T-XXX.md`、相关源码、已有测试模式 |
| `review-artifact` | 目标产物、目标产物对应契约、`contracts/review-status.md`、必要时读取 `state-machine.md` |
| `resolve-decision` | `ISSUES.md` 中目标 `Q-XXX`、`contracts/issues.md`、`contracts/changelog.md`、目标问题影响的产物 |
| 修订收敛 | `REVISIONS.md` 中目标 `R-XXX`、`contracts/revisions.md`、目标产物契约、`contracts/review-status.md`、目标产物、受影响下游产物 |
| `fix-workspace` | `tools/validate.py` 输出指向的异常文件；如果只是 `CONTEXT.md` 快照漂移，执行 `tools/rebuild_context.py` 后重读 `CONTEXT.md` |

## 写入后重读规则

写入后应将对应文件标记为已修改。如果后续判断依赖该文件内容，必须重新读取。

- 写入阶段产物后，如果后续需要使用该产物内容，必须重新读取目标产物。
- 修改产物审核状态后，应运行或等效执行 `rebuild_context.py`，然后重新读取 `CONTEXT.md`。
- 写入 `ISSUES.md` 后，如果本事务还需要读取待决策数量或目标问题，必须重新读取 `ISSUES.md`。
- 写入 `REVISIONS.md` 后，如果本事务还要处理修订列表，必须重新读取 `REVISIONS.md`。
- 追加 `JOURNAL.md` 后，通常不需要重新读取，除非后续输出依赖最新日志内容。
- `rebuild_context.py` 更新 `CONTEXT.md` 后，必须重新读取 `CONTEXT.md`，再继续依赖上下文快照的判断。

## 事务模型

每次会改变工作空间状态的操作都视为一次工作流事务：

1. 读取当前状态。
2. 检查 `REVISIONS.md` 是否存在待处理修订；若存在，优先执行修订收敛。
3. 执行 `tools/validate.py` 和门禁检查；可脚本化硬规则以校验器结果为准，语义判断仍由 Agent 按契约处理。
4. 选择 `capabilities/` 中的一个能力；处理人工决策或修订收敛时不选择能力，改为执行对应运行时流程。
5. 执行能力、决策处理或修订收敛。
6. 写入能力产物、决策归档或修订归档。
7. 根据产物审核状态和 `state-machine.md` 更新 `CONTEXT.md`；如只是状态快照漂移，优先通过 `rebuild_context.py` 重建。
8. 必要时写入或解决 `ISSUES.md`。
9. 追加 `JOURNAL.md`。
10. 输出本次结果和下一步建议。

如果执行过程中发现必须由人工决策的问题，则写入 `ISSUES.md` 和 `JOURNAL.md`，并将 `CONTEXT.md` 更新为 `blocked_by_decision` / `resolve-decision` 后停止。不得在同一次事务中继续推进到下一个能力。

如果门禁失败是缺少必要输入或工作空间文件，则将 `CONTEXT.md` 更新为 `blocked_by_missing_input` / `fix-workspace`。如果门禁失败是状态与产物矛盾，则将 `CONTEXT.md` 更新为 `blocked_by_inconsistent_state` / `fix-workspace`。

## 有序写入规则

所有工作流文件都必须保持稳定的结构顺序，禁止为了“追加”把新条目直接插到章节顶部或插入到标题和既有内容之间。

- 编号型条目按编号升序排列：`PRD-XX`、`REQ-XXX`、`Q-XXX`、`R-XXX`、`T-XXX`、修改点序号、偏离序号。
- 分章节编号文件在目标章节内按编号升序排列；新编号仍从全文件最大编号递增。
- 日期归档文件按 `YYYY-MM-DD` 日期章节升序排列；同一天只保留一个日期章节；同日新条目追加到该日期章节末尾。
- 表格和清单更新时保持原有表头位置不变，只改对应行或按编号顺序插入新行。
- `暂无` 只用于空章节或空列表；同一章节出现真实条目时必须删除 `暂无`。
- 运行时重建类文件优先使用 `rebuild_context.py` 等确定性工具生成，避免手工局部插入导致顺序漂移。

## 产物事实源与状态快照

阶段产物及其审核状态是工作流事实源，`CONTEXT.md` 是运行时生成的状态快照。任务是否已规格化、已实现或已测试，必须以对应产物存在且审核状态为 `已确认` 为准。

`CONTEXT.md` 中除 `## 项目约束` 来自初始化输入并在重建时保留外，其余摘要和状态信息均应由运行时根据阶段产物生成。`## 需求概要` 的权威来源是 `output/analysis.md` 的 `## 需求概要`；需求分析能力不得直接维护 `CONTEXT.md` 中的需求概要。

| 事实 | 权威来源 |
|---|---|
| 需求分析是否可进入设计 | `output/analysis.md` 存在，且审核状态为 `已确认` |
| 技术方案是否可进入规格 | `output/design.md` 存在，且审核状态为 `已确认` |
| 任务是否有规格 | `output/specs/T-XXX.md` 存在，且审核状态为 `已确认` |
| 任务是否已实现 | `output/reports/T-XXX.md` 存在，且审核状态为 `已确认` |
| 任务是否已测试 | `output/test-reports/T-XXX.md` 存在，且审核状态为 `已确认` |
| 是否停在审核阶段 | 存在任一审核状态为 `待审核` 或 `需修改` 的阶段产物 |

当 `CONTEXT.md` 与产物事实冲突时，以产物事实为准。运行时应进入 `blocked_by_inconsistent_state` / `fix-workspace`，并优先执行 `rebuild_context.py` 重建 `CONTEXT.md`。重建后必须再次运行 `tools/validate.py`，仍失败时不得继续阶段能力。

`rebuild_context.py` 允许根据阶段产物重建 `CONTEXT.md`，但必须保留 `## 项目约束`。它不得修改 `output/` 阶段产物、`ISSUES.md`、`REVISIONS.md` 或代码仓库。通过 `wf` 触发重建时，`wf` 必须在脚本成功后追加 `JOURNAL.md`。

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

写入 `ISSUES.md` 时，新问题必须放入对应阶段章节，并按 `Q-XXX` 升序插入；有问题条目时删除该阶段的 `暂无` 占位。处理完成归档到 `CHANGELOG.md` 时，必须复用或创建正确日期章节，不得直接插到文件顶部。

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

写入和归档修订时必须遵守 `contracts/revisions.md` 的结构约束：`## 待处理` 和 `## 已处理` 内分别按 `R-XXX` 升序排列；新增修订写入待处理区的正确编号位置；处理完成的修订移动到已处理区的正确编号位置；有条目时删除该章节的 `暂无` 占位。

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
- `待处理产物` 列出全部审核状态为 `待审核` 或 `需修改` 的阶段产物。
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
- `output/reports/T-XXX.md` 已确认 → 先更新 `CONTEXT.md` 的 `## 代码产出`，再产生 `task_implemented`
- `output/test-reports/T-XXX.md` 已确认 → 先更新 `CONTEXT.md` 的 `## 测试记录`，再产生 `tests_generated`

## `CONTEXT.md` 更新

`CONTEXT.md` 中的阶段、下一步、任务完成状态、代码产出状态和测试状态，只能由运行时根据状态机更新。

能力只生成或修订产物，不直接产生完成事件。完成事件只能由运行时在对应产物审核状态为 `已确认` 后产生，并根据 `state-machine.md` 映射为状态变化。

当 `CONTEXT.md` 的下一步是 `review-artifact` 时，运行时不得再次执行生成能力。它只能执行以下动作：

- 用户明确确认产物通过时，执行人工审核确认流程。
- 用户提出修改意见时，写入 `REVISIONS.md` 并执行修订收敛。
- 用户没有给出确认或修订时，输出待审核产物清单和下一步提示，不落盘。

当待处理产物超过一个且用户没有明确目标产物时，运行时必须先询问目标，不得猜测。

任何扫描或事件处理结束后，如果仍存在审核状态为 `待审核` 或 `需修改` 的阶段产物，`CONTEXT.md` 下一步必须保持 `review-artifact`，`待处理产物` 必须列出全部目标，不得写为下游能力。

`task_implemented` 后，运行时必须按产物事实扫描任务和 `output/reports/T-XXX.md`：

- 如果所有真实任务均已完成，且对应报告存在并已确认，产生 `all_tasks_implemented`。
- 否则保持 `implementation_in_progress`，下一步根据剩余未实现任务或未测试任务写为 `implement-code` 或 `generate-tests`。

`tests_generated` 后，运行时必须按产物事实扫描测试记录和 `output/test-reports/T-XXX.md`：

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

日志写入必须遵守 `contracts/journal.md` 的日期归档约束：日期章节按 `YYYY-MM-DD` 升序排列；当天已有日期标题时复用并追加到该章节末尾；当天没有日期标题时只在文件末尾新增日期章节；不得在旧日期标题和其日志之间插入新日期标题。

## `CHANGELOG.md` 更新

`CHANGELOG.md` 只用于归档已解决的人工决策，不作为普通活动日志。

## 上游产物修改规则

下游能力不得静默改写上游产物。实现阶段发现规格或设计错误时，应在报告中记录偏离；如果需要人工决策，则同时写入 `ISSUES.md`。
