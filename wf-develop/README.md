# AIWorkFlow

AIWorkFlow 是面向 Agent 的工作空间式研发流程。它保留需求分析、技术设计、规格生成、代码实现和测试生成五个阶段，把状态、版本、审核、依赖、记忆和静态看板交给确定性 Python 内核管理，让 Agent 专注语义工作。

## 入口

| Skill | 职责 |
|---|---|
| `wf-init` | 在空目录创建工作空间并复制 PRD。 |
| `wf` | 推进阶段、处理审核与修订、记录决策、恢复事务和迁移旧工作空间。 |
| `wf-status` | 只读查看状态、待审核项、阻塞问题和健康检查。 |

三个 Skill 作为同一发行单元使用，共享 `wf/tools/aiwf.py` 和 `wf/tools/aiwf_core/`。

## 工作方式

```text
wf-init
  -> 需求分析 -> 人工审核
  -> 技术设计 -> 人工审核
  -> 任务规格 -> 人工审核
  -> 代码实现 -> 人工审核
  -> 测试生成 -> 人工审核
  -> 完成
```

Agent 每次通过 `prepare` 获得自描述任务包，只读取任务相关输入并写入工作区草稿和结果模板。`submit` 在事务中提升正式产物，用户通过 `review` 决定批准或要求修改。已批准产物通过 `revise` 创建新 revision，实际变化会使相关下游产物失效。

阻塞语义工作的问题通过 `question` 一次性提交，用户回答由 `decide` 原样保存。工作空间发生中断时，`recover` 根据事务日志恢复。旧工作空间迁移默认只预览，必须明确使用 `migrate --apply` 才会写入。

## 工作空间

```text
workspace/
├── .aiwf/
│   ├── project.json
│   ├── state.json
│   ├── requirements.json
│   ├── tasks.json
│   ├── artifacts.json
│   ├── decisions.json
│   ├── questions.json
│   ├── memory.json
│   ├── memory.md
│   ├── events.jsonl
│   ├── results/
│   ├── history/
│   ├── work/
│   └── transactions/
├── prd/
├── artifacts/
│   ├── analysis.md
│   ├── design.md
│   ├── specs/
│   ├── reports/
│   └── tests/
└── dashboard.html
```

结构化 JSON 是流程事实源，Markdown 保存用户可读语义，`memory.md` 和 `dashboard.html` 是可重新生成的只读投影。状态命令不会修复或渲染文件；写命令会先恢复事务并同步生成视图。

## 代码结构

```text
wf-develop/
├── wf/SKILL.md
├── wf/references/stages/
├── wf/tools/aiwf.py
├── wf/tools/aiwf_core/
├── wf-init/SKILL.md
├── wf-status/SKILL.md
├── tests/
└── REFACTOR_TECHNICAL_PLAN.md
```

阶段参考只包含语义目标、建议关注点、最低交付内容和必须停止的情况。JSON Schema、ID、状态迁移、revision 和依赖规则全部由内核生成或校验，不复制到 Skill 指令。

## 验证

```bash
cd /Users/cm/GitProj/AIWorkflow/wf-develop
python3 -m unittest discover -s tests -p 'test_*.py'
python3 wf/tools/aiwf.py --version
python3 /Users/cm/.codex/skills/.system/skill-creator/scripts/quick_validate.py wf
python3 /Users/cm/.codex/skills/.system/skill-creator/scripts/quick_validate.py wf-init
python3 /Users/cm/.codex/skills/.system/skill-creator/scripts/quick_validate.py wf-status
```

当前目录是开发版本。线上目录 `wf-release` 必须保持不变，只有完成统一效果验收并得到明确发布授权后才能同步。
