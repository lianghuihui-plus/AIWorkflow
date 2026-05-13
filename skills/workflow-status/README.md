# workflow-status

扫描工作流目录下所有报告的状态，生成工作流概览文档。

## 输入

- `workflow.yaml` 中的 `output.base_dir` 和 `project.name`

## 输出

- `output/status.md` — 工作流概览文档

## 使用方式

```
执行 workflow-status → 扫描输出目录 → 生成 status.md
```

## 注意

- 工具型 skill，不参与管线流程
- 每次执行覆盖更新 status.md
