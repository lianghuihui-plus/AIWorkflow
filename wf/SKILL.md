---
name: wf
description: 当用户在 AIWorkFlow 工作空间中要求继续、下一步、推进流程、分析需求、生成方案、生成规格、实现任务、生成测试、处理 Q-XXX 待决策、收敛用户修订或修复阻塞状态时使用。
---

# AIWorkFlow 主入口

`wf` 是 AIWorkFlow 的主入口。用户不需要逐个调用阶段 skill；本入口根据工作空间状态、运行时规则、门禁和能力契约选择下一步。

## 适用场景

用户表达以下意图时使用：

- 继续工作流、下一步、推进当前项目
- 分析需求、写方案、生成规格
- 实现下一个任务、生成测试
- 处理 `ISSUES.md` 中的 `Q-XXX`
- 记录或处理用户对产物的修订意见
- 审核、确认或退回阶段产物
- 查看状态、修复不一致工作空间

## 核心原则

- 当前目录存在 `CONTEXT.md` 时，必须按 AIWorkFlow 模式工作。
- 任何状态改变前必须读取工作空间状态并执行门禁检查。
- 不确定项写入 `ISSUES.md`，不得替用户做决策。
- 能力只负责产出，状态推进由运行时和状态机决定。
- 用户通过对话提出明确产物修订时，先写入 `REVISIONS.md`，再执行收敛。
- 实质操作后必须更新 `CONTEXT.md` 并追加 `JOURNAL.md`。

## 步骤 1：定位工作空间

如果当前目录存在 `CONTEXT.md`，使用当前目录。

如果当前目录不存在 `CONTEXT.md`：

1. 用户给出了 workspace 路径 → 切换到该路径。
2. 用户请求新建工作空间 → 提示用户进入一个空目录后执行 `wf-init`。
3. 否则询问用户工作空间路径，或提示先在空目录执行 `wf-init`。

存在 `CONTEXT.md` 但缺少 `AGENT.md`、`ISSUES.md`、`REVISIONS.md`、`JOURNAL.md`、`CHANGELOG.md`、`prd/` 或 `output/` 时，不继续阶段能力，输出修复建议。

## 步骤 2：定位并加载运行时资料

运行时资料随 `wf` skill 安装，位于当前 skill 目录内：

- `runtime.md`
- `state-machine.md`
- `guards.md`
- `capabilities/`
- `contracts/`

如果这些文件缺失，提示检查 `wf` skill 目录软链接或修复 AIWorkFlow，不要猜测规则。

按顺序读取：

1. `runtime.md`
2. `state-machine.md`
3. `guards.md`
4. 工作空间 `AGENT.md`
5. 工作空间 `CONTEXT.md`
6. 工作空间 `ISSUES.md`
7. 工作空间 `REVISIONS.md`
8. 工作空间 `JOURNAL.md` 最近记录

## 步骤 3：识别用户意图

| 用户意图 | 目标动作 |
|---|---|
| 状态、概览、健康检查、validate | 使用 `wf-status` 的检查规则输出状态，不落盘 |
| 继续、下一步 | 根据 `CONTEXT.md` 下一步和状态机选择能力 |
| 审核产物、确认通过、同意进入下一步 | 执行 `review-artifact`，先校验产物契约，再更新审核状态和 `CONTEXT.md` |
| 处理 `Q-XXX` | 读取 `ISSUES.md`，按人工决策执行并归档 |
| 用户提出修改、修订产物、调整产物内容 | 先写入 `REVISIONS.md`，再按修订收敛规则处理 |
| 生成下一个任务、实现、写代码 | 请求 `implement-code`，但必须先通过门禁 |
| 写测试、补测试 | 请求 `generate-tests`，但必须先通过门禁 |
| 初始化、新项目 | 提示用户进入空目录后执行 `wf-init` |

## 步骤 4：执行门禁检查

按 `guards.md` 检查：

- 工作空间完整性
- 当前阶段和下一步是否可识别
- 待决策项是否阻塞当前动作
- 目标能力所需输入是否存在
- 任务索引、报告、测试报告是否自洽

门禁结果为 `fail` 时停止，输出失败原因和最小修复建议。

门禁结果为 `warn` 时说明风险。只有规则允许继续，或用户明确要求继续，才执行能力。

