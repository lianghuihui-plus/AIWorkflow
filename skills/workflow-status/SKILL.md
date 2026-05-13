---
name: workflow-status
description: 扫描工作流目录下所有报告的状态，生成工作流概览文档。当用户要查看进度/状态/概览时使用。
---

# 工作流概览

扫描 `{OUT}/` 下所有阶段报告和 bug 文档的状态，生成 `{OUT}/status.md`。

> 工具型 skill，手动触发，不参与管线。

## 配置读取

### 定位工作流目录

按以下优先级定位 `workflow.yaml` 所在的工作流根目录：

1. **检查当前目录** — 当前工作目录中存在 `workflow.yaml` → 从该目录读取配置
2. **检查会话上下文** — 如本会话中已运行过 `workflow-init` 或其他阶段 skill，且已知工作流目录路径 → 使用该路径
3. **询问用户** — 以上均未找到时，向用户询问：
   > 我需要知道当前工作流目录路径，请提供 workflow-xxx 目录的路径。

验证定位到的目录中存在 `workflow.yaml`；不存在则提示用户先执行 `workflow-init` 初始化。

定位到 `workflow.yaml` 后，立即解析并执行。

### 读取并校验

1. 解析 `workflow.yaml`，校验 YAML 格式
2. 提取 `output.base_dir`（默认 `output`），记为 `OUT`
3. 提取 `project.name`，记为 `PROJECT`

YAML 格式非法导致无法解析 → 终止并告知用户具体错误。

### 配置字段说明

| 配置路径 | 含义 | 必填 |
|---------|------|------|
| `output.base_dir` | 输出根目录 | 是（默认 `output`） |
| `project.name` | 项目名称 | 否 |

---

## 执行流程

### Step 1：扫描管线阶段

读取以下文件的状态字段，文件不存在则状态记为「—」：

| 文件 | 对应阶段 |
|------|---------|
| `{OUT}/requirements.md` | prd-analyzer |
| `{OUT}/tasks.md` | task-decomposer |
| `{OUT}/tech-design.md` | tech-designer |

此外扫描 `{OUT}/specs/README.md`，获取所有任务列表。对每个任务：

- 读取 `{OUT}/specs/T-XXX-spec.md` 的状态 → 确定 task-spec-generator 整体进度
- 读取 `{OUT}/generated/T-XXX-report.md` 的状态 → 确定 code-generator 进度
- 读取 `{OUT}/tests/T-XXX-test-report.md` 的状态 → 确定 unit-test-generator 进度

### Step 2：扫描 Bug

扫描 `{OUT}/bugs/` 目录下所有 `BUG-XXX.md`，读取每条的状态和问题简述。

### Step 3：生成文档

写入 `{OUT}/status.md`：

```markdown
# 工作流概览

> 工作流：[PROJECT]
> 更新时间：YYYY-MM-DD HH:MM

## 管线进度

| 阶段 | 状态 | 待处理 |
|------|------|--------|
| prd-analyzer | [状态] | [待处理项，无则 —] |
| task-decomposer | [状态] | [待处理项] |
| tech-designer | [状态] | [待处理项] |
| task-spec-generator | [状态] | [待处理项] |
| code-generator | [状态] | [待处理项] |
| unit-test-generator | [状态] | [待处理项] |

> 各阶段状态取所有相关报告的汇总值：
> - 全部「已确认/已审核」→ 该列
> - 存在「待审核」→ 待审核，待处理列注明是哪些
> - 全部为「—」→ —

## 任务详情

| 任务 | 标题 | 规格 | 代码 | 测试 |
|------|------|------|------|------|
| [T-001](specs/T-001-spec.md) | [标题] | [状态] | [状态] | [状态] |

> 状态取值：已确认 / 已审核 / 待审核 / —
> 任务 ID 链接到对应 spec 文件，状态非「—」的单元格链接到对应报告

## Bug 列表

| Bug | 状态 | 简述 |
|-----|------|------|
| [BUG-001](bugs/BUG-001.md) | [状态] | [问题简述] |

> 无 bug 时写「无」
```

### Step 4：输出概述

生成文档后，回复用户一段简短概述，包含：

1. **当前状态**：哪些阶段已确认，哪些待审核，哪些未开始
2. **下一步建议**：按管线顺序推荐最靠前的未完成操作，如无未完成事项则建议 `git-commit`

> 概述不超过三句话，不重复文档中的表格细节。
