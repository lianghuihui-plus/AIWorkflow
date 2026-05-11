# tech-designer

对已分解的任务进行技术方案设计。探索真实代码库，产出数据结构、核心流程、影响范围等技术方案。

## 输入

- `output/tasks.md`（状态必须为「已确认」）
- `output/requirements.md`（用于扫描全局约束）
- `workflow.yaml` 中 `project.code_path` 指向的真实代码库

## 输出

- `output/tech-design.md` — 包含任务总览、每个任务的数据结构变更、核心逻辑流程、入口与出口、影响范围、边界场景

## 使用方式

```
# 初版生成
执行 tech-designer → 基于真实代码探索生成 tech-design.md（状态：待审核）

# 人工审核后修订
在 tech-design.md 的待澄清项中填写人工决策 → 执行 tech-designer → 自动收敛
```

## 注意

- 仅在上一个阶段产物状态为「已确认」时才能执行
- 必须配置 `project.code_path` 指向真实代码库，否则无法探索代码
- 不凭空编造文件路径或类名，不确定时记录为「待澄清」
- 所有待澄清项解决 → 自动收敛为「已确认」
