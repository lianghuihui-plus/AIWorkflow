# workflow-init

初始化 AI 辅助开发工作流。通过一轮交互问答收集项目信息，创建 `workflow-xxx` 目录，生成 `workflow.yaml` 和 `AGENT.md`。

## 输入

- 用户在对话中执行 `workflow-init`
- 按提示回答 5 个问题（项目名称、平台、PRD 路径、代码路径、工作流目录位置）

## 输出

```
workflow-{项目名称}/
├── workflow.yaml      # 配置文件，后续阶段的唯一入口
├── AGENT.md           # Agent 角色与项目约束（默认模板，按需修改）
└── output/            # 各阶段输出目录
```

## 使用方式

```
执行 workflow-init → 按提示逐项回答 → 初始化完成 → 进入生成的目录继续
```

## 注意

- 初始化后进入 `workflow-xxx` 目录再执行后续阶段
- 建议先执行 `dev-profile` 加载 Agent 角色，再开始需求分析
- `workflow.yaml` 可手动修改，后续阶段自动读取
- 目录下已存在同名 workflow 目录时会提示确认是否覆盖
