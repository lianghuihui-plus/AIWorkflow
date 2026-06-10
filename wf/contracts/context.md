# 产物契约：CONTEXT.md

## 路径

`CONTEXT.md`

## 必需章节

- `# 工作空间上下文 — {项目名称}`
- `## 需求概要`
- `## 当前状态`
- `## 项目约束`
- `## 代码产出`
- `## 测试记录`

## 当前状态字段

`## 当前状态` 必须包含：

```markdown
- 阶段：{阶段}
- 待决策：{数量} 项（详见 ISSUES.md）
- 下一步：{能力名}
- 待处理产物：
  - 暂无
- 规格：
  - T-001 — {标题}（{修改点数量} 个修改点）
```

规格生成前，`规格` 可以为 `暂无`。

`待处理产物` 记录所有审核状态为 `待审核` 或 `需修改` 的阶段产物。没有待处理产物时必须写 `暂无`。

## 阶段与下一步取值

`阶段` 必须使用 `state-machine.md` 中定义的状态值：

- `initialized`
- `requirements_analyzed`
- `design_ready`
- `specs_ready`
- `implementation_in_progress`
- `implementation_done`
- `tests_done`
- `blocked_by_decision`
- `blocked_by_missing_input`
- `blocked_by_inconsistent_state`

`下一步` 必须使用以下取值之一：

- `analyze-requirements`
- `design-solution`
- `generate-specs`
- `implement-code`
- `generate-tests`
- `review-artifact`
- `status`
- `resolve-decision`
- `fix-workspace`

初始化后的标准状态为：

```markdown
- 阶段：initialized
- 下一步：analyze-requirements
```

终态标准状态为：

```markdown
- 阶段：tests_done
- 下一步：status
```

阻塞状态必须在 `下一步` 中写明解除动作：待人工决策使用 `resolve-decision`，缺输入或状态不一致使用 `fix-workspace`。

产物生成或实质修订后，阶段保持为生成前的活动状态，`下一步` 必须写为 `review-artifact`。只有目标产物审核状态为 `已确认` 后，运行时才能根据状态机推进到下一阶段。

存在待审核或需修改产物时，`下一步` 必须写为 `review-artifact`，`待处理产物` 必须列出全部目标：

```markdown
- 待处理产物：
  - output/analysis.md（待审核）
  - output/specs/T-001.md（需修改）
```

## 状态事实源

`CONTEXT.md` 是运行时生成的状态快照，不是任务完成事实的最终来源。冲突时以阶段产物及其审核状态为准。

`## 项目约束` 是初始化输入，运行时重建时必须保留。`## 需求概要` 从 `output/analysis.md` 的 `## 需求概要` 同步生成；需求分析能力不得直接把需求概要写入 `CONTEXT.md` 作为权威内容。

| 事实 | 权威来源 |
|---|---|
| 需求分析是否可进入设计 | `output/analysis.md` 存在，且审核状态为 `已确认` |
| 技术方案是否可进入规格 | `output/design.md` 存在，且审核状态为 `已确认` |
| 任务是否有规格 | `output/specs/T-XXX.md` 存在，且审核状态为 `已确认` |
| 任务是否已实现 | `output/report-T-XXX.md` 存在，且审核状态为 `已确认` |
| 任务是否已测试 | `output/test-report-T-XXX.md` 存在，且审核状态为 `已确认` |
| 是否停在审核阶段 | 存在任一审核状态为 `待审核` 或 `需修改` 的阶段产物 |

当 `CONTEXT.md` 与产物事实冲突时，应进入 `blocked_by_inconsistent_state` / `fix-workspace`，并通过 `rebuild_context.py` 按产物事实重建状态快照。

## 项目约束

```markdown
- 平台：{平台}
- 代码仓库：{路径或无}
```

## 代码产出表

```markdown
| 任务 | 状态 |
|---|---|
| T-001 | ✅ 已完成 |
```

## 测试记录表

```markdown
| 任务 | 测试文件 | 状态 |
|---|---|---|
| T-001 | tests/Xxx.test.ts | ✅ 已完成 |
```

## 解析规则

- 任务编号格式为 `T-[0-9]{3}`。
- `T-XXX` 占位符不算真实任务。
- 待处理产物只解析 `## 当前状态` 下的 `- 待处理产物：` 区域。
- 规格索引只解析 `## 当前状态` 下的 `- 规格：` 区域。
- 规格索引中只有明确包含 `✅ 已实现` 的任务才视为已实现；`✅ 已确认` 只能表示规格已确认，不代表代码已实现。
- 包含 `✅ 已测试` 的任务，只有对应测试报告存在且审核状态为 `已确认`，才视为已测试。

## 写入规则

- 阶段和下一步只能由运行时更新。
- `## 需求概要` 由运行时或 `rebuild_context.py` 从 `output/analysis.md` 同步生成。
- `## 项目约束` 由初始化写入，重建时保留原值。
- 待处理产物只能由运行时或 `rebuild_context.py` 根据产物审核状态更新。
- 能力只生成或修订产物；完成事件只能由运行时在产物审核确认后产生。
- 存在待审核或需修改产物时，`下一步` 必须为 `review-artifact`，不得写为下游能力。
- 存在待审核或需修改产物时，`待处理产物` 必须列出全部目标；不存在时必须写 `暂无`。
- 缺少 `output/report-T-XXX.md` 时，不得标记任务已实现。
- 缺少 `output/test-report-T-XXX.md` 时，不得标记任务已测试。
- `output/report-T-XXX.md` 审核状态不是 `已确认` 时，不得标记任务已实现。
- `output/test-report-T-XXX.md` 审核状态不是 `已确认` 时，不得标记任务已测试。
