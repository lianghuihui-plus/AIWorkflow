#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

write_base_workspace() {
  local ws="$1"
  mkdir -p "$ws/prd" "$ws/output/specs" "$ws/output/reports" "$ws/output/test-reports"
  printf '需求\n' > "$ws/prd/req.md"
  cat > "$ws/AGENT.md" <<'EOF'
# Agent
EOF
  cat > "$ws/ISSUES.md" <<'EOF'
# 待澄清

## 分析阶段

暂无

## 设计阶段

暂无

## 实现阶段

暂无

## 测试阶段

暂无
EOF
  cat > "$ws/REVISIONS.md" <<'EOF'
# 用户修订

## 待处理

暂无

## 已处理

暂无
EOF
  cat > "$ws/JOURNAL.md" <<'EOF'
# 工作日志
EOF
  cat > "$ws/CHANGELOG.md" <<'EOF'
# 决策归档
EOF
  cat > "$ws/CONTEXT.md" <<'EOF'
# 工作空间上下文 — Demo

> 最后更新：2026-06-10 10:00

## 需求概要

Demo

## 当前状态

- 阶段：initialized
- 待决策：0 项（详见 ISSUES.md）
- 下一步：analyze-requirements
- 待处理产物：
  - 暂无
- 规格：
  - 暂无

## 项目约束

- 平台：HarmonyOS
- 代码仓库：无

## 代码产出

| 任务 | 状态 |
|---|---|
| — | — |

## 测试记录

| 任务 | 测试文件 | 状态 |
|---|---|---|
| — | — | — |
EOF
}

write_review_status() {
  local file="$1"
  local status="$2"
  mkdir -p "$(dirname "$file")"
  cat > "$file" <<EOF
# $(basename "$file")

## 审核状态

- 状态：$status
- 审核人：
- 审核时间：
- 修订来源：

## 内容

demo
EOF
}

assert_json_status() {
  local json="$1"
  local expected="$2"
  python3 - "$json" "$expected" <<'PY'
import json
import sys
payload = json.loads(sys.argv[1])
expected = sys.argv[2]
actual = payload.get("status")
if actual != expected:
    raise SystemExit(f"expected status {expected}, got {actual}: {payload}")
PY
}

assert_contains_issue_type() {
  local json="$1"
  local expected="$2"
  python3 - "$json" "$expected" <<'PY'
import json
import sys
payload = json.loads(sys.argv[1])
expected = sys.argv[2]
types = [issue.get("type") for issue in payload.get("issues", [])]
if expected not in types:
    raise SystemExit(f"expected issue type {expected}, got {types}")
PY
}

assert_file_review_status() {
  local file="$1"
  local expected="$2"
  grep -q -- "- 状态：$expected" "$file" || fail "expected $file review status $expected"
}

