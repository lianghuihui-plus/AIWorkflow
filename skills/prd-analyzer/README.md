# prd-analyzer

分析 PRD 文档，提取结构化需求。支持多份 PRD、平台过滤、模糊点与冲突检测。

## 输入

- `workflow.yaml` 中配置的 PRD 文件（`prd.sources`）
- `workflow.yaml` 中的目标平台（`project.platform`）

## 输出

- `output/requirements.md` — 功能需求、暂不纳入、需澄清（REQ 内）、待澄清（跨 REQ/全局）、原文引用附录

## 使用方式

```
# 初版生成
执行 prd-analyzer → 生成 requirements.md（状态：待审核）

# 人工审核后修订
填写纳入列（Y/N）和人工回应/决策 → 执行 prd-analyzer → 自动收敛

# 需求变更
改文档状态为「待审核」，对话描述变更内容 → 修订模式自动处理
```

## 注意

- 执行前确保 PRD 文件路径正确且文件存在
- 纳入列留空，由人工填写 Y 或 N
- 「需澄清」和「待澄清」是两个不同的表，不要混淆
- 修订时已解决的条目不会被删除，保留作为记录
- 所有待澄清项解决 + 纳入列全 Y → 收敛为「已审核」
