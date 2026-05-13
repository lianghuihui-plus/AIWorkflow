# unit-test-generator

基于代码生成报告逐修改点生成单元测试用例，直接写入项目代码仓库。每次处理一个 spec 文件，输出测试生成报告至 `tests/` 目录。

## 输入

- `output/specs/T-XXX-spec.md`（任务规格文件）
- `output/generated/T-XXX-report.md`（已审核的代码生成报告）
- `workflow.yaml` 中 `project.code_path` 指向的代码仓库
- `AGENT.md` 中「单元测试」段落（可选，未填写则自动检测）

## 输出

- 测试文件写入 `project.code_path` 下的对应测试目录
- `output/tests/T-XXX-test-report.md` — 测试生成报告

## 使用方式

```
# 用户指定任务
执行 test-generator T-003 → 生成测试 + 报告

# 用户未指定任务
执行 test-generator → 自动定位首个代码已审核且测试未完成的任务 → 确认后生成

# 修订
在报告的待澄清项中填写人工决策 → 执行 test-generator → 修改测试文件 → 人工确认审核通过 → 收敛为「已审核」
```

## 注意

- 必须代码报告状态为「已审核」后才能触发
- 每次只处理一个任务，不批量生成
- 纯删除类修改点不生成测试
- 测试框架和目录优先读取 AGENT.md，未填写则按平台自动检测
