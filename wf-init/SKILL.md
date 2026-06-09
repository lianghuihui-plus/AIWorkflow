---
name: wf-init
description: 当用户要新建或初始化 AIWorkFlow 工作空间，并且当前目录是空目录、已有 PRD 路径，需要生成 README、CONTEXT、ISSUES、REVISIONS、JOURNAL、CHANGELOG、AGENT 初始文件时使用。
---

# 工作空间初始化

在当前空目录中初始化 AIWorkFlow 工作空间并生成所有初始文件。

> 继续已有工作空间：执行 `wf`，由主入口读取工作空间状态并判断下一步。
> 模板来源：使用当前 skill 目录下的 `templates/`；如无法读取模板文件，则按本 skill 中的变量规则生成等价文件，并提示检查 `wf-init` skill 目录软链接。

## 模板资料定位

初始化时如需读取模板，使用当前 `wf-init` skill 目录下的 `templates/`：

- `templates/README.md`
- `templates/AGENT.md`
- `templates/CONTEXT.md`
- `templates/ISSUES.md`
- `templates/REVISIONS.md`
- `templates/JOURNAL.md`
- `templates/CHANGELOG.md`

如果 `templates/` 缺失，仍可按本 skill 中的文件清单、变量规则和 `wf/contracts/` 生成等价文件；但完成提示必须说明模板资料缺失，建议检查 `wf-init` skill 目录软链接。

## 执行流程

### 步骤 1：当前目录校验

`wf-init` 只初始化当前目录，不创建父目录或工作空间子目录。

执行任何写入前，必须检查当前目录是否为空：

- 当前目录为空 → 继续初始化。
- 当前目录不存在 → 报错并停止，提示用户先创建目录并进入该目录。
- 当前目录存在任何文件或目录（包括隐藏文件）→ 报错并停止，不得覆盖、删除、迁移或复用已有内容。

报错模板：

```text
❌ 当前目录不是空目录，不能执行 wf-init。

请新建一个空目录，进入该目录后重新执行 wf-init。
```

### 步骤 2：交互问答

项目名称默认使用当前目录名（`basename 当前目录`），不单独询问。按表格顺序，一问一答收集。每问一个，等待用户回答后再继续。**Q2（PRD 路径）回答后，先执行步骤 3 处理路径，再继续 Q3。**

| 序号 | 提示语 | 必填 | 校验 |
|------|--------|------|------|
| 1 | `开发平台默认是 HarmonyOS，是否确认？如不是，请说明实际平台。` | 是 | 不能为空；用户确认时记录为 `HarmonyOS` |
| 2 | `原始 PRD 文档路径是？` | 是 | 文件或目录必须存在 |
| 3 | `项目代码路径是？（没有的话填"无"）` | 否 | 如提供，目录必须存在。填"无"则跳过 |

**校验失败 → 修正后继续当前问，不跳过。**

### 步骤 3：PRD 路径处理

拿到 PRD 路径后，自动判断并记录完整文件列表，**暂不拷贝**：
- **是文件**：记录该文件绝对路径。
- **是目录**：扫描目录下所有文件（.md / .txt / .pdf），逐条记录绝对路径。
- 不向用户确认，直接进入下一问。

### 步骤 4：创建工作空间目录结构

在当前目录下创建以下子目录：

```
./
├── prd/        ← 原始 PRD 文件副本
└── output/     ← 各阶段产物
```

### 步骤 5：拷贝 PRD 文件

将步骤 3 中记录的全部 PRD 文件拷贝到 `prd/` 目录下，保持原文件名。拷贝后，后续所有生成文件中的 PRD 来源均指向 `prd/` 下的副本。

### 步骤 6：生成工作空间文件

优先从当前 skill 目录的 `templates/` 读取模板并生成以下文件：

- `README.md` ← `templates/README.md`
- `CONTEXT.md` ← `templates/CONTEXT.md`
- `ISSUES.md` ← `templates/ISSUES.md`
- `REVISIONS.md` ← `templates/REVISIONS.md`
- `JOURNAL.md` ← `templates/JOURNAL.md`
- `AGENT.md` ← `templates/AGENT.md`
- `CHANGELOG.md` ← `templates/CHANGELOG.md`

变量替换规则：

- `{项目名称}` → 当前目录名（`basename 当前目录`）
- `{平台}` → 步骤 2 确认或输入的开发平台，默认 `HarmonyOS`
- `{代码路径}` → 有代码路径则填绝对路径，填"无"则写 `无`
- `{代码路径信息}` → 有代码路径则 `仓库：{路径}`，填"无"则 `无代码仓库`
- `{PRD 份数}` → 步骤 3 记录的文件数量
- `YYYY-MM-DD`、`YYYY-MM-DD HH:MM`、`HH:MM` → 当前日期时间

`CONTEXT.md` 初始化状态必须符合 `wf/contracts/context.md`：

```markdown
- 阶段：initialized
- 下一步：analyze-requirements
```

如果无法读取 `templates/`，可以使用本 skill 的规则生成等价文件，但必须完全符合 `templates/` 和 `wf/contracts/` 的当前格式，并在完成提示中说明模板资料缺失。

### 步骤 7：完成提示

```
✅ 工作空间初始化完成

项目名称：{当前目录名}
目标平台：XXX
PRD 文档：X 份
项目代码：有/无
工作空间目录：{当前目录绝对路径}

📁 已在当前目录创建工作空间结构（含 prd/、output/）
📄 已生成 README.md（入口文件）
📄 已生成 CONTEXT.md
📄 已生成 ISSUES.md
📄 已生成 REVISIONS.md
📄 已生成 JOURNAL.md
📄 已生成 AGENT.md
📄 已初始化 CHANGELOG.md

下一步：执行 wf 继续工作流
```
