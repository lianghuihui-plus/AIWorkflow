# bug-new

收集 bug 信息，生成结构化 bug 文档到 `bugs/` 目录，作为 bug-fixer 的输入。

## 输入

- `workflow.yaml` 中 `project.code_path` 指向的代码仓库
- 用户描述（模式 A）或引用源中的 CL 条目（模式 B）

## 输出

- `output/bugs/BUG-XXX.md` — 结构化 bug 文档

## 使用方式

```
# 模式 A：交互式描述 bug
执行 bug-new → 描述问题 → 指定文件 → 生成文档

# 模式 B：从报告提取
执行 bug-new（附带 CL-002 引用）→ 自动提取 → 生成文档
```

## 注意

- 只生成文档，不修复代码
- 编号全局递增
- 修复由 bug-fixer 执行
