# AIWorkFlow

基于工作空间的 AI 辅助开发流程。通过 `wf` 主入口读取工作空间状态、运行时规则和能力契约，让 Agent 在共享上下文中推进，支持跨会话恢复和人工决策收敛。

## 核心理念

- **运行时入口**：用户主要执行 `wf`，由主入口判断当前状态和下一步
- **共享上下文**：Agent 加载 AGENT + CONTEXT + ISSUES + REVISIONS + JOURNAL，按工作空间规则行动
- **能力契约**：需求分析、技术设计、规格、代码、测试作为能力保留，不再依赖用户手动串联
- **问题收敛**：任何能力发现问题写入 ISSUES，人工决策后自动执行并归档
- **人工审核**：每个阶段产物生成后必须由用户审核确认，确认前不得进入下一步
- **跨会话恢复**：JOURNAL 持续记录进度，下次启动无缝接续

## 技能入口

| Skill | 用途 |
|---|---|
| `wf` | 主入口：继续、下一步、处理问题、生成代码、生成测试、状态推进 |
| `wf-init` | 初始化工作空间 |
| `wf-status` | 状态与健康检查，不落盘 |

## Skill 结构

| 路径 | 职责 |
|---|---|
| `wf/SKILL.md` | 工作流主入口 |
| `wf/runtime.md` | 工作流通用读写规则 |
| `wf/state-machine.md` | 状态和事件转移 |
| `wf/guards.md` | 执行前门禁 |
| `wf/capabilities/` | 阶段能力契约 |
| `wf/contracts/` | 产物格式契约，包含 `REVISIONS.md` 修订契约和审核状态契约 |
| `wf/tools/validate.py` | `wf` 内置校验器，用于状态改变前的确定性硬门禁 |
| `wf/tools/rebuild_context.py` | 根据阶段产物事实重建 `CONTEXT.md` 状态快照 |
| `wf/tools/render_review_dashboard.py` | 根据工作空间事实渲染根目录 `dashboard.html` 人工检视页 |
| `wf-status/tools/validate.py` | `wf-status` 内置校验器，用于只读健康检查 |
| `tools/validator_source/validate.py` | 校验器维护源，通过同步脚本复制到各 skill 目录 |
| `scripts/sync_validator_tools.py` | 同步校验器到 `wf/` 和 `wf-status/` skill 目录 |
| `wf-init/SKILL.md` | 工作空间初始化入口 |
| `wf-init/templates/` | 工作空间初始化模板 |

## 工作空间

### 目录结构

```
./
├── README.md           ← 工作空间说明
├── AGENT.md            ← Agent 运行约束
├── CONTEXT.md          ← 需求概要、当前阶段、代码产出、测试记录
├── ISSUES.md           ← 待澄清问题，按阶段分组
├── REVISIONS.md        ← 用户主动提出的产物修订
├── JOURNAL.md          ← 工作日志，每操作一记
├── CHANGELOG.md        ← 已解决决策的时间线归档
├── dashboard.html      ← 脚本生成的人工检视快照
├── prd/                ← 原始 PRD 文件副本
└── output/
    ├── analysis.md     ← 结构化需求分析
    ├── design.md       ← 任务拆解 + 技术方案
    ├── specs/          ← 开发规格
    │   └── T-XXX.md
    ├── reports/        ← 代码生成报告
    │   └── T-XXX.md
    └── test-reports/   ← 测试报告
        └── T-XXX.md
```

### 文件职责

| 文件 | 职责 | 写入时机 |
|------|------|---------|
| `CONTEXT.md` | 需求概要、当前阶段、下一步、待处理产物、代码产出、测试记录 | 阶段推进或状态快照重建时更新 |
| `ISSUES.md` | 待人工决策的问题，按阶段分组 | 发现问题时写入 |
| `REVISIONS.md` | 用户主动提出的产物修订意见 | 用户通过对话或文件提出修订时写入 |
| `JOURNAL.md` | 工作进度日志 | 每完成一个操作追加 |
| `CHANGELOG.md` | 已解决决策归档 | 问题解决时追加 |

### 运行时一致性

阶段产物及其审核状态是工作流事实源，`CONTEXT.md` 是运行时生成的状态快照。任务是否有规格、是否已实现、是否已测试，分别以对应规格、代码报告、测试报告存在且审核状态为 `已确认` 为准。

`validate.py` 负责确定性结构检查和动作硬门禁；`rebuild_context.py` 只根据产物事实重建 `CONTEXT.md`，不得修改 `output/` 阶段产物、`ISSUES.md`、`REVISIONS.md` 或代码仓库。

