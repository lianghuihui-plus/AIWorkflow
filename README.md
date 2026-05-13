# AIWorkFlow

将「从 PRD 到代码」拆解为一组可审核、可追踪、可修订的 AI 辅助开发阶段。配套 Git 提交、Bug 管理工具。

## 架构全景

```
                          workflow-init → dev-profile
                               │
                               ▼
  PRD ──→ prd-analyzer ──→ task-decomposer ──→ tech-designer
            │                     │                   │
            ▼                     ▼                   ▼
     requirements.md          tasks.md          tech-design.md
                                                      │
                                                      ▼
                                            task-spec-generator
                                                      │
                                                      ▼
                                                 specs/*.md
                                                      │
                                                      ▼
                                               code-generator
                                                      │
                                              代码 + 报告
                                                      │
                                                      ▼
                                           unit-test-generator
                                                      │
                                              测试 + 测试报告
                                                      │
                                          ┌───────────┴───────────┐
                                          ▼                       ▼
                                     bug-new ──→ bug-fixer    git-commit
                                          │            │            │
                                     BUG-XXX.md   修复代码      提交代码
```

| 类型 | Skill | 说明 |
|------|-------|------|
| 管线 | workflow-init → dev-profile → prd-analyzer → task-decomposer → tech-designer → task-spec-generator → code-generator → unit-test-generator | 逐阶段收敛，每阶段需审核确认后才进入下一阶段 |
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
# 1. 执行 workflow-init，按提示填写项目信息
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
├── skills/                       # 12 个 Skill
│   ├── workflow-init/
│   ├── dev-profile/
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
    ├── bugs/              # Bug 文档
    │   └── BUG-XXX.md
    └── status.md          # 工作流概览
```

## 各阶段说明

| 阶段 | 输入 | 输出 | 核心职责 |
|------|------|------|----------|
| `workflow-init` | 用户交互 | `workflow.yaml` + `AGENT.md` | 收集项目信息，初始化工作流目录 |
| `dev-profile` | `AGENT.md` | 上下文注入 | 加载 Agent 角色和项目约束 |
| `prd-analyzer` | PRD 文档 | `requirements.md` | 提取结构化需求，发现待澄清项 |
| `task-decomposer` | 已确认的需求 | `tasks.md` | 拆解开发任务，建立依赖关系 |
| `tech-designer` | 任务 + 代码仓库 | `tech-design.md` | 基于真实代码设计数据结构与流程 |
| `task-spec-generator` | 技术方案 | `specs/*.md` | 收敛为逐文件逐修改点的可执行规格 |
| `code-generator` | 单个任务规格 | 代码 + 生成报告 | 按修改点生成/修改项目代码 |
| `unit-test-generator` | 代码报告 + 实际代码 | 测试代码 + 测试报告 | 为已确认的代码生成单元测试 |
| `git-commit` | 代码仓库变更 | git commit | 按规范生成 message 并提交 |
| `bug-new` | 用户描述或报告引用 | `BUG-XXX.md` | 生成结构化 bug 文档 |
| `bug-fixer` | `BUG-XXX.md` | 代码修复 + 文档回写 | 分析根因，修复代码并同步测试 |
| `workflow-status` | `output/` 目录 | `status.md` | 扫描所有报告状态，生成工作流概览 |

## 核心理念

- **逐阶段收敛**：每个阶段减少不确定性，不跨阶段跳步
- **人工审核门禁**：每阶段产物需确认后才进入下一阶段
- **来源可追溯**：需求 → 任务 → 方案 → 规格 → 代码，完整链路可追踪
- **修订可收敛**：每阶段支持人工审核后修订，待澄清项解决后自动收敛
- **一次只做一个**：code-generator、unit-test-generator、bug-fixer 每次处理一个单元
