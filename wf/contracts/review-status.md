# 产物契约：审核状态

## 适用范围

以下阶段产物必须包含 `## 审核状态`：

- `output/analysis.md`
- `output/design.md`
- `output/specs/T-XXX.md`
- `output/report-T-XXX.md`
- `output/test-report-T-XXX.md`

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
- `已确认`：用户确认产物可进入下一步。

## 写入规则

- Agent 每次新生成或实质更新产物后，必须将状态写为 `待审核`。
- 产物进入 `待审核` 后，`CONTEXT.md` 的下一步必须写为 `review-artifact`。
- 用户通过对话提出修改意见时，Agent 必须先写入 `REVISIONS.md`，并将目标产物审核状态改为 `需修改`。
- `wf` 处理完相关修订后，目标产物审核状态仍为 `待审核`，等待用户重新确认。
- 只有用户明确确认通过，且目标产物通过对应产物契约校验后，才能将状态写为 `已确认`，并填写审核人和审核时间。
- 未达到 `已确认` 的产物不得作为进入下一阶段的门禁通过依据。

## 门禁规则

- `output/analysis.md` 未 `已确认` 时，不得执行 `design-solution`。
- `output/design.md` 未 `已确认` 时，不得执行 `generate-specs`。
- `output/specs/T-XXX.md` 未 `已确认` 时，不得执行对应任务的 `implement-code`。
- `output/report-T-XXX.md` 未 `已确认` 时，不得执行对应任务的 `generate-tests`。
- `output/test-report-T-XXX.md` 未 `已确认` 时，不得将对应任务标记为测试完成。
