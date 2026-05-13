---
name: dev-profile
description: 读取 AGENT.md，将 Agent 角色和项目约束注入当前会话上下文。当用户要加载角色/预设规约/加载 AGENT 时使用。
---

# Agent 角色加载

读取 `AGENT.md` 文件，将其内容注入当前会话上下文。后续阶段自动遵循其中定义的约束。

## 配置读取

### 定位工作流目录

按以下优先级定位 `workflow.yaml` 所在的工作流根目录：

1. **检查当前目录** — 当前工作目录中存在 `workflow.yaml` → 从该目录读取配置
2. **检查会话上下文** — 如本会话中已运行过 `workflow-init` 或其他阶段 skill，且已知工作流目录路径 → 使用该路径
3. **询问用户** — 以上均未找到时，向用户询问：
   > 我需要知道当前工作流目录路径，请提供 workflow-xxx 目录的路径。

验证定位到的目录中存在 `workflow.yaml`；不存在则提示用户先执行 `workflow-init` 初始化。

定位到 `workflow.yaml` 后，立即解析并执行：

**除工作流目录定位外，本阶段所有输入从 `workflow.yaml` 读取，不交互询问。**

### 读取并校验

1. 解析 `workflow.yaml`，校验 YAML 格式
2. 提取 `agent.profile`（默认 `AGENT.md`），记为 `PROFILE`

YAML 格式非法导致无法解析 → 终止并告知用户具体错误。

### 配置字段说明

| 配置路径 | 含义 | 必填 |
|---------|------|------|
| `agent.profile` | Agent 角色配置文件路径 | 是（默认 `AGENT.md`） |

---

## 执行

1. 读取 `{workflow根目录}/{PROFILE}`
2. 不存在 → 告知用户：`未找到 {PROFILE}，请先执行 workflow-init`
3. 存在 → 读取全文，注入上下文，回复用户：`已加载 {PROFILE}。`
