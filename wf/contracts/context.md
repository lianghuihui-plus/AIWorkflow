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
- 规格：
  - T-001 — {标题}（{修改点数量} 个修改点）
```

规格生成前，`规格` 可以为 `暂无`。

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
- 规格索引只解析 `## 当前状态` 下的 `- 规格：` 区域。
- 规格索引中只有明确包含 `✅ 已实现` 的任务才视为已实现；`✅ 已确认` 只能表示规格已确认，不代表代码已实现。
- 包含 `✅ 已测试` 的任务，只有对应测试报告存在且审核状态为 `已确认`，才视为已测试。

## 写入规则

- 阶段和下一步只能由运行时更新。
- 能力只生成或修订产物；完成事件只能由运行时在产物审核确认后产生。
- 存在待审核或需修改产物时，`下一步` 必须为 `review-artifact`，不得写为下游能力。
- 缺少 `output/report-T-XXX.md` 时，不得标记任务已实现。
- 缺少 `output/test-report-T-XXX.md` 时，不得标记任务已测试。
- `output/report-T-XXX.md` 审核状态不是 `已确认` 时，不得标记任务已实现。
- `output/test-report-T-XXX.md` 审核状态不是 `已确认` 时，不得标记任务已测试。
