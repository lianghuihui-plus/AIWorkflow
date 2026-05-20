# AIWorkFlow

将「从 PRD 到代码」拆解为一组可审核、可追踪、可修订的 AI 辅助开发阶段。支持需求变更后的增量更新传播。配套 Git 提交、Bug 管理工具。

## 架构全景

```
                      workflow-session
                            │
                            ▼
  PRD ──→ prd-analyzer ──→ task-decomposer ──→ tech-designer
            │  ↑                 │  ↑                │  ↑
            ▼  │                 ▼  │                ▼  │
     requirements.md          tasks.md          tech-design.md
        需求变更                    │                   │
            │                      ▼                   ▼
            │            task-spec-generator    ← 上游变更后
            │                 │  ↑              逐阶段触发更新
            │                 ▼  │
            │            specs/*.md
            │                 │  ↑
            │                 ▼  │
            │           code-generator
            │                 │
            │          代码 + 报告
            │                 │
            │                 ▼
            │       unit-test-generator
            │                 │
            │          测试 + 测试报告
            │                 │
            │      ┌──────────┴───────────┐
            │      ▼                      ▼
            │  bug-new ──→ bug-fixer   git-commit
            │      │           │           │
            └──────┴───────────┴───────────┘
              BUG-XXX.md   修复代码     提交代码
```

| 类型 | Skill | 说明 |
|------|-------|------|
| 管线 | workflow-session → prd-analyzer → task-decomposer → tech-designer → task-spec-generator → code-generator → unit-test-generator | 逐阶段收敛，每阶段支持三种模式：初版 / 修订 / 更新 |
| 工具 | git-commit | 扫描变更、按规范提交 |
| 工具 | bug-new → bug-fixer | 生成结构化 bug 文档 → 分析根因并修复 |
| 工具 | workflow-status | 扫描输出目录，生成工作流概览 |

## 快速开始

```bash
# 安装到指定平台
./install.sh cursor    # Cursor
./install.sh hermes    # Hermes Agent
./install.sh           # 所有平台

# 在 AI 对话中使用
# 1. 执行 workflow-session，选择"新建"或"继续"
# 2. 进入生成的 workflow-xxx 目录，按顺序执行各阶段
```

## 目录结构

```
AIWorkFlow/
├── install.sh                    # 统一安装入口
├── platforms/                    # 各平台安装脚本
│   ├── cursor/install/
│   ├── hermes/install/
│   └── openclaw/install/
├── skills/                       # 11 个 Skill
│   ├── workflow-session/
│   ├── prd-analyzer/
│   ├── task-decomposer/
│   ├── tech-designer/
│   ├── task-spec-generator/
│   ├── code-generator/
│   ├── unit-test-generator/
│   ├── git-commit/
│   ├── bug-new/
│   ├── bug-fixer/
│   └── workflow-status/
└── README.md
```

安装后在项目目录生成的工作流目录结构：

```
workflow-{项目名称}/
├── workflow.yaml          # 配置文件（各阶段的唯一配置入口）
├── AGENT.md               # Agent 角色与项目约束
└── output/
    ├── requirements.md    # 需求分析
    ├── tasks.md           # 任务分解
    ├── tech-design.md     # 技术方案
    ├── specs/             # 开发规格
    │   ├── README.md
    │   └── T-XXX-spec.md
    ├── generated/         # 代码生成报告
    │   └── T-XXX-report.md
    ├── tests/             # 测试生成报告
    │   └── T-XXX-test-report.md
    └── bugs/              # Bug 文档
        └── BUG-XXX.md
```

## 各阶段说明

| 阶段 | 输入 | 输出 | 模式 |
|------|------|------|------|
| `workflow-session` | 用户交互或已有目录 | `workflow.yaml` + `AGENT.md` 加载 | — |
| `prd-analyzer` | PRD 文档 | `requirements.md` | 初版 / 修订 |
| `task-decomposer` | 已审核的需求 | `tasks.md` | 初版 / 修订 / 更新（上游变更后增量更新） |
| `tech-designer` | 任务 + 代码仓库 | `tech-design.md` | 初版 / 修订 / 更新 |
| `task-spec-generator` | 技术方案 | `specs/*.md` | 初版 / 修订 / 更新 |
| `code-generator` | 单个任务规格 | 代码 + 报告 | 初版 / 修订 / 更新 |
| `unit-test-generator` | 代码报告 + 实际代码 | 测试代码 + 测试报告 | 生成 / 修订 |
| `git-commit` | 代码仓库变更 | git commit | — |
| `bug-new` | 用户描述或报告引用 | `BUG-XXX.md` | — |
| `bug-fixer` | `BUG-XXX.md` | 代码修复 + 文档回写 | — |
| `workflow-status` | `output/` 目录 | 对话输出（不落盘） | — |

## 需求变更传播

```
prd-analyzer                  下游各阶段（逐阶段触发）

改文档状态「待审核」           task-decomposer
对话描述变更 → 修订模式处理     → 更新模式：读 requirements.md → 对比 tasks.md → 增量更新
                               tech-designer
                               → 更新模式：读 tasks.md → 对比 tech-design.md → 增量更新
                               task-spec-generator
                               → 更新模式：读 tech-design.md → 对比 specs/ → 增量更新
                               code-generator
                               → 更新模式：读 spec → 对比 report → 增量更新代码
```

## 核心理念

- **逐阶段收敛**：每个阶段减少不确定性，不跨阶段跳步
- **人工审核门禁**：每阶段产物需确认后才进入下一阶段
- **来源可追溯**：需求 → 任务 → 方案 → 规格 → 代码，完整链路可追踪
- **修订可收敛**：每阶段支持人工审核后修订，待澄清项解决后自动收敛
- **增量更新**：需求变更后逐阶段传播，每阶段用自己的规则增量更新产物，无需重跑全管线
- **一次只做一个**：code-generator、unit-test-generator、bug-fixer 每次处理一个单元
