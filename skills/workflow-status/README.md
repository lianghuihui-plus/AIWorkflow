# workflow-status

实时扫描工作流目录下所有报告的状态，直接在对话中输出进度概览，不落盘。

## 输入

- `workflow.yaml` 中的 `output.base_dir` 和 `project.name`

## 输出

- 对话输出：管线进度、任务详情、Bug 列表、下一步建议（不生成文件）

## 使用方式

```
执行 workflow-status → 实时扫描输出目录 → 对话中展示概览
```

## 注意

- 工具型 skill，不参与管线流程
- 每次执行都是最新快照，不会有过期数据
