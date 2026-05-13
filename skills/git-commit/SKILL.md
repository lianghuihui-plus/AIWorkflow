---
name: git-commit
description: 扫描项目代码仓库的未提交变更，按规范生成 commit message 并提交。当用户完成代码或测试生成后要求提交时使用。
---

# Git 提交

扫描 `CODE_PATH` 下的未提交变更，按下方提交格式规范生成 commit message，经用户确认后提交。

> 本 skill 为工具型 skill，不参与管线流程。任意环节代码变更完成后均可手动触发。

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
2. 校验必填字段：
   - `project.code_path` — 如为空 → 终止并告知用户：**「workflow.yaml 中缺少 project.code_path，无法执行提交」**
3. 记 `CODE_PATH` = `project.code_path`

YAML 格式非法导致无法解析 → 终止并告知用户具体错误。

### 配置字段说明

| 配置路径 | 含义 | 必填 |
|---------|------|------|
| `project.code_path` | 项目代码路径 | 是 |

---

## 执行流程

### Step 1：扫描变更

在 `CODE_PATH` 下执行 `git status --porcelain`，列出所有未提交变更。

无变更 → 告知用户：**「当前无待提交变更」**，终止。

有变更 → 展示变更文件列表，继续。

### Step 2：询问 taskId

向用户询问本次提交的 taskId：

> 请提供本次提交的 taskId（如 T-001）：

用户提供后继续。

### Step 3：生成 commit message

**提交格式：**

```
<taskId>

[AI]
- Implemented: <描述，不超过 50 字>
- Affected modules: <模块名>
```

按格式生成 commit message：
- **Title**：用户提供的 taskId
- **Implemented**：分析变更文件，提炼变更摘要（不超过 50 字）
- **Affected modules**：涉及的模块名

生成后将完整 message 展示给用户确认：

```
T-001

[AI]
- Implemented: 新增登录接口及数据模型
- Affected modules: auth, login
```

### Step 4：执行提交

用户确认后在 `CODE_PATH` 下执行：

```
git add -A
git commit -m "<完整 message>"
```

提交完成后告知用户：
- commit hash
- 当前分支名

用户拒绝 → 终止，不提交。
