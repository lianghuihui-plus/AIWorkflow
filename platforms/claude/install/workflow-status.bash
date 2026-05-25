#!/usr/bin/env bash
# 安装 workflow-status 到 Claude Code skills
# 从 skills/workflow-status/SKILL.md 直接复制，不做修改

set -euo pipefail

SKILLS_DIR="$(cd "$(dirname "$0")/../../../skills" && pwd)"
SKILL_FILE="${SKILLS_DIR}/workflow-status/SKILL.md"
DST_DIR="${HOME}/.claude/skills/workflow-status"

[ -f "$SKILL_FILE" ] || { echo "    ❌ 找不到 SKILL: $SKILL_FILE"; exit 1; }

mkdir -p "$DST_DIR"
cp "$SKILL_FILE" "$DST_DIR/SKILL.md"

echo "    ✅ workflow-status"
