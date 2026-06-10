# AIWorkFlow 门禁规则

## 作用

门禁是在状态改变前执行的确定性检查。它不评价需求质量、方案质量或代码正确性，只判断当前能力是否具备必要的工作空间状态和输入产物。

## 结果等级

| 等级 | 含义 | 运行时行为 |
|---|---|---|
| `pass` | 必要输入存在，状态一致 | 继续执行 |
| `warn` | 存在非阻塞问题或待决策项 | 明确提示；仅在规则允许时继续 |
| `fail` | 缺少必要输入或状态矛盾 | 停止并给出修复建议 |

## 通用门禁

所有会改变状态的操作前必须检查：

- `CONTEXT.md` 存在。
- `AGENT.md` 存在；缺失时进入工作空间修复建议。
- `ISSUES.md` 存在；缺失时进入工作空间修复建议。
- `REVISIONS.md` 存在；缺失时进入工作空间修复建议。
- `JOURNAL.md` 和 `CHANGELOG.md` 存在；缺失时进入工作空间修复建议。
- `prd/` 和 `output/` 存在。
- `CONTEXT.md` 中当前阶段和下一步可识别，下一步应使用运行时能力名称。
- `CONTEXT.md` 包含 `待处理产物` 字段，且待处理产物列表与阶段产物审核状态一致。
- `ISSUES.md` 中问题编号唯一。
- `REVISIONS.md` 中修订编号唯一。

待决策问题默认是 `warn`。如果待决策问题直接影响当前请求能力或必要产物，则升级为 `fail`。

通用门禁中的确定性结构检查应优先委托当前 skill 目录下的 `tools/validate.py`。Agent 只处理校验器无法判断的语义问题、影响范围判断和人工决策。

## 分能力门禁

| 能力 | 必要条件 |
|---|---|
| `analyze-requirements` | `prd/` 存在，且至少包含一个 `.md`、`.txt` 或 `.pdf` 文件 |
| `design-solution` | `output/analysis.md` 存在，且审核状态为 `已确认` |
| `generate-specs` | `output/design.md` 和 `output/analysis.md` 存在，且二者审核状态均为 `已确认` |
| `implement-code` | `CONTEXT.md` 中存在代码仓库路径，且路径非空、不是 `无`、可访问；`output/design.md` 中每个任务都有对应 `output/specs/T-XXX.md`，且所有目标规格审核状态均为 `已确认` |
| `generate-tests` | `CONTEXT.md` 中存在代码仓库路径，且路径非空、不是 `无`、可访问；至少存在一个已实现但未测试的任务；对应 `output/specs/T-XXX.md` 和 `output/report-T-XXX.md` 存在，且规格和代码报告审核状态均为 `已确认` |
| `review-artifact` | 存在至少一个阶段产物审核状态为 `待审核` 或 `需修改` |

## 决策处理门禁

处理 `Q-XXX` 前必须检查：

- `ISSUES.md` 中存在目标 `Q-XXX`，且编号唯一。
- 目标问题包含非空 `人工决策`。
- 目标问题未标记为 `状态：已解决`。
- 决策影响的产物或代码范围可识别。

任一条件不满足都是 `fail`。

## 任务索引门禁

以 `contracts/context.md` 为任务索引解析依据。

任务完成事实以阶段产物及审核状态为准，`CONTEXT.md` 仅作为状态快照。`CONTEXT.md` 与产物事实冲突时是状态不一致，应进入 `blocked_by_inconsistent_state` / `fix-workspace`，不得信任快照继续推进。

- 任务编号重复是 `fail`。
- 规格索引中列出任务但缺少 `output/specs/T-XXX.md` 是 `warn`；当请求实现该任务时是 `fail`。
- 任务标记已实现但缺少 `output/report-T-XXX.md` 是 `warn`；当测试依赖该任务时是 `fail`。
- 任务标记已测试但缺少 `output/test-report-T-XXX.md` 是 `warn`。
- 任务标记已实现但 `output/report-T-XXX.md` 审核状态不是 `已确认` 是 `warn`；当测试依赖该任务时是 `fail`。
- 任务标记已测试但 `output/test-report-T-XXX.md` 审核状态不是 `已确认` 是 `warn`。

## 审核状态门禁

以 `contracts/review-status.md` 为审核状态解析依据。

- 缺少 `## 审核状态` 的阶段产物不得进入下一步。
- 对下游阶段能力而言，审核状态为 `待审核` 时必须停止，并提示用户审核确认或提出修订。
- 对下游阶段能力而言，审核状态为 `需修改` 时必须停止，并提示用户补充或执行 `REVISIONS.md` 中的修订。
- 只有审核状态为 `已确认` 的产物才能作为下游阶段能力输入。
- `review-artifact` 以存在 `待审核` 或 `需修改` 产物为通过条件，不受上述下游能力门禁阻塞。
- `下一步=review-artifact` 时，不得执行生成能力；只能处理确认、修订或输出待审核清单。
- 存在 `待审核` 或 `需修改` 产物时，`CONTEXT.md` 的 `待处理产物` 必须列出全部目标；缺失或不一致是状态不一致。

## 修复建议

每个 `fail` 必须输出：

- 失败检查项
- 为什么阻塞当前动作
- 最小修复动作
- 修复后建议执行的 `wf` 命令