`dashboard.html` 是由 `wf/tools/render_review_dashboard.py` 生成的只读人工检视页面，可纳入版本管理，但不作为流程事实源。它从 `CONTEXT.md`、`ISSUES.md`、`REVISIONS.md`、`JOURNAL.md`、`CHANGELOG.md`、`prd/` 和 `output/` 提取工作空间状态、PRD、需求、待办、任务、产物、日志和归档信息；冲突时始终以 Markdown 文件和阶段产物为准。

`wf` 和 `wf-status` 各自使用 skill 目录内的 `tools/validate.py`。维护时只修改 `tools/validator_source/validate.py`，再执行：

```text
python scripts/sync_validator_tools.py
```

同步到两个 skill 目录，避免校验规则分叉。

### 工作规范

**写操作规则：**

| 场景 | 文件 | 位置 | 格式 |
|------|------|------|------|
| 发现问题 | `ISSUES.md` | 对应阶段下按 Q-XXX 升序插入 | 问题/AI建议/影响/提出/人工决策/状态 |
| 用户提出修订 | `REVISIONS.md` | `## 待处理` 下按 R-XXX 升序插入 | 目标产物/修订类型/用户意见/影响范围/状态 |
| 问题解决 | `CHANGELOG.md` | 复用当天日期章节并追加；新日期只在文件末尾新增 | `### HH:MM — 摘要（来自 ISSUES.md Q-XXX）` |
| 阶段推进 | `CONTEXT.md` | `## 当前状态` 更新 | 阶段/下一步 |
| 操作完成 | `JOURNAL.md` | 复用当天日期章节并追加；新日期只在文件末尾新增 | HH:MM 时间戳 + 内容 |
| 人工检视页刷新 | `dashboard.html` | 工作空间根目录整体覆盖 | 由 `render_review_dashboard.py` 生成，不手工编辑 |

**问题收敛：**

1. 任何 skill 发现问题 → 写入 `ISSUES.md`，状态「待决策」
2. 用户填写「人工决策」
3. 用户要求处理时，Agent 读取 `ISSUES.md` 找到目标 Q-xxx 条目
4. 按决策执行，完成后：
   - 更新受影响的产物文件
   - 在 `CHANGELOG.md` 末尾追加归档：

     ```
     ## YYYY-MM-DD

     ### HH:MM — [问题简述]（来自 ISSUES.md Q-xxx）

     - **问题：** [原文照搬]
     - **决策：** [人工决策内容]
     - **影响：** [原文照搬]
     - **处理：** [已更新产物]
     ```

   - 从 `ISSUES.md` 删除该 Q-xxx 条目
   - 在 `JOURNAL.md` 追加操作日志

**修订收敛：**

1. 用户通过对话提出明确产物修订 → 写入 `REVISIONS.md` 的 `## 待处理`
2. 用户执行 `wf`
3. Agent 读取待处理 R-XXX 条目并同步目标产物和受影响下游
4. 完成后将 R-XXX 移入 `## 已处理`，补充处理结果、更新产物和处理时间
5. 在 `JOURNAL.md` 追加操作日志

**人工审核：**

1. Agent 生成或修订 `output/analysis.md`、`output/design.md`、`output/specs/T-XXX.md`、`output/reports/T-XXX.md` 或 `output/test-reports/T-XXX.md` 后，产物状态为 `待审核`
2. 此时 `CONTEXT.md` 的下一步为 `review-artifact`，不会重复执行生成能力
3. 用户审核后，可以直接说“确认通过 analysis”或“这个规格需要修改”
4. 确认通过时，Agent 先校验产物契约，再将产物审核状态改为 `已确认` 并推进状态机
5. 需要修改时，Agent 将意见写入 `REVISIONS.md`，收敛后重新进入 `待审核`

**阶段推进：**

阶段推进由 `wf` 根据自身目录下的 `state-machine.md` 统一处理。阶段能力不再作为独立 skill 暴露，而是放在 `wf/capabilities/` 中由 `wf` 按需加载。

**跨会话恢复：**

读 `JOURNAL.md` 最后一条 → 了解上次进度，继续工作。

## 快速开始

```
# 1. 创建并进入一个空目录，然后初始化工作空间
执行 wf-init

# 2. 继续工作流
执行 wf

# 3. 随时查看
wf-status
```

> 如果初始化时填写代码仓库为“无”，流程可以推进到规格生成；代码实现和测试生成需要补充有效代码仓库路径后再执行 `wf`。
