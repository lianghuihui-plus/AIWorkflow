# task-decomposer

将已确认的结构化需求拆解为开发任务块，建立依赖关系并排序。

## 输入

- `output/requirements.md`（状态必须为「已确认」）

## 输出

- `output/tasks.md` — 包含任务总览、任务详情、待澄清项

## 使用方式

```
# 初版生成
执行 task-decomposer → 生成 tasks.md（状态：待审核）

# 人工审核后修订
在 tasks.md 的待澄清项中填写人工决策 → 执行 task-decomposer → 自动收敛
```

## 注意

- 仅在 requirements.md 状态为「已确认」时才能执行
- 只做任务拆分和依赖排序，不涉及技术方案和实现细节
- 硬依赖才设为依赖，软依赖不设依赖
- 全局约束影响的任务会标记 `[G]`
- 所有待澄清项解决 → 自动收敛为「已确认」
