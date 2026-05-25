#!/usr/bin/env bash
# 安装 code-generator 到 Claude Code skills
# 从 skills/code-generator/SKILL.md 直接复制，不做修改

set -euo pipefail

SKILLS_DIR="$(cd "$(dirname "$0")/../../../skills" && pwd)"
SKILL_FILE="${SKILLS_DIR}/code-generator/SKILL.md"
DST_DIR="${HOME}/.claude/skills/code-generator"

[ -f "$SKILL_FILE" ] || { echo "    ❌ 找不到 SKILL: $SKILL_FILE"; exit 1; }

mkdir -p "$DST_DIR"
cp "$SKILL_FILE" "$DST_DIR/SKILL.md"

echo "    ✅ code-generator"
