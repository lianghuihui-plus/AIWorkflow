# bug-fixer

读取结构化 bug 文档，分析根因并修复代码，同步更新测试文件和关联报告。

## 输入

- `output/bugs/BUG-XXX.md`（待修复的 bug 文档）
- `workflow.yaml` 中 `project.code_path` 指向的代码仓库

## 输出

- 代码文件修复（写入 `project.code_path`）
- 测试文件同步更新
- bug 文档「Bug 修复」段填写 + 状态改为「已修复」
- 关联测试报告 CL 状态更新（如有）

## 使用方式

```
# 用户指定 bug
执行 bug-fixer BUG-003 → 修复该 bug

# 自动定位
执行 bug-fixer → 自动定位首个待修复 bug → 确认后修复
```

## 注意

- 每次只处理一个 bug
- 状态为「已修复」的 bug 不再处理
- 如需重新修复，手动将状态改回「待修复」
