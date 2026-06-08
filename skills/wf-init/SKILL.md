---
name: wf-init
description: 工作空间初始化。创建 workspace 目录，拷贝 PRD 文件，生成所有初始文件（README、CONTEXT、ISSUES、JOURNAL、CHANGELOG、AGENT）。每次开始新项目时执行。继续已有工作空间只需让 Agent 读 README.md。
---

# 工作空间初始化

创建新的工作空间目录并生成所有初始文件。

> 继续已有工作空间：直接让 Agent 读 `{workspace}/README.md`，无需执行本 skill。

## 执行流程

### Step 1：交互问答

按表格顺序，一问一答收集。每问一个，等待用户回答后再继续。**Q3（PRD 路径）回答后，先执行 Step 2 处理路径，再继续 Q4。**

| 序号 | 提示语 | 必填 | 校验 |
|------|--------|------|------|
| 1 | `项目名称叫什么？` | 是 | 不能为空 |
| 2 | `开发平台是哪个？（如：HarmonyOS / iOS / Android / Web / 其他）` | 是 | 不能为空 |
| 3 | `原始 PRD 文档路径是？` | 是 | 文件或目录必须存在 |
| 4 | `项目代码路径是？（没有的话填"无"）` | 否 | 如提供，目录必须存在。填"无"则跳过 |
| 5 | `工作空间根目录是？我会在该目录下创建 workspace-{项目名称}。` | 是 | 父目录不存在则自动创建 |

**校验失败 → 修正后继续当前问，不跳过。**

### Step 2：PRD 路径处理

拿到 PRD 路径后，自动判断并记录完整文件列表，**暂不拷贝**：
- **是文件**：记录该文件绝对路径。
- **是目录**：扫描目录下所有文件（.md / .txt / .pdf），逐条记录绝对路径。
- 不向用户确认，直接进入下一问。

### Step 3：工作空间目录命名

目录名使用 `workspace-{项目名称}` 格式。如目标位置已存在同名目录，提示用户确认是否覆盖或指定其他名称。

### Step 4：创建工作空间目录

在用户指定的位置创建 `workspace-{项目名称}` 目录，包含以下子目录：

```
workspace-{项目名称}/
├── prd/        ← 原始 PRD 文件副本
└── output/     ← 各阶段产物
```

### Step 5：拷贝 PRD 文件

将 Step 2 中记录的全部 PRD 文件拷贝到 `prd/` 目录下，保持原文件名。拷贝后，后续所有生成文件中的 PRD 来源均指向 `prd/` 下的副本。

### Step 6：生成 README.md

生成工作空间入口文件。模板如下，其中变量替换规则：

- `{项目名称}` → Step 1 输入的项目名称
- `{平台}` → Step 1 输入的开发平台
- `{代码路径信息}` → 有代码路径则 `仓库：{路径}`，填"无"则 `无代码仓库`
- `{PRD 份数}` → Step 2 记录的文件数量

```markdown
# {项目名称}

> {平台} · {代码路径信息} · PRD：{PRD 份数} 份 · 最后更新：YYYY-MM-DD

## 工作流

按顺序推进，每阶段一个 skill：

| # | 阶段 | Skill | 产出 |
|---|------|-------|------|
| 1 | 需求分析 | `wf-prd-analyzer` | `output/analysis.md` |
| 2 | 技术方案 | `wf-tech-designer` | `output/design.md` |
| 3 | 开发规格 | `wf-spec-generator` | `output/specs/T-XXX.md` |
| 4 | 代码生成 | `wf-code-generator` | `output/report-T-XXX.md` + 写入代码仓库 |
| 5 | 测试 | `wf-test-generator` | `output/test-report-T-XXX.md` + 写入测试代码 |

辅助：`wf-git-commit`（提交）· `wf-status`（状态与健康检查）

编码规范见 `AGENT.md`。需要人工决策的问题见 `ISSUES.md`。

## 待决策

详见 `ISSUES.md`

## 文件索引

| 文件 | 内容 |
|------|------|
| `CONTEXT.md` | 需求概要、当前阶段、下一步 |
| `ISSUES.md` | 待澄清问题，需人工逐条决策 |
| `JOURNAL.md` | 工作日志：上次会话进度、文件变动、备忘 |
| `CHANGELOG.md` | 已解决的变更和决策归档 |
| `AGENT.md` | 编码规范、平台约束、项目约定 |

## 目录

| 目录 | 说明 |
|------|------|
| `prd/` | 原始 PRD 文件 |
| `output/` | 各阶段产物 |

## 产物

| 文件 | 说明 |
|------|------|
| `output/analysis.md` | 结构化需求分析 |
| `output/design.md` | 任务拆解 + 技术方案 |
| `output/specs/T-XXX.md` | 逐文件编码指令 |
| `output/report-T-XXX.md` | 代码生成结果、偏离说明 |
| `output/test-report-T-XXX.md` | 测试用例清单、覆盖情况 |

## 工作规范

### 写操作

| 场景 | 文件 | 写入位置 | 格式 |
|------|------|---------|------|
| 发现问题需人工决策 | `ISSUES.md` | 对应阶段下追加 Q-xxx | 问题/AI建议/影响/状态 |
| 问题已解决 | `CHANGELOG.md` | 文件末尾按日期追加 | 时间线格式 |
| 阶段推进 | `CONTEXT.md` | `## 当前状态` 更新 | 阶段/下一步 |
| 每完成一个操作 | `JOURNAL.md` | 文件末尾按日期追加 | HH:MM 时间戳 + 内容 |