write_valid_test_report() {
  local file="$1"
  local status="$2"
  mkdir -p "$(dirname "$file")"
  cat > "$file" <<EOF
# 单元测试报告 — T-001 示例任务

## 审核状态

- 状态：$status
- 审核人：User
- 审核时间：2026-06-10 10:00
- 修订来源：

## 任务范围

demo

## 已生成单元测试

| # | 行为 | 测试点 | 测试文件 | 状态 | 说明 |
|---|---|---|---|---|---|
| 1 | normal | branch | \`tests/Demo.test.ts\` | 已生成 | demo |

## 未生成单元测试

| # | 行为 | 测试点 | 测试文件 | 状态 | 说明 |
|---|---|---|---|---|---|
| — | 无 | — | — | — | 全部目标行为已生成单元测试 |

## 辅助验证记录

| # | 验证项 | 命令/方式 | 结果 | 说明 |
|---|---|---|---|---|
| — | 未执行 | — | 未执行 | 缺少可用测试执行脚本 |

## 结论

已生成单测
EOF
}

test_validator_detects_pending_artifact_mismatch() {
  local ws="$TMP_DIR/pending-mismatch"
  write_base_workspace "$ws"
  write_review_status "$ws/output/analysis.md" "待审核"

  local out
  out="$(python3 "$ROOT_DIR/tools/validator_source/validate.py" "$ws" --json || true)"
  assert_json_status "$out" "fail"
  assert_contains_issue_type "$out" "pending_artifacts_mismatch"
}

test_validator_action_guard_blocks_unconfirmed_analysis() {
  local ws="$TMP_DIR/action-guard"
  write_base_workspace "$ws"
  write_review_status "$ws/output/analysis.md" "待审核"

  local out
  out="$(python3 "$ROOT_DIR/tools/validator_source/validate.py" "$ws" --action design-solution --json || true)"
  assert_json_status "$out" "fail"
  assert_contains_issue_type "$out" "unconfirmed_analysis"
}

test_validator_blocks_confirmed_analysis_with_unresolved_requirement_decisions() {
  local ws="$TMP_DIR/analysis-unresolved-decisions"
  write_base_workspace "$ws"
  cat > "$ws/output/analysis.md" <<'EOF'
# 需求分析 — Demo

## 审核状态

- 状态：已确认
- 审核人：User
- 审核时间：2026-06-10 10:00
- 修订来源：

## PRD 来源

demo

## 文件清单

| ID | 文件 |
|---|---|
| PRD-01 | req.md |

## 需求概要

demo

## 功能需求

### 需求纳入决策表

| ID | 标题 | 所属模块 | 来源 | 处理方式 |
|---|---|---|---|---|
| REQ-001 | 示例需求 | demo | PRD-01 |  |
| REQ-002 | 待决策需求 | demo | PRD-01 | 待决策 |

### 需求详情

#### REQ-001 — 示例需求

**所属模块：** demo

**变更内容：**
- demo

**处理逻辑：**
- demo

**约束条件：**
- demo

**需求来源：** PRD-01

**不纳入原因：**

**原文引用：**
> demo

#### REQ-002 — 待决策需求

**所属模块：** demo

**变更内容：**
- demo

**处理逻辑：**
- demo

**约束条件：**
- demo

**需求来源：** PRD-01

**不纳入原因：**

**原文引用：**
> demo
EOF

  local out
  out="$(python3 "$ROOT_DIR/tools/validator_source/validate.py" "$ws" --action design-solution --json || true)"
  assert_json_status "$out" "fail"
  assert_contains_issue_type "$out" "analysis_confirmed_with_unresolved_requirement_decisions"
}

test_invalidate_downstream_marks_confirmed_outputs_stale() {
  local ws="$TMP_DIR/invalidate-downstream"
  write_base_workspace "$ws"
  write_review_status "$ws/output/specs/T-001.md" "待审核"
  write_review_status "$ws/output/reports/T-001.md" "已确认"
  write_valid_test_report "$ws/output/test-reports/T-001.md" "已确认"

  python3 "$ROOT_DIR/wf/tools/invalidate_downstream.py" "$ws" output/specs/T-001.md

  assert_file_review_status "$ws/output/specs/T-001.md" "待审核"
  assert_file_review_status "$ws/output/reports/T-001.md" "需更新"
  assert_file_review_status "$ws/output/test-reports/T-001.md" "需更新"
  grep -q -- "- 修订来源：上游产物已更新：output/specs/T-001.md" "$ws/output/reports/T-001.md" || fail "expected report invalidation source"
  grep -q -- "- 修订来源：上游产物已更新：output/specs/T-001.md" "$ws/output/test-reports/T-001.md" || fail "expected test report invalidation source"
}

test_validator_rejects_stale_downstream_artifacts() {
  local ws="$TMP_DIR/stale-downstream"
  write_base_workspace "$ws"
  write_review_status "$ws/output/specs/T-001.md" "待审核"
  write_review_status "$ws/output/reports/T-001.md" "已确认"
  write_valid_test_report "$ws/output/test-reports/T-001.md" "已确认"

  local out
  out="$(python3 "$ROOT_DIR/tools/validator_source/validate.py" "$ws" --json || true)"
  assert_json_status "$out" "fail"
  assert_contains_issue_type "$out" "stale_downstream_artifact"
}

test_validator_accepts_needs_update_review_status() {
  local ws="$TMP_DIR/needs-update-status"
  write_base_workspace "$ws"
  write_review_status "$ws/output/reports/T-001.md" "需更新"

  local out
  out="$(python3 "$ROOT_DIR/tools/validator_source/validate.py" "$ws" --json || true)"
  assert_json_status "$out" "pass"
}

test_validator_implement_requires_design_tasks() {
  local ws="$TMP_DIR/implement-no-design"
  local repo="$TMP_DIR/code-repo"
  mkdir -p "$repo"
  write_base_workspace "$ws"
  python3 - "$ws/CONTEXT.md" "$repo" <<'PY'
from pathlib import Path
import sys
context = Path(sys.argv[1])
repo = sys.argv[2]
text = context.read_text()
text = text.replace("- 代码仓库：无", f"- 代码仓库：{repo}")
text = text.replace("- 下一步：analyze-requirements", "- 下一步：implement-code")
context.write_text(text)
PY

  local out
  out="$(python3 "$ROOT_DIR/tools/validator_source/validate.py" "$ws" --action implement-code --json || true)"
  assert_json_status "$out" "fail"
  assert_contains_issue_type "$out" "unconfirmed_design"
}

test_validator_generate_specs_requires_design_tasks() {
  local ws="$TMP_DIR/generate-specs-empty-design"
  write_base_workspace "$ws"
  write_review_status "$ws/output/analysis.md" "已确认"
  cat > "$ws/output/design.md" <<'EOF'
# 技术方案 — Demo

## 审核状态

- 状态：已确认
- 审核人：User
- 审核时间：2026-06-10 10:00
- 修订来源：

## 任务总览

| ID | 任务标题 | 关联需求 | 依赖 | 状态 |
|---|---|---|---|---|

## 任务详情
EOF

  local out
  out="$(python3 "$ROOT_DIR/tools/validator_source/validate.py" "$ws" --action generate-specs --json || true)"
  assert_json_status "$out" "fail"
  assert_contains_issue_type "$out" "missing_design_tasks"
}

test_validator_generate_tests_requires_confirmed_spec() {
  local ws="$TMP_DIR/generate-tests-missing-spec"
  local repo="$TMP_DIR/generate-tests-repo"
  mkdir -p "$repo"
  write_base_workspace "$ws"
  cat > "$ws/CONTEXT.md" <<EOF
# 工作空间上下文 — Demo

## 需求概要

Demo

## 当前状态

- 阶段：implementation_done
- 待决策：0 项（详见 ISSUES.md）
- 下一步：generate-tests
- 待处理产物：
  - 暂无
- 规格：
  - T-001 — 示例任务 ✅ 已实现

## 项目约束

- 平台：HarmonyOS
- 代码仓库：$repo

## 代码产出

| 任务 | 状态 |
|---|---|
| T-001 | ✅ 已完成 |

## 测试记录

| 任务 | 测试文件 | 状态 |
|---|---|---|
| T-001 | — | 待测试 |
EOF
  cat > "$ws/output/design.md" <<'EOF'
# 技术方案 — Demo

## 审核状态

- 状态：已确认
- 审核人：User
- 审核时间：2026-06-10 10:00
- 修订来源：

## 任务总览

| ID | 任务标题 | 关联需求 | 依赖 | 状态 |
|---|---|---|---|---|
| T-001 | 示例任务 | REQ-001 | — | 待开发 |

## 设计视图

### 类关系图

不适用：无代码仓库。

## 任务详情

### T-001 — 示例任务

**技术目标：**
- demo

**关联需求：**
- REQ-001

**依赖：** 无

**模块架构：**
- demo

**接口/方法定义：**
- 无

**数据结构：**
- 无数据结构变更。

**设计约束：**
- 无

**影响范围：**
- src/demo.ts
EOF
  cat > "$ws/output/reports/T-001.md" <<'EOF'
# 代码生成报告 — T-001 示例任务

## 审核状态

- 状态：已确认
- 审核人：User
- 审核时间：2026-06-10 10:00
- 修订来源：

## 修改清单

| # | 文件 | 类型 | 按规格 | 说明 |
|---|---|---|---|---|
| 1 | `src/demo.ts` | 修改 | ✅ | demo |

## 偏离说明

无
EOF

  local out
  out="$(python3 "$ROOT_DIR/tools/validator_source/validate.py" "$ws" --action generate-tests --json || true)"
  assert_json_status "$out" "fail"
  assert_contains_issue_type "$out" "missing_confirmed_spec_for_tests"
}

test_validator_duplicate_ids_are_failures() {
  local ws="$TMP_DIR/duplicate-ids"
  write_base_workspace "$ws"
  cat > "$ws/ISSUES.md" <<'EOF'
# 待澄清

## 分析阶段

### Q-001 — A

- **问题：** A
- **AI 建议：** A
- **影响：** A
- **提出：** 2026-06-10 test

---

**人工决策：** 确认调整
**状态：** 待决策

## 设计阶段

### Q-001 — B

- **问题：** B
- **AI 建议：** B
- **影响：** B
- **提出：** 2026-06-10 test

---

**人工决策：** 确认调整
**状态：** 待决策

## 实现阶段

暂无

## 测试阶段

暂无
EOF

  local out
  out="$(python3 "$ROOT_DIR/tools/validator_source/validate.py" "$ws" --json || true)"
  assert_json_status "$out" "fail"
  assert_contains_issue_type "$out" "duplicate_issue_id"
}

test_validator_warns_for_open_issues() {
  local ws="$TMP_DIR/open-issues-warn"
  write_base_workspace "$ws"
  cat > "$ws/ISSUES.md" <<'EOF'
# 待澄清

## 分析阶段

### Q-001 — 确认需求口径

- **问题：** 是否按曝光作为已读口径？
- **AI 建议：** 请确认口径。
- **影响：** output/analysis.md
- **提出：** 2026-06-10 analyze-requirements

---

**人工决策：**
**状态：** 待决策

## 设计阶段

暂无

## 实现阶段

暂无

## 测试阶段

暂无
EOF

  local out
  out="$(python3 "$ROOT_DIR/tools/validator_source/validate.py" "$ws" --json || true)"
  assert_json_status "$out" "warn"
  assert_contains_issue_type "$out" "open_issue"
}

test_validator_blocks_action_when_open_issue_impacts_input() {
  local ws="$TMP_DIR/open-issue-blocks-action"
  write_base_workspace "$ws"
  write_review_status "$ws/output/analysis.md" "已确认"
  cat > "$ws/ISSUES.md" <<'EOF'
# 待澄清

## 分析阶段

### Q-001 — 确认需求口径

- **问题：** 是否按曝光作为已读口径？
- **AI 建议：** 请确认口径。
- **影响：** output/analysis.md
- **提出：** 2026-06-10 analyze-requirements

---

**人工决策：**
**状态：** 待决策

## 设计阶段

暂无

## 实现阶段

暂无

## 测试阶段

暂无
EOF

  local out
  out="$(python3 "$ROOT_DIR/tools/validator_source/validate.py" "$ws" --action design-solution --json || true)"
  assert_json_status "$out" "fail"
  assert_contains_issue_type "$out" "blocking_open_issue"
}

test_validator_warns_for_analysis_unresolved_phrase() {
  local ws="$TMP_DIR/analysis-unresolved-phrase"
  write_base_workspace "$ws"
  cat > "$ws/output/analysis.md" <<'EOF'
# 需求分析 — Demo

## 审核状态

- 状态：已确认
- 审核人：User
- 审核时间：2026-06-10 10:00
- 修订来源：

## PRD 来源

demo

## 文件清单

| ID | 文件 |
|---|---|
| PRD-01 | req.md |

## 需求概要

存在已读口径待确认。

## 功能需求

### 需求纳入决策表

| ID | 标题 | 所属模块 | 来源 | 处理方式 |
|---|---|---|---|---|
| REQ-001 | 已读上报 | demo | PRD-01 | 纳入 |

### 需求详情

#### REQ-001 — 已读上报

**所属模块：** demo

**变更内容：**
- demo

**处理逻辑：**
- demo

**约束条件：**
- demo

**需求来源：** PRD-01

**不纳入原因：**

**原文引用：**
> demo
EOF

  local out
  out="$(python3 "$ROOT_DIR/tools/validator_source/validate.py" "$ws" --json || true)"
  assert_json_status "$out" "warn"
  assert_contains_issue_type "$out" "analysis_unresolved_phrase"
}

test_validator_warns_for_missing_design_view() {
  local ws="$TMP_DIR/missing-design-view"
  write_base_workspace "$ws"
  cat > "$ws/output/design.md" <<'EOF'
# 技术方案 — Demo

## 审核状态

- 状态：已确认
- 审核人：User
- 审核时间：2026-06-10 10:00
- 修订来源：

## 任务总览

| ID | 任务标题 | 关联需求 | 依赖 | 状态 |
|---|---|---|---|---|
| T-001 | 示例任务 | REQ-001 | — | 待开发 |

## 任务详情

### T-001 — 示例任务

**技术目标：**
- demo

**关联需求：**
- REQ-001

**依赖：** 无

**模块架构：**
- demo

**接口/方法定义：**
- 无

**数据结构：**
- 无数据结构变更。

**设计约束：**
- 无

**影响范围：**
- src/demo.ts
EOF

  local out
  out="$(python3 "$ROOT_DIR/tools/validator_source/validate.py" "$ws" --json || true)"
  assert_json_status "$out" "warn"
  assert_contains_issue_type "$out" "design_view_missing"
}

test_validator_warns_for_design_view_without_mermaid_or_reason() {
  local ws="$TMP_DIR/design-view-without-diagram"
  write_base_workspace "$ws"
  cat > "$ws/output/design.md" <<'EOF'
# 技术方案 — Demo

## 审核状态

- 状态：已确认
- 审核人：User
- 审核时间：2026-06-10 10:00
- 修订来源：

## 任务总览

| ID | 任务标题 | 关联需求 | 依赖 | 状态 |
|---|---|---|---|---|
| T-001 | 示例任务 | REQ-001 | — | 待开发 |

## 设计视图

### 类关系图

后续补充。

## 任务详情

### T-001 — 示例任务

**技术目标：**
- demo

**关联需求：**
- REQ-001

**依赖：** 无

**模块架构：**
- demo

**接口/方法定义：**
- 无

**数据结构：**
- 无数据结构变更。

**设计约束：**
- 无

**影响范围：**
- src/demo.ts
EOF

  local out
  out="$(python3 "$ROOT_DIR/tools/validator_source/validate.py" "$ws" --json || true)"
  assert_json_status "$out" "warn"
  assert_contains_issue_type "$out" "design_view_without_mermaid_or_reason"
}

test_validator_blocks_confirmed_design_missing_task_fields() {
  local ws="$TMP_DIR/design-missing-task-fields"
  write_base_workspace "$ws"
  cat > "$ws/output/design.md" <<'EOF'
# 技术方案 — Demo

## 审核状态

- 状态：已确认
- 审核人：User
- 审核时间：2026-06-10 10:00
- 修订来源：

## 任务总览

| ID | 任务标题 | 关联需求 | 依赖 | 状态 |
|---|---|---|---|---|
| T-001 | 示例任务 | REQ-001 | — | 待开发 |

## 设计视图

### 类关系图

不适用：无代码仓库。

## 任务详情

### T-001 — 示例任务

**关联需求：**
- REQ-001

**需求摘要：**
- 旧字段不应继续使用。
EOF

  local out
  out="$(python3 "$ROOT_DIR/tools/validator_source/validate.py" "$ws" --json || true)"
  assert_json_status "$out" "fail"
  assert_contains_issue_type "$out" "design_confirmed_missing_required_task_field"
  assert_contains_issue_type "$out" "design_uses_legacy_requirement_summary"
}

test_validator_warns_for_behavior_detail_in_design_interface_definitions() {
  local ws="$TMP_DIR/design-interface-behavior-detail"
  write_base_workspace "$ws"
  write_review_status "$ws/output/specs/T-001.md" "已确认"
  cat > "$ws/output/design.md" <<'EOF'
# 技术方案 — Demo

## 审核状态

- 状态：已确认
- 审核人：User
- 审核时间：2026-06-10 10:00
- 修订来源：

## 任务总览

| ID | 任务标题 | 关联需求 | 依赖 | 状态 |
|---|---|---|---|---|
| T-001 | 示例任务 | REQ-001 | — | 待开发 |

## 设计视图

### 类关系图

不适用：无代码仓库。

## 任务详情

### T-001 — 示例任务

**关联需求：** REQ-001

**技术目标：**
- demo

**依赖：** 无

**模块架构：**
- demo

**接口/方法定义：**
- `src/demo.ts` — `loadItems(params?: LoadParams): Item[]`，兼容无参调用时返回空数组

**数据结构：**
- 无

**设计约束：**
- 无

**影响范围：**
- src/demo.ts
EOF

  local out
  out="$(python3 "$ROOT_DIR/tools/validator_source/validate.py" "$ws" --json || true)"
  assert_json_status "$out" "warn"
  assert_contains_issue_type "$out" "design_interface_contains_behavior_detail"
}

test_validator_warns_for_unchanged_item_in_design_interface_definitions() {
  local ws="$TMP_DIR/design-interface-unchanged-item"
  write_base_workspace "$ws"
  write_review_status "$ws/output/specs/T-001.md" "已确认"
  cat > "$ws/output/design.md" <<'EOF'
# 技术方案 — Demo

## 审核状态

- 状态：已确认
- 审核人：User
- 审核时间：2026-06-10 10:00
- 修订来源：

## 任务总览

| ID | 任务标题 | 关联需求 | 依赖 | 状态 |
|---|---|---|---|---|
| T-001 | 示例任务 | REQ-001 | — | 待开发 |

## 设计视图

### 类关系图

不适用：无代码仓库。

## 任务详情

### T-001 — 示例任务

**关联需求：** REQ-001

**技术目标：**
- demo

**依赖：** 无

**模块架构：**
- demo

**接口/方法定义：**
- `src/existing.ts` — `existingMethod(): void`，复用现有接口，不改动

**数据结构：**
- 无

**设计约束：**
- 无

**影响范围：**
- src/existing.ts
EOF

  local out
  out="$(python3 "$ROOT_DIR/tools/validator_source/validate.py" "$ws" --json || true)"
  assert_json_status "$out" "warn"
  assert_contains_issue_type "$out" "design_interface_contains_unchanged_item"
}

test_design_contract_uses_technical_task_sections() {
  local contract="$ROOT_DIR/wf/contracts/design.md"

  grep -q "\\*\\*技术目标：\\*\\*" "$contract" || fail "design contract should use technical target instead of requirement summary"
  ! grep -q "\\*\\*需求摘要：\\*\\*" "$contract" || fail "design contract should not keep requirement summary in task details"
  grep -q "不得复述 PRD 原文" "$contract" || fail "technical target should reject PRD restatement"
  grep -q "任务局部 Mermaid" "$contract" || fail "module architecture should allow task-local diagrams"
  grep -q "无数据结构变更" "$contract" || fail "data structure section should allow explicit no-change text"
  grep -q "不写未变化字段" "$contract" || fail "data structure section should reject unchanged fields"
}

test_design_diagram_labels_require_chinese_explanations() {
  local contract="$ROOT_DIR/wf/contracts/design.md"
  local capability="$ROOT_DIR/wf/capabilities/design-solution.md"

  grep -q "图中的说明文字必须使用中文" "$contract" || fail "design contract should require Chinese diagram explanations"
  grep -q "类型名、方法名、字段名、文件名、接口名、类名、枚举值等代码标识可以保持英文或项目原始命名" "$contract" || fail "design contract should allow code identifiers to keep original names"
  grep -q "图中的说明文字必须使用中文" "$capability" || fail "design capability should require Chinese diagram explanations"
}

test_readme_describes_current_framework_loop() {
  local readme="$ROOT_DIR/README.md"

  grep -q "从 PRD 到测试报告" "$readme" || fail "README should describe the end-to-end framework loop"
  grep -q "review-artifact" "$readme" || fail "README should document review-artifact gate"
  grep -q "需求纳入决策表" "$readme" || fail "README should document analysis decision table"
  grep -q "设计视图" "$readme" || fail "README should document design views"
  grep -q "需更新" "$readme" || fail "README should document downstream invalidation"
  grep -q "dashboard.html" "$readme" || fail "README should document review dashboard"
  grep -q "scripts/sync_validator_tools.py" "$readme" || fail "README should document validator sync"
}

test_generate_specs_reads_technical_design_fields() {
  local capability="$ROOT_DIR/wf/capabilities/generate-specs.md"

  grep -q "技术目标" "$capability" || fail "generate-specs should read design technical target"
  grep -q "设计约束" "$capability" || fail "generate-specs should read design constraints"
  grep -q "影响范围" "$capability" || fail "generate-specs should read design impact scope"
  grep -q "不得只依据任务标题" "$capability" || fail "generate-specs should not rely only on task title"
}

test_validator_allows_decision_resolution_with_pending_revision_artifact() {
  local ws="$TMP_DIR/blocked-decision-with-pending"
  write_base_workspace "$ws"
  cat > "$ws/ISSUES.md" <<'EOF'
# 待澄清

## 分析阶段

### Q-001 — 是否调整需求

- **问题：** 是否调整需求？
- **AI 建议：** 请确认。
- **影响：** output/analysis.md
- **提出：** 2026-06-10 wf

---

**人工决策：** 确认调整
**状态：** 待决策

## 设计阶段

暂无

## 实现阶段

暂无

## 测试阶段

暂无
EOF
  cat > "$ws/output/analysis.md" <<'EOF'
# 需求分析 — Demo

## 审核状态

- 状态：需修改
- 审核人：
- 审核时间：
- 修订来源：R-001

## 需求概要

Demo
EOF
  python3 - "$ws/CONTEXT.md" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text()
text = text.replace("- 阶段：initialized", "- 阶段：blocked_by_decision")
text = text.replace("- 待决策：0 项（详见 ISSUES.md）", "- 待决策：1 项（详见 ISSUES.md）")
text = text.replace("- 下一步：analyze-requirements", "- 下一步：resolve-decision")
text = text.replace("  - 暂无", "  - output/analysis.md（需修改）", 1)
path.write_text(text)
PY

  local out
  out="$(python3 "$ROOT_DIR/tools/validator_source/validate.py" "$ws" --action resolve-decision --json || true)"
  assert_json_status "$out" "pass"
}

test_validator_resolve_decision_requires_target_issue_decision() {
  local ws="$TMP_DIR/resolve-decision-guards"
  write_base_workspace "$ws"
  cat > "$ws/ISSUES.md" <<'EOF'
# 待澄清

## 分析阶段

### Q-001 — 缺少决策

- **问题：** 是否调整需求？
- **AI 建议：** 请确认。
- **影响：** output/analysis.md
- **提出：** 2026-06-10 wf

---

**人工决策：**
**状态：** 待决策

## 设计阶段

暂无

## 实现阶段

暂无

## 测试阶段

暂无
EOF
  python3 - "$ws/CONTEXT.md" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text()
text = text.replace("- 阶段：initialized", "- 阶段：blocked_by_decision")
text = text.replace("- 待决策：0 项（详见 ISSUES.md）", "- 待决策：1 项（详见 ISSUES.md）")
text = text.replace("- 下一步：analyze-requirements", "- 下一步：resolve-decision")
path.write_text(text)
PY

  local out
  out="$(python3 "$ROOT_DIR/tools/validator_source/validate.py" "$ws" --action resolve-decision --target Q-001 --json || true)"
  assert_json_status "$out" "fail"
  assert_contains_issue_type "$out" "missing_manual_decision"

  python3 - "$ws/ISSUES.md" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text()
text = text.replace("**人工决策：**", "**人工决策：** 确认调整")
path.write_text(text)
PY
  out="$(python3 "$ROOT_DIR/tools/validator_source/validate.py" "$ws" --action resolve-decision --target Q-001 --json || true)"
  assert_json_status "$out" "pass"
}

test_sync_validator_copies_source() {
  python3 "$ROOT_DIR/scripts/sync_validator_tools.py" --check >/dev/null
}

test_rebuild_context_repairs_pending_artifacts() {
  local ws="$TMP_DIR/rebuild-pending"
  write_base_workspace "$ws"
  write_review_status "$ws/output/analysis.md" "待审核"

  python3 "$ROOT_DIR/wf/tools/rebuild_context.py" "$ws"
  grep -q -- "- 下一步：review-artifact" "$ws/CONTEXT.md" || fail "expected review-artifact after rebuild"
  grep -q -- "- output/analysis.md（待审核）" "$ws/CONTEXT.md" || fail "expected pending analysis artifact"
}

test_rebuild_context_repairs_false_completion() {
  local ws="$TMP_DIR/rebuild-false-completion"
  write_base_workspace "$ws"
  cat > "$ws/output/design.md" <<'EOF'
# 技术方案 — Demo

## 审核状态

- 状态：已确认
- 审核人：User
- 审核时间：2026-06-10 10:00
- 修订来源：

## 任务总览

| ID | 任务标题 | 关联需求 | 依赖 | 状态 |
|---|---|---|---|---|
| T-001 | 示例任务 | REQ-001 | — | 待开发 |

## 任务详情

### T-001 — 示例任务
EOF
  write_review_status "$ws/output/specs/T-001.md" "已确认"
  python3 - "$ws/CONTEXT.md" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text()
text = text.replace("- 规格：\n  - 暂无", "- 规格：\n  - T-001 — 示例任务 ✅ 已实现")
text = text.replace("| — | — |", "| T-001 | ✅ 已完成 |")
path.write_text(text)
PY

  local before
  before="$(python3 "$ROOT_DIR/tools/validator_source/validate.py" "$ws" --json || true)"
  assert_json_status "$before" "fail"
  assert_contains_issue_type "$before" "missing_confirmed_report"

  python3 "$ROOT_DIR/wf/tools/rebuild_context.py" "$ws"
  if grep -q "✅ 已实现" "$ws/CONTEXT.md"; then
    fail "expected rebuild to remove false implemented marker"
  fi
  grep -q "T-001" "$ws/CONTEXT.md" || fail "expected task to remain in context"
}

test_rebuild_context_counts_issues_with_task_ids() {
  local ws="$TMP_DIR/rebuild-issue-count"
  write_base_workspace "$ws"
  cat > "$ws/ISSUES.md" <<'EOF'
# 待澄清

## 实现阶段

### Q-001 — T-001 是否调整

- **问题：** T-001 是否调整实现范围？
- **AI 建议：** 请确认。
- **影响：** T-001
- **提出：** 2026-06-10 implement-code

---

**人工决策：**
**状态：** 待决策
EOF

  python3 "$ROOT_DIR/wf/tools/rebuild_context.py" "$ws"
  grep -q -- "- 待决策：1 项（详见 ISSUES.md）" "$ws/CONTEXT.md" || fail "expected issue count to include Q block with T id"
}

test_rebuild_context_does_not_use_test_report_as_test_file() {
  local ws="$TMP_DIR/rebuild-test-file"
  write_base_workspace "$ws"
  cat > "$ws/output/design.md" <<'EOF'
# 技术方案 — Demo

## 审核状态

- 状态：已确认
- 审核人：User
- 审核时间：2026-06-10 10:00
- 修订来源：

## 任务总览

| ID | 任务标题 | 关联需求 | 依赖 | 状态 |
|---|---|---|---|---|
| T-001 | 示例任务 | REQ-001 | — | 待开发 |

## 设计视图

### 类关系图

```mermaid
classDiagram
  class DemoViewModel
  class DemoReporter
  DemoViewModel --> DemoReporter : uses
```
EOF
  write_review_status "$ws/output/specs/T-001.md" "已确认"
  write_review_status "$ws/output/reports/T-001.md" "已确认"
  cat > "$ws/output/test-reports/T-001.md" <<'EOF'
# 单元测试报告 — T-001 示例任务

## 审核状态

- 状态：已确认
- 审核人：User
- 审核时间：2026-06-10 10:00
- 修订来源：

## 任务范围

demo

## 已生成单元测试

| # | 行为 | 测试点 | 测试文件 | 状态 | 说明 |
|---|---|---|---|---|---|
| 1 | normal | branch | `tests/Demo.test.ts` | 已生成 | demo |

## 未生成单元测试

| # | 行为 | 测试点 | 测试文件 | 状态 | 说明 |
|---|---|---|---|---|---|
| — | 无 | — | — | — | 全部目标行为已生成单元测试 |

## 辅助验证记录

| # | 验证项 | 命令/方式 | 结果 | 说明 |
|---|---|---|---|---|
| — | 未执行 | — | 未执行 | 缺少可用测试执行脚本 |

## 结论

已生成单测
EOF

  python3 "$ROOT_DIR/wf/tools/rebuild_context.py" "$ws"
  if grep -q "| T-001 | output/test-reports/T-001.md | ✅ 已完成 |" "$ws/CONTEXT.md"; then
    fail "test report path must not be used as test file path"
  fi
  grep -q "| T-001 | tests/Demo.test.ts | ✅ 已完成 |" "$ws/CONTEXT.md" || fail "expected test file from test report"
}

test_rebuild_context_uses_analysis_summary_and_preserves_constraints() {
  local ws="$TMP_DIR/rebuild-summary"
  write_base_workspace "$ws"
  python3 - "$ws/CONTEXT.md" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text()
text = text.replace("\nDemo\n\n## 当前状态", "\n旧需求概要\n\n## 当前状态")
text = text.replace("- 平台：HarmonyOS", "- 平台：CustomOS")
text = text.replace("- 代码仓库：无", "- 代码仓库：/tmp/custom-repo")
path.write_text(text)
PY
  cat > "$ws/output/analysis.md" <<'EOF'
# 需求分析 — Demo

## 审核状态

- 状态：已确认
- 审核人：User
- 审核时间：2026-06-10 10:00
- 修订来源：

## 需求概要

- 新需求概要来自 analysis
- 共 2 项候选需求

## 功能需求

### 需求纳入决策表

| ID | 标题 | 所属模块 | 来源 | 处理方式 |
|---|---|---|---|---|
| REQ-001 | 示例需求 | demo | PRD-01 | 纳入 |
EOF

  python3 "$ROOT_DIR/wf/tools/rebuild_context.py" "$ws"
  grep -q "新需求概要来自 analysis" "$ws/CONTEXT.md" || fail "expected summary from analysis"
  if grep -q "旧需求概要" "$ws/CONTEXT.md"; then
    fail "expected old context summary to be replaced"
  fi
  grep -q -- "- 平台：CustomOS" "$ws/CONTEXT.md" || fail "expected project platform to be preserved"
  grep -q -- "- 代码仓库：/tmp/custom-repo" "$ws/CONTEXT.md" || fail "expected project repo to be preserved"
}

test_render_review_dashboard_creates_root_html() {
  local ws="$TMP_DIR/dashboard"
  write_base_workspace "$ws"
  python3 - "$ws/CONTEXT.md" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text()
path.write_text(text.replace("- 代码仓库：无", "- 代码仓库：/tmp/demo-repo"))
PY
  cat > "$ws/README.md" <<'EOF'
# Demo Workspace
EOF
  cat > "$ws/JOURNAL.md" <<'EOF'
# 工作日志

## 2026-06-10

### 10:01 — 日志 01

- 记录：第 1 条日志

### 10:02 — 日志 02

- 记录：第 2 条日志

### 10:03 — 日志 03

- 记录：第 3 条日志

### 10:04 — 日志 04

- 记录：第 4 条日志

### 10:05 — 日志 05

- 记录：第 5 条日志

### 10:06 — 日志 06

- 记录：第 6 条日志

### 10:07 — 日志 07

- 记录：第 7 条日志

### 10:08 — 日志 08

- 记录：第 8 条日志

### 10:09 — 日志 09

- 记录：第 9 条日志
EOF
  cat > "$ws/CHANGELOG.md" <<'EOF'
# 变更记录

## 2026-06-10

### 10:01 — 决策 01

- **问题：** 示例问题 01
- **决策：** 示例决策 01
- **影响：** output/analysis.md
- **处理：** 已归档

### 10:02 — 决策 02

- **问题：** 示例问题 02
- **决策：** 示例决策 02
- **影响：** output/analysis.md
- **处理：** 已归档

### 10:03 — 决策 03

- **问题：** 示例问题 03
- **决策：** 示例决策 03
- **影响：** output/analysis.md
- **处理：** 已归档

### 10:04 — 决策 04

- **问题：** 示例问题 04
- **决策：** 示例决策 04
- **影响：** output/analysis.md
- **处理：** 已归档

### 10:05 — 决策 05

- **问题：** 示例问题 05
- **决策：** 示例决策 05
- **影响：** output/analysis.md
- **处理：** 已归档

### 11:30 — 示例决策（来自 ISSUES.md Q-001）

- **问题：** 示例问题
- **决策：** 示例决策
- **影响：** output/analysis.md
- **处理：** 已归档
EOF
  cat > "$ws/output/analysis.md" <<'EOF'
# 需求分析 — Demo

## 审核状态

- 状态：待审核
- 审核人：
- 审核时间：
- 修订来源：

## 需求概要

Demo

## 功能需求

### 需求纳入决策表

| ID | 标题 | 所属模块 | 来源 | 处理方式 |
|---|---|---|---|---|
| REQ-001 | 示例纳入需求 | demo | PRD-01 | 纳入 |
| REQ-002 | 示例排除需求 | demo | PRD-01 | 暂不纳入 |
| REQ-003 | 示例待决策需求 | demo | PRD-01 | 待决策 |

### 原文引用

>> 用户原文引用内容

#### REQ-001 — 示例需求标题

需求标题不能比上级标题更小。
EOF
  cat > "$ws/REVISIONS.md" <<'EOF'
# 用户修订

## 待处理

暂无

## 已处理

### R-001 — 示例修订

- **目标产物：** output/analysis.md
- **修订类型：** 需求调整
- **用户意见：** 示例意见
- **影响范围：** analysis
- **状态：** 已处理
- **处理结果：** 已更新
- **更新产物：** output/analysis.md
- **处理时间：** 2026-06-10 11:00

### R-002 — 更新修订

- **目标产物：** output/design.md
- **修订类型：** 方案调整
- **用户意见：** 更新意见
- **影响范围：** design
- **状态：** 已处理
- **处理结果：** 已更新
- **更新产物：** output/design.md
- **处理时间：** 2026-06-10 12:00
EOF
  cat > "$ws/output/design.md" <<'EOF'
# 技术方案 — Demo

## 审核状态

- 状态：已确认
- 审核人：User
- 审核时间：2026-06-10 10:00
- 修订来源：

## 任务总览

| ID | 任务标题 | 关联需求 | 依赖 | 状态 |
|---|---|---|---|---|
| T-001 | 示例任务 | REQ-001 | — | 待开发 |

## 设计视图

### 类关系图

```mermaid
classDiagram
  class DemoViewModel
  class DemoReporter
  DemoViewModel --> DemoReporter : uses
```
EOF
  write_review_status "$ws/output/specs/T-001.md" "已确认"
  write_review_status "$ws/output/reports/T-001.md" "待审核"

  python3 "$ROOT_DIR/wf/tools/render_review_dashboard.py" "$ws" >/dev/null

  test -f "$ws/dashboard.html" || fail "expected dashboard.html to be generated in workspace root"
  grep -q "<h1>Demo</h1>" "$ws/dashboard.html" || fail "expected project dashboard title"
  if grep -q "Demo 工作流" "$ws/dashboard.html"; then
    fail "dashboard title must not append workflow suffix"
  fi
  if grep -q "<h1>AIWorkFlow Dashboard</h1>" "$ws/dashboard.html"; then
    fail "dashboard title must use project name"
  fi
  grep -q "项目上下文" "$ws/dashboard.html" || fail "expected project context"
  grep -q "页面大纲" "$ws/dashboard.html" || fail "expected outline sidebar"
  grep -q 'href="#revisions"' "$ws/dashboard.html" || fail "expected outline anchor links"
  grep -q 'id="revisions"' "$ws/dashboard.html" || fail "expected revision section anchor"
  grep -q "pipeline-step" "$ws/dashboard.html" || fail "expected workflow pipeline"
  grep -q "data-state=" "$ws/dashboard.html" || fail "expected pipeline state attributes"
  grep -q "需求分析" "$ws/dashboard.html" || fail "expected pipeline analysis step"
  grep -q "测试生成" "$ws/dashboard.html" || fail "expected pipeline test step"
  grep -q "结构完整" "$ws/dashboard.html" || fail "expected workspace status"
  if grep -q "需要人工关注" "$ws/dashboard.html"; then
    fail "attention summary metric should be removed"
  fi
  grep -q 'class="metric" href="#issues"' "$ws/dashboard.html" || fail "expected issue metric anchor"
  grep -q 'class="metric" href="#revisions"' "$ws/dashboard.html" || fail "expected revision metric anchor"
  grep -q 'class="metric" href="#artifacts"' "$ws/dashboard.html" || fail "expected artifact metric anchor"
  grep -q "/tmp/demo-repo" "$ws/dashboard.html" || fail "expected concrete code repo path"
  grep -q "prd/req.md" "$ws/dashboard.html" || fail "expected prd file list"
  grep -q "output/analysis.md" "$ws/dashboard.html" || fail "expected artifact path"
  grep -q 'href="#artifact-output-analysis-md"' "$ws/dashboard.html" || fail "expected artifact content anchor link"
  grep -q 'id="artifact-output-analysis-md"' "$ws/dashboard.html" || fail "expected artifact preview anchor"
  grep -q 'href="#artifact-output-specs-t-001-md"' "$ws/dashboard.html" || fail "expected task artifact anchor link"
  grep -q 'id="artifact-content"' "$ws/dashboard.html" || fail "expected artifact content section"
  grep -q "artifact-preview" "$ws/dashboard.html" || fail "expected artifact preview details"
  grep -q "artifact-preview-head" "$ws/dashboard.html" || fail "expected document-style artifact preview header"
  grep -q "artifact-markdown" "$ws/dashboard.html" || fail "expected rendered markdown preview"
  grep -q 'class="mermaid"' "$ws/dashboard.html" || fail "expected mermaid diagram container"
  grep -q "mermaid@11" "$ws/dashboard.html" || fail "expected mermaid CDN script"
  grep -q "mermaid.initialize" "$ws/dashboard.html" || fail "expected mermaid initialization"
  grep -q 'id="diagramViewer"' "$ws/dashboard.html" || fail "expected diagram fullscreen viewer"
  grep -q 'id="diagramZoomIn"' "$ws/dashboard.html" || fail "expected diagram zoom in control"
  grep -q 'id="diagramZoomOut"' "$ws/dashboard.html" || fail "expected diagram zoom out control"
  grep -q 'id="diagramZoomReset"' "$ws/dashboard.html" || fail "expected diagram zoom reset control"
  grep -q 'id="diagramClose"' "$ws/dashboard.html" || fail "expected diagram close control"
  grep -q "openDiagramViewer" "$ws/dashboard.html" || fail "expected diagram open handler"
  grep -q "applyDiagramTransform" "$ws/dashboard.html" || fail "expected diagram transform handler"
  grep -q "pointerdown" "$ws/dashboard.html" || fail "expected diagram drag handler"
  grep -q "wheel" "$ws/dashboard.html" || fail "expected diagram wheel zoom handler"
  grep -q "md-table-wrap" "$ws/dashboard.html" || fail "expected markdown table rendering"
  grep -q "<h5>REQ-001 — 示例需求标题</h5>" "$ws/dashboard.html" || fail "expected deep requirement heading rendering"
  grep -q ".artifact-markdown h3 { font-size: 17px;" "$ws/dashboard.html" || fail "expected artifact h3 heading size"
  grep -q ".artifact-markdown h4 { font-size: 16px;" "$ws/dashboard.html" || fail "expected artifact h4 heading size"
  grep -q ".artifact-markdown h5 { font-size: 15px;" "$ws/dashboard.html" || fail "expected artifact h5 heading size"
  grep -q "<blockquote>" "$ws/dashboard.html" || fail "expected blockquote rendering"
  grep -q "用户原文引用内容" "$ws/dashboard.html" || fail "expected blockquote content"
  if grep -q "&gt;&gt; 用户原文引用内容" "$ws/dashboard.html"; then
    fail "blockquote markers should be stripped from artifact preview"
  fi
  grep -q "openArtifactTarget" "$ws/dashboard.html" || fail "expected artifact anchor auto-open script"
  if grep -q 'href="output/analysis.md"' "$ws/dashboard.html"; then
    fail "dashboard must not link directly to markdown artifacts"
  fi
  grep -q "待审核" "$ws/dashboard.html" || fail "expected pending review status"
  grep -q "todo-type" "$ws/dashboard.html" || fail "expected redesigned todo type column"
  grep -q "todo-meta" "$ws/dashboard.html" || fail "expected redesigned todo metadata"
  grep -q -- '--card-bg:' "$ws/dashboard.html" || fail "expected shared card background token"
  grep -q '<span class="pill warn">待审核</span>' "$ws/dashboard.html" || fail "expected unified pending review status pill"
  grep -q -- '--warn: #d6a100;' "$ws/dashboard.html" || fail "expected bright yellow pending review color"
  grep -q 'status-count warn' "$ws/dashboard.html" || fail "expected unified pending review status count"
  grep -q "todo-action" "$ws/dashboard.html" || fail "expected todo artifact review action layout"
  grep -q "todo-action-link" "$ws/dashboard.html" || fail "expected unified todo action button style"
  grep -q "去审核" "$ws/dashboard.html" || fail "expected todo artifact review action"
  grep -q "T-001" "$ws/dashboard.html" || fail "expected task matrix entry"
  grep -q "task-progress-board" "$ws/dashboard.html" || fail "expected card-style task progress"
  grep -q "artifact-summary-board" "$ws/dashboard.html" || fail "expected artifact summary board"
  grep -q "requirement-board" "$ws/dashboard.html" || fail "expected grouped requirement board"
  grep -q "requirement-group warn" "$ws/dashboard.html" || fail "expected pending requirement group"
  grep -q "requirement-group ok" "$ws/dashboard.html" || fail "expected included requirement group"
  grep -q "requirement-group muted" "$ws/dashboard.html" || fail "expected excluded requirement group"
  python3 - "$ws/dashboard.html" <<'PY' || fail "expected requirement groups to prioritize pending, then included, then excluded"
from pathlib import Path
import sys

html = Path(sys.argv[1]).read_text()
html = html.split('id="requirements"', 1)[1]
if not (html.index("示例待决策需求") < html.index("示例纳入需求") < html.index("示例排除需求")):
    raise SystemExit(1)
PY
  grep -q "revision-dialog" "$ws/dashboard.html" || fail "expected dialog-style revision rendering"
  grep -q -- '--revision-user-bg:' "$ws/dashboard.html" || fail "expected distinct user revision bubble color token"
  grep -q -- '--revision-result-bg:' "$ws/dashboard.html" || fail "expected distinct revision result bubble color token"
  grep -q "用户意见" "$ws/dashboard.html" || fail "expected revision user opinion label"
  grep -q "已更新" "$ws/dashboard.html" || fail "expected revision handled result"
  grep -q "处理时间：2026-06-10 11:00" "$ws/dashboard.html" || fail "expected handled revision time"
  python3 - "$ws/dashboard.html" <<'PY' || fail "expected revisions to render in reverse order"
from pathlib import Path
import sys

html = Path(sys.argv[1]).read_text()
if html.index("R-002") > html.index("R-001"):
    raise SystemExit(1)
PY
  grep -q "决策 01" "$ws/dashboard.html" || fail "expected full changelog, not recent-only entries"
  grep -q "日志 01" "$ws/dashboard.html" || fail "expected full journal, not recent-only entries"
  grep -q "timeline-date-group" "$ws/dashboard.html" || fail "expected grouped timeline rendering"
  grep -q "border-left: 2px dashed" "$ws/dashboard.html" || fail "expected dashed timeline arrows"
  grep -q "timeline-detail" "$ws/dashboard.html" || fail "expected structured timeline details"
  grep -q "timeline-detail body" "$ws/dashboard.html" || fail "expected readable timeline body detail style"
  grep -q ">问题<" "$ws/dashboard.html" || fail "expected plain changelog detail label"
  grep -q ">示例问题<" "$ws/dashboard.html" || fail "expected plain changelog detail value"
  if grep -q "\\*\\*问题" "$ws/dashboard.html"; then
    fail "timeline markdown bold markers should be cleaned"
  fi
}

test_validator_revisions_require_ordered_sections() {
  local ws="$TMP_DIR/revisions-order"
  write_base_workspace "$ws"
  cat > "$ws/REVISIONS.md" <<'EOF'
# 用户修订

## 待处理

暂无

## 已处理

### R-002 — second

- **状态：** 已处理

### R-001 — first

- **状态：** 已处理
EOF

  out="$(python3 "$ROOT_DIR/tools/validator_source/validate.py" "$ws" --json || true)"
  assert_json_status "$out" "fail"
  echo "$out" | grep -q "revision_order_invalid" || fail "expected unordered revision ids to fail"
}

test_validator_journal_requires_date_archive_order() {
  local ws="$TMP_DIR/journal-order"
  write_base_workspace "$ws"
  cat > "$ws/JOURNAL.md" <<'EOF'
# 工作日志

## 2026-06-09

## 2026-06-12

### 10:00 — later

- demo

### 09:00 — earlier

- demo

### 15:00 — old date entry under wrong date section

- demo
EOF

  out="$(python3 "$ROOT_DIR/tools/validator_source/validate.py" "$ws" --json || true)"
  assert_json_status "$out" "fail"
  echo "$out" | grep -q "journal_empty_date_section" || fail "expected empty date section to fail"
  echo "$out" | grep -q "journal_time_order_invalid" || fail "expected unordered journal time warning"
}

test_validator_detects_ordered_artifact_drift() {
  local ws="$TMP_DIR/ordered-artifacts"
  write_base_workspace "$ws"
  cat > "$ws/ISSUES.md" <<'EOF'
# 待澄清

## 分析阶段

### Q-002 — second

- **问题：** second
- **AI 建议：** demo
- **影响：** output/analysis.md
- **提出：** 2026-06-10 wf

---

**人工决策：**
**状态：** 待决策

### Q-001 — first

- **问题：** first
- **AI 建议：** demo
- **影响：** output/analysis.md
- **提出：** 2026-06-10 wf

---

**人工决策：**
**状态：** 待决策

## 设计阶段

暂无

## 实现阶段

暂无

## 测试阶段

暂无
EOF
  cat > "$ws/CHANGELOG.md" <<'EOF'
# 决策归档

## 2026-06-12

### 10:00 — later

- demo

## 2026-06-11

### 10:00 — earlier

- demo
EOF
  python3 - "$ws/CONTEXT.md" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text()
text = text.replace("  - 暂无\n\n## 项目约束", "  - T-002 — second\n  - T-001 — first\n\n## 项目约束")
text = text.replace("| — | — |", "| T-002 | ✅ 已完成 |\n| T-001 | ✅ 已完成 |", 1)
text = text.replace("| — | — | — |", "| T-002 | — | ✅ 已完成 |\n| T-001 | — | ✅ 已完成 |")
path.write_text(text)
PY
  cat > "$ws/output/analysis.md" <<'EOF'
# 需求分析 — Demo

## 审核状态

- 状态：待审核
- 审核人：
- 审核时间：
- 修订来源：

## PRD 来源

## 文件清单

| ID | 文件 |
|---|---|
| PRD-02 | b.md |
| PRD-01 | a.md |

## 需求概要

demo

## 功能需求

### 需求纳入决策表

| ID | 标题 | 所属模块 | 来源 | 处理方式 |
|---|---|---|---|---|
| REQ-002 | second | demo | PRD-02 | 纳入 |
| REQ-001 | first | demo | PRD-01 | 纳入 |

### 需求详情

#### REQ-002 — second

#### REQ-001 — first
EOF
  cat > "$ws/output/design.md" <<'EOF'
# 技术方案 — Demo

## 审核状态

- 状态：待审核
- 审核人：
- 审核时间：
- 修订来源：

## 任务总览

| ID | 任务标题 | 关联需求 | 依赖 | 状态 |
|---|---|---|---|---|
| T-002 | second | REQ-002 | — | 待开发 |
| T-001 | first | REQ-001 | — | 待开发 |

## 任务详情

### T-002 — second

### T-001 — first
EOF
  cat > "$ws/output/specs/T-001.md" <<'EOF'
# T-001 — first

## 审核状态

- 状态：待审核
- 审核人：
- 审核时间：
- 修订来源：

## 任务概述

demo

## 依赖

无

## 关键行为

demo

## 实现方案

demo

## 修改点

### 修改点 2：second

### 修改点 1：first
EOF
  cat > "$ws/output/reports/T-001.md" <<'EOF'
# 代码生成报告 — T-001 first

## 审核状态

- 状态：待审核
- 审核人：
- 审核时间：
- 修订来源：

## 修改清单

| # | 文件 | 类型 | 按规格 | 说明 |
|---|---|---|---|---|
| 2 | `b.ts` | 修改 | ✅ | demo |
| 1 | `a.ts` | 修改 | ✅ | demo |

## 偏离说明

无

### 偏离 2 — second

### 偏离 1 — first
EOF
  cat > "$ws/output/test-reports/T-001.md" <<'EOF'
# 单元测试报告 — T-001 first

## 审核状态

- 状态：待审核
- 审核人：
- 审核时间：
- 修订来源：

## 任务范围

demo

## 已生成单元测试

| # | 行为 | 测试点 | 测试文件 | 状态 | 说明 |
|---|---|---|---|---|---|
| 2 | second | demo | `b.test.ts` | 已生成 | demo |
| 1 | first | demo | `a.test.ts` | 已生成 | demo |

## 未生成单元测试

| # | 行为 | 测试点 | 测试文件 | 状态 | 说明 |
|---|---|---|---|---|---|
| — | 无 | — | — | — | 全部目标行为已生成单元测试 |
| 1 | edge | demo | — | 待补充 | reason |

## 辅助验证记录

| # | 验证项 | 命令/方式 | 结果 | 说明 |
|---|---|---|---|---|
| — | 未执行 | — | 未执行 | 缺少脚本 |
| 1 | 单元测试执行 | `run-unit.sh` | 失败 | demo |

## 结论

部分生成
EOF

  out="$(python3 "$ROOT_DIR/tools/validator_source/validate.py" "$ws" --json || true)"
  assert_json_status "$out" "fail"
  echo "$out" | grep -q "issue_order_invalid" || fail "expected issue order failure"
  echo "$out" | grep -q "changelog_date_order_invalid" || fail "expected changelog date order failure"
  echo "$out" | grep -q "context_spec_order_invalid" || fail "expected context spec order failure"
  echo "$out" | grep -q "analysis_requirement_table_order_invalid" || fail "expected analysis table order warning"
  echo "$out" | grep -q "design_task_table_order_invalid" || fail "expected design task order warning"
  echo "$out" | grep -q "spec_change_order_invalid" || fail "expected spec change order warning"
  echo "$out" | grep -q "code_report_change_list_order_invalid" || fail "expected code report change list order warning"
  echo "$out" | grep -q "code_report_deviation_order_invalid" || fail "expected code report deviation order warning"
  echo "$out" | grep -q "code_report_deviation_none_with_entries" || fail "expected code report none-with-entries failure"
  echo "$out" | grep -q "test_report_generated_order_invalid" || fail "expected test report generated order warning"
  echo "$out" | grep -q "test_report_placeholder_with_entries" || fail "expected test report placeholder-with-entries failure"
}

test_validator_rejects_legacy_test_report_structure() {
  local ws="$TMP_DIR/legacy-test-report"
  write_base_workspace "$ws"
  cat > "$ws/output/test-reports/T-001.md" <<'EOF'
# 测试报告 — T-001 legacy

## 审核状态

- 状态：待审核
- 审核人：
- 审核时间：
- 修订来源：

## 测试清单

| # | 测试用例 | 覆盖行为 | 文件 | 状态 |
|---|---|---|---|---|
| 1 | legacy | demo | `legacy.test.ts` | ✅ |

## 未覆盖行为

无
EOF

  out="$(python3 "$ROOT_DIR/tools/validator_source/validate.py" "$ws" --json || true)"
  assert_json_status "$out" "fail"
  echo "$out" | grep -q "test_report_title_invalid" || fail "expected legacy title failure"
  echo "$out" | grep -q "test_report_legacy_section" || fail "expected legacy section failure"
  echo "$out" | grep -q "test_report_missing_section" || fail "expected missing new section failure"
}

test_validator_accepts_new_test_report_structure_with_missing_scripts() {
  local ws="$TMP_DIR/new-test-report"
  write_base_workspace "$ws"
  python3 - "$ws/CONTEXT.md" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text()
text = text.replace("- 下一步：analyze-requirements", "- 下一步：review-artifact")
text = text.replace("  - 暂无", "  - output/test-reports/T-001.md（待审核）", 1)
path.write_text(text)
PY
  cat > "$ws/output/test-reports/T-001.md" <<'EOF'
# 单元测试报告 — T-001 demo

## 审核状态

- 状态：待审核
- 审核人：
- 审核时间：
- 修订来源：

## 任务范围

demo

## 已生成单元测试

| # | 行为 | 测试点 | 测试文件 | 状态 | 说明 |
|---|---|---|---|---|---|
| 1 | normal | branch | `demo.test.ts` | 已生成 | demo |

## 未生成单元测试

| # | 行为 | 测试点 | 测试文件 | 状态 | 说明 |
|---|---|---|---|---|---|
| — | 无 | — | — | — | 全部目标行为已生成单元测试 |

## 辅助验证记录

| # | 验证项 | 命令/方式 | 结果 | 说明 |
|---|---|---|---|---|
| — | 未执行 | — | 未执行 | 缺少可用测试执行脚本 |

## 结论

已生成单测
EOF

  out="$(python3 "$ROOT_DIR/tools/validator_source/validate.py" "$ws" --json || true)"
  assert_json_status "$out" "pass"
  if echo "$out" | grep -q "test_report_"; then
    fail "expected new test report structure to pass test report validation"
  fi
}

test_validator_rejects_confirmed_blocking_test_report() {
  local ws="$TMP_DIR/blocking-test-report"
  write_base_workspace "$ws"
  cat > "$ws/output/test-reports/T-001.md" <<'EOF'
# 单元测试报告 — T-001 blocking

## 审核状态

- 状态：已确认
- 审核人：User
- 审核时间：2026-06-10 10:00
- 修订来源：

## 任务范围

demo

## 已生成单元测试

| # | 行为 | 测试点 | 测试文件 | 状态 | 说明 |
|---|---|---|---|---|---|
| 1 | normal | branch | `demo.test.ts` | 已生成，未通过 | assertion failed |

## 未生成单元测试

| # | 行为 | 测试点 | 测试文件 | 状态 | 说明 |
|---|---|---|---|---|---|
| 1 | edge | edge | — | 阻塞 | 需要决策 |

## 辅助验证记录

| # | 验证项 | 命令/方式 | 结果 | 说明 |
|---|---|---|---|---|
| 1 | 单元测试执行 | `run-unit.sh` | 失败 | demo |

## 结论

阻塞
EOF

  out="$(python3 "$ROOT_DIR/tools/validator_source/validate.py" "$ws" --json || true)"
  assert_json_status "$out" "fail"
  echo "$out" | grep -q "test_report_confirmed_with_blocking_status" || fail "expected confirmed blocking test report failure"
}

test_validator_requires_output_subdirectories() {
  local ws="$TMP_DIR/missing-output-subdirs"
  write_base_workspace "$ws"
  rm -rf "$ws/output/reports" "$ws/output/test-reports"

  out="$(python3 "$ROOT_DIR/tools/validator_source/validate.py" "$ws" --json || true)"
  assert_json_status "$out" "fail"
  echo "$out" | grep -q "缺少 output/reports/" || fail "expected missing reports directory failure"
  echo "$out" | grep -q "缺少 output/test-reports/" || fail "expected missing test reports directory failure"
}

test_wf_init_agent_template_uses_rendered_coding_rules() {
  if grep -q "如果 .*不是 HarmonyOS" "$ROOT_DIR/wf-init/templates/AGENT.md"; then
    fail "AGENT template must not leak platform conditional instructions"
  fi
  grep -q "{编码规范}" "$ROOT_DIR/wf-init/templates/AGENT.md" || fail "AGENT template should use coding rules placeholder"
  grep -q "{编码规范}" "$ROOT_DIR/wf-init/SKILL.md" || fail "wf-init should document coding rules rendering"
  grep -q "通用编码规范正文" "$ROOT_DIR/wf-init/SKILL.md" || fail "wf-init should include non-HarmonyOS coding rules"
}

test_validator_detects_pending_artifact_mismatch
test_validator_action_guard_blocks_unconfirmed_analysis
test_validator_blocks_confirmed_analysis_with_unresolved_requirement_decisions
test_invalidate_downstream_marks_confirmed_outputs_stale
test_validator_rejects_stale_downstream_artifacts
test_validator_accepts_needs_update_review_status
test_validator_implement_requires_design_tasks
test_validator_generate_specs_requires_design_tasks
test_validator_generate_tests_requires_confirmed_spec
test_validator_duplicate_ids_are_failures
test_validator_warns_for_open_issues
test_validator_blocks_action_when_open_issue_impacts_input
test_validator_warns_for_analysis_unresolved_phrase
test_validator_warns_for_missing_design_view
test_validator_warns_for_design_view_without_mermaid_or_reason
test_validator_blocks_confirmed_design_missing_task_fields
test_validator_warns_for_behavior_detail_in_design_interface_definitions
test_validator_warns_for_unchanged_item_in_design_interface_definitions
test_design_contract_uses_technical_task_sections
test_design_diagram_labels_require_chinese_explanations
test_readme_describes_current_framework_loop
test_generate_specs_reads_technical_design_fields
test_validator_allows_decision_resolution_with_pending_revision_artifact
test_validator_resolve_decision_requires_target_issue_decision
test_sync_validator_copies_source
test_rebuild_context_repairs_pending_artifacts
test_rebuild_context_repairs_false_completion
test_rebuild_context_counts_issues_with_task_ids
test_rebuild_context_does_not_use_test_report_as_test_file
test_rebuild_context_uses_analysis_summary_and_preserves_constraints
test_render_review_dashboard_creates_root_html
test_validator_revisions_require_ordered_sections
test_validator_journal_requires_date_archive_order
test_validator_detects_ordered_artifact_drift
test_validator_rejects_legacy_test_report_structure
test_validator_accepts_new_test_report_structure_with_missing_scripts
test_validator_rejects_confirmed_blocking_test_report
test_validator_requires_output_subdirectories
test_wf_init_agent_template_uses_rendered_coding_rules

echo "runtime tool tests passed"
