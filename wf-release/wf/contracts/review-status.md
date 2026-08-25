# 产物契约：审核状态

## 适用范围

以下阶段产物必须包含 `## 审核状态`：

- `output/analysis.md`
- `output/design.md`
- `output/specs/T-XXX.md`
- `output/reports/T-XXX.md`
- `output/test-reports/T-XXX.md`

## 格式

```markdown
## 审核状态

- 状态：待审核
- 审核人：
- 审核时间：
- 修订来源：
```

## 状态取值

- `待审核`：Agent 已生成或更新产物，等待用户审核。
- `需修改`：用户认为产物需要调整，具体修订应写入 `REVISIONS.md`。
- `需更新`：该产物曾经确认过，但上游产物已发生影响下游的变更，当前产物必须重新生成或重新同步后才能再次作为完成事实。
- `已确认`：用户确认产物可进入下一步。

## 写入规则

- Agent 每次新生成或实质更新产物后，必须将状态写为 `待审核`。
- 产物进入 `待审核` 后，运行时必须按 `runtime.md` 将 `CONTEXT.md` 的下一步写为 `review-artifact`，并将该产物列入 `CONTEXT.md` 的 `待处理产物`。
- 用户通过对话提出修改意见时，修订记录由运行时按 `runtime.md` 写入 `REVISIONS.md`，目标产物审核状态改为 `需修改`。
- 产物进入 `需修改` 后，运行时必须按 `runtime.md` 保持 `CONTEXT.md` 下一步为 `review-artifact`，并将该产物列入 `CONTEXT.md` 的 `待处理产物`。
- `wf` 处理完相关修订后，目标产物审核状态应回到 `待审核`，等待用户重新确认。
- 上游产物发生实质更新后，运行时必须按 `runtime.md` 将受影响且当前为 `已确认` 的下游产物改为 `需更新`，清空审核人和审核时间，并在 `修订来源` 记录触发失效的上游产物。
- `需更新` 不进入 `CONTEXT.md` 的 `待处理产物` 列表；它表示下游产物需要重新执行生成能力，而不是等待人工审核。
- 只有用户明确确认通过，且目标产物通过对应产物契约校验后，才能将状态写为 `已确认`，并填写审核人和审核时间。
- 未达到 `已确认` 的产物不得作为进入下一阶段的门禁通过依据。
- 产物审核状态改为 `已确认` 后，`CONTEXT.md` 的 `待处理产物` 列表由运行时按 `runtime.md` 重建。

## 门禁规则

- `output/analysis.md` 未 `已确认` 时，不得执行 `design-solution`。
- `output/design.md` 未 `已确认` 时，不得执行 `generate-specs`。
- `output/specs/T-XXX.md` 未 `已确认` 时，不得执行对应任务的 `implement-code`。
- `output/reports/T-XXX.md` 未 `已确认` 时，不得执行对应任务的 `generate-tests`。
- `output/test-reports/T-XXX.md` 未 `已确认` 时，不得将对应任务标记为测试完成。