### 阶段推进

| Skill | 完成后 CONTEXT 更新 |
|-------|-------------------|
| `wf-prd-analyzer` | 阶段：需求分析完成，待审核 · 下一步：wf-tech-designer |
| `wf-tech-designer` | 阶段：技术方案完成，待审核 · 下一步：wf-spec-generator |
| `wf-spec-generator` | 阶段：规格生成完成 · 下一步：wf-code-generator |
| `wf-code-generator` | 标注任务 ✅ · 全部完成则 阶段：代码生成完成 · 下一步：wf-test-generator |
| `wf-test-generator` | 标注任务 ✅ · 全部完成则 阶段：测试完成 |

### 问题收敛

1. 任何 skill 发现问题 → 写入 `ISSUES.md`，状态「待决策」
2. 用户在任何时候填写「人工决策」
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
     ```

   - 从 `ISSUES.md` 删除该 Q-xxx 条目
   - 在 `JOURNAL.md` 追加操作日志

### 跨会话恢复

读 `JOURNAL.md` 最后一条 → 了解上次进度，继续工作。
```

### Step 7：生成 CONTEXT.md

生成初始模板，预填平台和代码路径：

```markdown
# 工作空间上下文 — {项目名称}

> 最后更新：YYYY-MM-DD HH:MM
> 当前阶段：未开始

## 需求概要

[执行 wf-prd-analyzer 后填充]

## 当前状态

- 阶段：未开始
- 待决策：0 项（详见 ISSUES.md）
- 下一步：执行 wf-prd-analyzer
- 规格：
  - 暂无

## 项目约束

- 平台：{平台}
- 代码仓库：{代码路径}（无则填"无"）

## 代码产出

| 任务 | 状态 |
|------|------|
| — | — |

> 状态取值：`待开发` / `✅ 已完成`

## 测试记录

| 任务 | 测试文件 | 状态 |
|------|---------|------|
| — | — | — |

> 状态取值：`待测试` / `✅ 已完成`
```

### Step 8：生成 ISSUES.md

```markdown
# 待澄清

> 需人工决策的问题。逐条跟踪，解决后移入 CHANGELOG.md。

## 分析阶段

暂无

## 设计阶段

暂无

## 实现阶段

暂无

## 测试阶段

暂无
```

### Step 9：生成 JOURNAL.md

```markdown
# 工作日志

## YYYY-MM-DD

### HH:MM — 工作空间初始化

- 工作空间创建完成
- 平台：{平台}
- PRD 来源：{PRD 份数} 份
- 代码仓库：{代码路径}（无则填"无"）
```

### Step 10：生成 AGENT.md

根据平台生成初始约束：

```markdown
# Agent 约束

## 平台

{平台}

## 编码规范

[请根据平台和项目需求手动补充编码规范]

## 通用规则

- 遵循 CONTEXT.md 中的项目约束
- 工作空间全局规范已由会话注入，此处不重复
```

### Step 11：初始化 CHANGELOG.md

```markdown
# 变更记录

## YYYY-MM-DD

### HH:MM — 工作空间初始化

- 工作空间创建完成
```

### Step 12：完成提示

```
✅ 工作空间初始化完成

项目名称：XXX
目标平台：XXX
PRD 文档：X 份
项目代码：有/无
工作空间目录：{路径}/workspace-xxx/

📁 已创建目录结构（含 prd/、output/）
📄 已生成 README.md（入口文件）
📄 已生成 CONTEXT.md
📄 已生成 ISSUES.md
📄 已生成 JOURNAL.md
📄 已生成 AGENT.md
📄 已初始化 CHANGELOG.md

下一步：执行 wf-prd-analyzer 开始需求分析
```
