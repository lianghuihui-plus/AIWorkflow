# dev-profile

读取 `AGENT.md`，将 Agent 角色和项目约束注入当前会话上下文。后续阶段自动遵循其中定义的编码规范、架构约定等约束。

## 输入

- 工作流目录下的 `AGENT.md`（由 `workflow-init` 生成默认版本）

## 输出

- 将 `AGENT.md` 内容注入当前会话上下文，后续所有阶段自动遵循

## 使用方式

```
# 1. 首次使用：修改 workflow-init 生成的 AGENT.md，按项目实际情况填写
# 2. 执行 dev-profile 加载
执行 dev-profile → 已加载 AGENT.md。
```

## 注意

- 必须在 workflow 目录下执行，或已通过其他 skill 定位到 workflow 目录
- `AGENT.md` 不存在时会提示先执行 `workflow-init`
- 修改 `AGENT.md` 后需重新执行 `dev-profile` 才能生效
- 此 skill 不自动执行，由用户手动触发
