---
name: wf-test-generator
description: 测试生成。读取 spec 规格文件和实际代码，对照关键行为生成单元测试。产出 output/test-report-T-XXX.md 记录测试覆盖。过程记录写入 CONTEXT/ISSUES/JOURNAL。
---

# 测试生成

对照 spec 中的关键行为，为已生成的代码编写单元测试，产出 `output/test-report-T-XXX.md`。

> 在 workspace 目录下执行。

## 前置检查

当前目录存在 `CONTEXT.md`。不存在 → 报错终止。

## 执行流程

### Step 1：确认目标

确定要测试的任务：

- 用户指定 T-XXX → 直接使用
- 未指定 → 读 CONTEXT.md 规格索引，优先选已 ✅ 但未标记测试完成的任务
- 无可用任务 → 告知用户：**「没有待测试的任务」**

`output/specs/T-XXX.md` 存在。不存在 → 报错终止。

### Step 2：读取输入

读 `output/specs/T-XXX.md`，提取：关键行为、修改点清单。
读 `CONTEXT.md`，提取代码路径。代码路径为空 → 报错终止。
根据修改点清单读取对应源码文件。

### Step 3：生成测试

对照 spec 中的「关键行为」逐条编写测试用例：

- **正常路径** — 覆盖关键行为中的正常交互流程
- **边界/异常** — 覆盖关键行为中的异常处理和边界条件
- **状态变化** — 覆盖关键行为中的状态转换

确认测试框架和目录结构，遵循已有代码的测试风格。

### Step 4：生成报告

`output/` 目录不存在则先创建。生成 `output/test-report-T-XXX.md`：

```markdown
# 测试报告 — T-XXX [任务标题]

> 生成日期：YYYY-MM-DD · 来源：specs/T-XXX.md

## 测试清单

| # | 测试用例 | 覆盖行为 | 文件 | 状态 |
|---|---------|---------|------|------|
| 1 | [用例描述] | 关键行为 1：正常路径 | `tests/Xxx.test.ets` | ✅ |
| 2 | [用例描述] | 关键行为 2：边界条件 | `tests/Xxx.test.ets` | ✅ |
| 3 | [用例描述] | 异常处理 | `tests/Xxx.test.ets` | ✅ |

## 未覆盖行为

> 全部覆盖则写「无」。

- [行为描述] — [未覆盖原因]
```

### Step 5：更新工作空间文件

**更新 CONTEXT.md：**

- 在 `规格` 索引中标注测试完成（`T-001 — ✅ 已测试 [report](output/test-report-T-001.md)`）
- 在 `## 测试记录` 表格中追加（`T-001 | tests/Xxx.test.ets | ✅ 已完成`）
- 如全部任务测试完成 → `阶段` 改为 `测试完成`

**写入 ISSUES.md（测试中发现的问题）：**

在 `## 测试阶段` 下按以下格式追加：

```
### Q-001 — [问题简述]

- **问题：** [具体描述]
- **AI 建议：** [建议方案]
- **影响：** [影响的文件或任务]
- **提出：** YYYY-MM-DD wf-test-generator

---

**人工决策：**
**状态：** 待决策
```

**写入 JOURNAL.md：**

```
### HH:MM — wf-test-generator 完成 T-XXX

- 任务：[标题]
- 编写 X 个测试用例，覆盖 X 个关键行为
- 生成 output/test-report-T-XXX.md
- 发现问题 X 项，写入 ISSUES.md
```

---

## 输出前自检

- [ ] 每个关键行为都有对应的测试用例
- [ ] 覆盖了正常路径、边界条件和异常处理
- [ ] 测试风格与已有测试一致
- [ ] `output/test-report-T-XXX.md` 已生成，未覆盖行为有说明
- [ ] 发现问题已写入 ISSUES.md
