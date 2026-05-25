#!/usr/bin/env bash
# 安装 bug-new 到 Claude Code skills
# 从 skills/bug-new/SKILL.md 直接复制，不做修改

set -euo pipefail

SKILLS_DIR="$(cd "$(dirname "$0")/../../../skills" && pwd)"
SKILL_FILE="${SKILLS_DIR}/bug-new/SKILL.md"
DST_DIR="${HOME}/.claude/skills/bug-new"

[ -f "$SKILL_FILE" ] || { echo "    ❌ 找不到 SKILL: $SKILL_FILE"; exit 1; }

mkdir -p "$DST_DIR"
cp "$SKILL_FILE" "$DST_DIR/SKILL.md"

echo "    ✅ bug-new"
