# AIWorkFlow

基于工作空间的 AI 辅助开发流程。将"需求到代码"拆解为可追踪的阶段，Agent 在共享上下文中推进，支持跨会话恢复和人工决策收敛。

## 核心理念

- **共享上下文**：Agent 启动时一次性加载 README + CONTEXT + ISSUES + JOURNAL，不重复读取
- **松散耦合**：各阶段按推荐顺序推进但可跳过、回退、交叉，Agent 自主判断
- **问题收敛**：任何阶段发现问题写入 ISSUES，人工决策后自动执行并归档
- **跨会话恢复**：JOURNAL 持续记录进度，下次启动无缝接续

## 技能

| # | 阶段 | Skill | 产出 |
|---|------|-------|------|
| 1 | 需求分析 | `wf-prd-analyzer` | `output/analysis.md` |
| 2 | 技术方案 | `wf-tech-designer` | `output/design.md` |
| 3 | 开发规格 | `wf-spec-generator` | `output/specs/T-XXX.md` |
| 4 | 代码生成 | `wf-code-generator` | `output/report-T-XXX.md` + 写入代码仓库 |
| 5 | 测试 | `wf-test-generator` | `output/test-report-T-XXX.md` + 写入测试代码 |

辅助：`wf-git-commit`（提交）· `wf-status`（状态与健康检查）

## 安装

```bash
./install.sh           # 所有平台
./install.sh cursor    # 只装 Cursor
./install.sh hermes    # 只装 Hermes
```

## 工作空间

### 目录结构

```
workspace-{项目}/
├── README.md           ← 入口：工作流 + 规范
├── CONTEXT.md          ← 需求概要、当前阶段、代码产出、测试记录
├── ISSUES.md           ← 待澄清问题，按阶段分组
├── JOURNAL.md          ← 工作日志，每操作一记
├── CHANGELOG.md        ← 已解决决策的时间线归档
├── AGENT.md            ← 编码约束
├── prd/                ← 原始 PRD 文件副本
└── output/
    ├── analysis.md     ← 结构化需求分析
    ├── design.md       ← 任务拆解 + 技术方案
    └── specs/          ← 逐文件编码指令
```

### 文件职责

| 文件 | 职责 | 写入时机 |
|------|------|---------|
| `CONTEXT.md` | 需求概要、当前阶段、下一步、代码产出、测试记录 | 阶段推进时更新 |
| `ISSUES.md` | 待人工决策的问题，按阶段分组 | 发现问题时写入 |
| `JOURNAL.md` | 工作进度日志 | 每完成一个操作追加 |
| `CHANGELOG.md` | 已解决决策归档 | 问题解决时追加 |

### 工作规范

**写操作规则：**

| 场景 | 文件 | 位置 | 格式 |
|------|------|------|------|
| 发现问题 | `ISSUES.md` | 对应阶段下追加 Q-xxx | 问题/AI建议/影响/状态 |
| 问题解决 | `CHANGELOG.md` | 文件末尾按日期追加 | 时间线格式 |
| 阶段推进 | `CONTEXT.md` | `## 当前状态` 更新 | 阶段/下一步 |
| 操作完成 | `JOURNAL.md` | 文件末尾按日期追加 | HH:MM 时间戳 + 内容 |

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
     ```

   - 从 `ISSUES.md` 删除该 Q-xxx 条目
   - 在 `JOURNAL.md` 追加操作日志

**阶段推进：**

| Skill | 完成后 CONTEXT 更新 |
|-------|-------------------|
| `wf-prd-analyzer` | 需求分析完成 → 下一步：wf-tech-designer |
| `wf-tech-designer` | 技术方案完成 → 下一步：wf-spec-generator |
| `wf-spec-generator` | 规格生成完成 → 下一步：wf-code-generator |
| `wf-code-generator` | 标注任务 ✅ · 全部完成则代码生成完成 |
| `wf-test-generator` | 标注任务 ✅ · 全部完成则测试完成 |

**跨会话恢复：**

读 `JOURNAL.md` 最后一条 → 了解上次进度，继续工作。

## 快速开始

```
# 1. 创建工作空间
执行 wf-init

# 2. 按阶段推进
wf-prd-analyzer → wf-tech-designer → wf-spec-generator → wf-code-generator → wf-test-generator

# 3. 随时查看
wf-status
```
