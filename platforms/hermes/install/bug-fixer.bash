#!/usr/bin/env bash
# 安装 bug-fixer 到 Hermes skills
# 从 skills/bug-fixer/SKILL.md 直接复制，不做修改

set -euo pipefail

SKILLS_DIR="$(cd "$(dirname "$0")/../../../skills" && pwd)"
SKILL_FILE="${SKILLS_DIR}/bug-fixer/SKILL.md"
DST_DIR="${HOME}/.hermes/skills/bug-fixer"

[ -f "$SKILL_FILE" ] || { echo "    ❌ 找不到 SKILL: $SKILL_FILE"; exit 1; }

mkdir -p "$DST_DIR"
cp "$SKILL_FILE" "$DST_DIR/SKILL.md"

echo "    ✅ bug-fixer"
