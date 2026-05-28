#!/usr/bin/env bash
set -euo pipefail
SKILLS_DIR="$(cd "$(dirname "$0")/../../../skills" && pwd)"
SKILL_FILE="${SKILLS_DIR}/wf-test-generator/SKILL.md"
DST_DIR="${HOME}/.claude/skills/wf-test-generator"
[ -f "$SKILL_FILE" ] || { echo "    ❌ 找不到 SKILL: $SKILL_FILE"; exit 1; }
mkdir -p "$DST_DIR"
cp "$SKILL_FILE" "$DST_DIR/SKILL.md"
echo "    ✅ wf-test-generator"
