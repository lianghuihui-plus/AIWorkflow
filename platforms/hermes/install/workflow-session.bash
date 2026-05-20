#!/usr/bin/env bash
# 安装 workflow-session 到 Hermes skills
# 从 skills/workflow-session/SKILL.md 直接复制

set -euo pipefail

SKILLS_DIR="$(cd "$(dirname "$0")/../../../skills" && pwd)"
SKILL_FILE="${SKILLS_DIR}/workflow-session/SKILL.md"
DST_DIR="${HOME}/.hermes/skills/workflow-session"

[ -f "$SKILL_FILE" ] || { echo "    ❌ 找不到 SKILL: $SKILL_FILE"; exit 1; }

mkdir -p "$DST_DIR"
cp "$SKILL_FILE" "$DST_DIR/SKILL.md"

echo "    ✅ workflow-session"
