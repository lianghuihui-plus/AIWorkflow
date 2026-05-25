#!/usr/bin/env bash
# 安装 prd-analyzer 到 Claude Code skills
# 从 skills/prd-analyzer/SKILL.md 直接复制，不做修改

set -euo pipefail

SKILLS_DIR="$(cd "$(dirname "$0")/../../../skills" && pwd)"
SKILL_FILE="${SKILLS_DIR}/prd-analyzer/SKILL.md"
DST_DIR="${HOME}/.claude/skills/prd-analyzer"

[ -f "$SKILL_FILE" ] || { echo "    ❌ 找不到 SKILL: $SKILL_FILE"; exit 1; }

mkdir -p "$DST_DIR"
cp "$SKILL_FILE" "$DST_DIR/SKILL.md"

echo "    ✅ prd-analyzer"
