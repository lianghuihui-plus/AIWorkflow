# 能力：生成测试

## 适用意图

当实现报告已存在，工作空间需要为已完成任务的代码变更生成对应单元测试时使用。

## 前置条件

- 代码仓库路径非空、不是 `无`、可访问。
- 目标 `output/specs/T-XXX.md` 存在。
- 目标 `output/reports/T-XXX.md` 存在。
- 目标任务已实现但尚未测试。

## 输入

- `output/specs/T-XXX.md`：关键行为和修改点。
- `output/reports/T-XXX.md`：实际实现和偏离说明。
- 相关源码文件、已有测试模式和项目测试说明。
- 可选：`<wf-skill-dir>/scripts/test-runners/` 中匹配当前代码仓库的平台测试执行脚本。

## 输出

- 写入代码仓库的测试代码。
- 符合 `contracts/test-report.md` 的 `output/test-reports/T-XXX.md`。
- 审核状态：`待审核`。
- 完成事件：用户确认 `output/test-reports/T-XXX.md` 后，由运行时产生 `tests_generated` 或 `all_tests_completed`。
- 可选：写入 `ISSUES.md` 的测试阶段问题。

## 规则

- 从规格、实现报告和代码变更中提取待覆盖行为。
- 遵循代码仓库已有单元测试框架、目录、命名风格和 mock 方式。
- 为可测试行为生成或更新单元测试，覆盖正常路径、边界条件、异常处理和状态变化。
- 对暂未生成单元测试的行为，在测试报告中记录测试点、状态、原因和后续条件。
- 如果实现报告中的偏离影响预期行为，应测试已接受的实际行为，并记录原因。
- 默认只修改测试代码和测试报告；如需调整业务逻辑代码才能形成稳定测试，写入 `ISSUES.md` 或转入实现修订流程。
- 有可用测试执行脚本时调用脚本执行相关单元测试；脚本缺失或不可用时记录未执行原因。
- 执行失败时，可以进行一次基于明确失败原因的测试代码修正；仍失败时记录失败摘要和下一步建议。
- `generate-tests` 能力只产出或修订测试代码与测试报告；`CONTEXT.md`、`JOURNAL.md`、审核等待状态和完成事件由运行时统一处理。

## 测试执行脚本

平台相关命令由 `<wf-skill-dir>/scripts/test-runners/` 下的可选脚本承载，按平台目录隔离：

```text
<wf-skill-dir>/scripts/test-runners/{platform}/detect.sh
<wf-skill-dir>/scripts/test-runners/{platform}/run-unit.sh
<wf-skill-dir>/scripts/test-runners/{platform}/build-test.sh
```

调用规则：

- 先根据代码仓库特征选择候选平台目录。
- 存在 `detect.sh` 时先执行检测；检测可用后再调用后续脚本。
- 存在且可执行的 `run-unit.sh` 用于执行目标任务相关单元测试。
- 存在且可执行的 `build-test.sh` 用于记录测试相关构建或编译验证。
- 脚本只输出执行摘要、日志路径和退出码，不直接写入工作流产物、审核状态、`CONTEXT.md`、`REVISIONS.md`、`ISSUES.md` 或测试报告。

调用脚本时通过环境变量传递上下文：

```text
AIWF_CODE_REPO
AIWF_WORKSPACE
AIWF_TASK_ID
AIWF_SPEC_PATH
AIWF_REPORT_PATH
AIWF_TEST_REPORT_PATH
AIWF_CHANGED_FILES
AIWF_LOG_DIR
```

## 不确定项

以下情况写入测试阶段问题：

- 预期行为不明确。
- 项目中找不到测试框架或测试目录。
- 缺少必要测试依赖或环境。
- 现有实现无法在不改变对外行为的情况下测试。
- 需要修改业务逻辑代码才能完成单元测试。
- 用户、项目规则或审核意见明确要求执行通过，但缺少可用测试执行脚本。

## 完成标准

- 已写入或更新单元测试文件，或在报告中说明未生成单元测试的原因。
- `output/test-reports/T-XXX.md` 已生成。
- 报告将单元测试映射到关键行为，并列出未生成单元测试的行为。
- 辅助验证记录说明脚本执行结果或未执行原因。
- `output/test-reports/T-XXX.md` 的审核状态为 `待审核`，等待用户确认后才能标记测试完成。
