# git-commit

扫描项目代码仓库的未提交变更，按内置提交格式生成 commit message 并提交。

## 输入

- `workflow.yaml` 中 `project.code_path` 指向的代码仓库
- 用户提供的 taskId

## 输出

- 在 `project.code_path` 下执行 `git commit`

## 使用方式

```
# 任意环节代码变更完成后
执行 git-commit → 扫描变更 → 提供 taskId → 确认 message → 提交
```

## 注意

- 工具型 skill，不参与管线流程
- taskId 由用户提供，不自动推断
- 无变更时直接终止