## 步骤 5：选择并加载能力契约

根据状态机和用户意图加载一个能力文件：

如果 `CONTEXT.md` 的下一步是 `review-artifact`，不得选择阶段生成能力。此时只能处理人工确认、修订收敛，或输出待审核产物清单。

| 能力 | 文件 |
|---|---|
| `analyze-requirements` | `capabilities/analyze-requirements.md` |
| `design-solution` | `capabilities/design-solution.md` |
| `generate-specs` | `capabilities/generate-specs.md` |
| `implement-code` | `capabilities/implement-code.md` |
| `generate-tests` | `capabilities/generate-tests.md` |

同时加载该能力需要的 `contracts/*.md`。

## 步骤 6：按动作加载产物契约

| 动作 | 必读能力 | 必读产物契约 |
|---|---|---|
| 需求分析 | `capabilities/analyze-requirements.md` | `contracts/analysis.md`、`contracts/review-status.md`、`contracts/context.md`、`contracts/issues.md`、`contracts/journal.md` |
| 技术设计 | `capabilities/design-solution.md` | `contracts/design.md`、`contracts/review-status.md`、`contracts/context.md`、`contracts/issues.md`、`contracts/journal.md` |
| 规格生成 | `capabilities/generate-specs.md` | `contracts/spec.md`、`contracts/review-status.md`、`contracts/context.md`、`contracts/issues.md`、`contracts/journal.md` |
| 代码实现 | `capabilities/implement-code.md` | `contracts/spec.md`、`contracts/code-report.md`、`contracts/review-status.md`、`contracts/context.md`、`contracts/issues.md`、`contracts/journal.md` |
| 测试生成 | `capabilities/generate-tests.md` | `contracts/test-report.md`、`contracts/review-status.md`、`contracts/context.md`、`contracts/issues.md`、`contracts/journal.md` |
| 处理决策 | 无 | `contracts/issues.md`、`contracts/changelog.md`、`contracts/journal.md`、`contracts/context.md` |
| 处理修订 | 无 | `contracts/revisions.md`、目标产物契约、`contracts/review-status.md`、`contracts/context.md`、`contracts/issues.md`、`contracts/journal.md` |

## 步骤 7：执行能力

按能力契约执行具体工作：

- 使用契约中的输入、输出、不确定项、完成标准。
- 不使用旧阶段 skill 的管道式“下一步推进”规则。
- 发现需人工判断的问题，写入 `ISSUES.md` 后停止。
- 偏离上游设计或规格时，写入当前阶段报告；需要用户判断时同时写入 `ISSUES.md`。
- 新生成或实质更新阶段产物后，将产物审核状态写为 `待审核`，不得直接推进下一阶段。

## 步骤 8：处理人工审核

当用户明确表示产物审核通过、确认、可以进入下一步时：

1. 识别用户确认的目标产物；不明确时先询问。
2. 读取目标产物对应的 `contracts/*.md` 和 `contracts/review-status.md`。
3. 按产物契约质量规则完整校验目标产物；校验失败时不得确认，按问题类型写入 `ISSUES.md` 或 `REVISIONS.md`。
4. 校验通过后，将目标产物 `## 审核状态` 改为 `已确认`，填写审核人和审核时间。
5. 按 `runtime.md` 和 `state-machine.md` 产生对应完成事件并更新 `CONTEXT.md`。
6. 追加 `JOURNAL.md`。

## 步骤 9：统一落盘

能力执行完成后，由运行时统一处理：

- 更新 `CONTEXT.md` 的阶段、下一步、任务索引、代码产出或测试记录。
- 追加 `JOURNAL.md`。
- 必要时写入 `ISSUES.md`。
- 处理修订时归档到 `REVISIONS.md` 的已处理区。
- 处理 `Q-XXX` 时归档到 `CHANGELOG.md` 并从 `ISSUES.md` 删除。

## 步骤 10：输出结果

输出内容必须包含：

- 本次识别到的当前阶段和目标能力。
- 门禁结果。
- 生成或修改的产物。
- 新增或解决的问题。
- 新增或处理的修订。
- 待审核或已确认的产物。
- 下一步建议。

如果没有执行状态改变，明确说明“不落盘”。

