---
name: wf-git-commit
description: Git 提交。扫描代码仓库未提交变更，按规范生成 commit message 并提交。
---

# Git 提交

扫描代码仓库未提交变更，按规范生成 commit message，经用户确认后提交。

> 在 workspace 目录下执行。

## 定位代码仓库

读 `CONTEXT.md`（「项目约束」→ `代码仓库`），提取代码路径。

按以下优先级确定 `REPO_PATH`：

1. 代码路径有值且非"无" → 使用该路径
2. 当前工作目录是 git 仓库 → 使用当前目录
3. 询问用户

验证该目录是 git 仓库（`git rev-parse --git-dir` 成功）。不是则终止。

---

## 执行流程

### Step 1：扫描变更

在 `REPO_PATH` 下执行 `git status --porcelain`。

无变更 → 告知用户并终止。有变更 → 展示变更文件列表，继续。

### Step 2：询问 taskId

> 请提供本次提交的 taskId（如 \<taskId\>）：

### Step 3：生成 commit message

```
<taskId>

[AI]
- Implemented: <描述，不超过 50 字>
- Affected modules: <模块名>
```

展示给用户确认。确认 → 继续；拒绝 → 终止。

### Step 4：执行提交

1. 将确认后的 message 写入临时文件（如 `/tmp/hermes_commit_msg`）
2. **只 stage 本次相关文件**（`git add <file1> <file2> …`），**禁止 `git add -A` 或 `git add .`**
3. `git commit -F <临时文件路径>`
4. 删除临时文件
5. **验证**：`git log -1 --name-only`，核对与 `git add` 一致

提交完成后告知用户 commit hash 和当前分支名。

### Step 5：写入 JOURNAL.md

```
### HH:MM — wf-git-commit

- 提交 X 个文件
- commit: <hash>
```
