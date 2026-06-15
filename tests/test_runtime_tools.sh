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
EOF
  write_review_status "$ws/output/specs/T-001.md" "已确认"
  write_review_status "$ws/output/reports/T-001.md" "已确认"
  write_review_status "$ws/output/test-reports/T-001.md" "已确认"

  python3 "$ROOT_DIR/wf/tools/rebuild_context.py" "$ws"
  if grep -q "| T-001 | output/test-reports/T-001.md | ✅ 已完成 |" "$ws/CONTEXT.md"; then
    fail "test report path must not be used as test file path"
  fi
  grep -q "| T-001 | — | ✅ 已完成 |" "$ws/CONTEXT.md" || fail "expected unknown test file placeholder"
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
# 测试报告 — T-001 first

## 审核状态

- 状态：待审核
- 审核人：
- 审核时间：
- 修订来源：

## 测试清单

| # | 测试用例 | 覆盖行为 | 文件 | 状态 |
|---|---|---|---|---|
| 2 | second | demo | `b.test.ts` | ✅ |
| 1 | first | demo | `a.test.ts` | ✅ |

## 未覆盖行为

无

- edge — reason
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
  echo "$out" | grep -q "test_report_case_order_invalid" || fail "expected test report case order warning"
  echo "$out" | grep -q "test_report_uncovered_none_with_entries" || fail "expected test report uncovered none-with-entries failure"
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
test_validator_implement_requires_design_tasks
test_validator_generate_specs_requires_design_tasks
test_validator_duplicate_ids_are_failures
test_validator_allows_decision_resolution_with_pending_revision_artifact
test_validator_resolve_decision_requires_target_issue_decision
test_sync_validator_copies_source
test_rebuild_context_repairs_pending_artifacts
test_rebuild_context_repairs_false_completion
test_rebuild_context_counts_issues_with_task_ids
test_rebuild_context_does_not_use_test_report_as_test_file
test_rebuild_context_uses_analysis_summary_and_preserves_constraints
test_validator_revisions_require_ordered_sections
test_validator_journal_requires_date_archive_order
test_validator_detects_ordered_artifact_drift
test_validator_requires_output_subdirectories
test_wf_init_agent_template_uses_rendered_coding_rules

echo "runtime tool tests passed"
