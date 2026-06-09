# {项目名称}

> {平台} · {代码路径信息} · PRD：{PRD 份数} 份 · 最后更新：YYYY-MM-DD

## 工作方式

这是 AIWorkFlow 工作空间。推荐使用 `wf` 作为主入口继续推进：

```text
wf
继续
下一步
处理 Q-001
生成下一个任务
看当前状态
```

Agent 会读取 `AGENT.md`、`CONTEXT.md`、`ISSUES.md`、`REVISIONS.md` 和 `JOURNAL.md`，根据工作流运行时自动判断下一步。

编码规范见 `AGENT.md`。需要人工决策的问题见 `ISSUES.md`。

## 文件索引

| 文件 | 内容 |
|---|---|
| `AGENT.md` | 工作空间内 Agent 必须遵守的运行规则 |
| `CONTEXT.md` | 当前阶段、下一步、任务索引、代码产出、测试记录 |
| `ISSUES.md` | 待人工决策问题 |
| `REVISIONS.md` | 用户主动提出的产物修订意见 |
| `JOURNAL.md` | 工作日志和跨会话恢复线索 |
| `CHANGELOG.md` | 已解决人工决策归档 |

## 目录

| 目录 | 说明 |
|---|---|
| `prd/` | 原始 PRD 文件副本 |
| `output/` | 工作流阶段产物 |

## 核心产物

| 文件 | 说明 |
|---|---|
| `output/analysis.md` | 需求分析 |
| `output/design.md` | 技术方案 |
| `output/specs/T-XXX.md` | 开发规格 |
| `output/report-T-XXX.md` | 代码生成报告 |
| `output/test-report-T-XXX.md` | 测试报告 |

## 工作规范

### 人工审核

每个阶段产物生成或修订后都会进入 `待审核` 状态，`CONTEXT.md` 的下一步会变为 `review-artifact`。用户确认通过后才能进入下一步；需要修改时，可以直接对话提出意见，Agent 会写入 `REVISIONS.md` 并收敛产物。

### 写操作

| 场景 | 文件 | 写入位置 | 格式 |
|---|---|---|---|
| 发现问题需人工决策 | `ISSUES.md` | 对应阶段下追加 Q-XXX | 问题/AI建议/影响/提出/人工决策/状态 |
| 用户提出产物修订 | `REVISIONS.md` | `## 待处理` 下追加 R-XXX | 目标产物/修订类型/用户意见/影响范围/状态 |
| 问题已解决 | `CHANGELOG.md` | 文件末尾按日期追加 | 决策归档格式 |
| 阶段推进 | `CONTEXT.md` | `## 当前状态` 更新 | 阶段/下一步 |
| 每完成一个操作 | `JOURNAL.md` | 文件末尾按日期追加 | HH:MM 时间戳 + 内容 |

### 阶段推进

阶段推进由 `wf` 根据运行时状态机统一处理。阶段能力不再作为独立 skill 暴露，而是由 `wf` 按需加载。

