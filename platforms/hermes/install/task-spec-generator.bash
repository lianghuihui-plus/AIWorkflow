#!/usr/bin/env bash
# 安装 task-spec-generator 到 Hermes skills
# 从 skills/task-spec-generator/SKILL.md 直接复制，不做修改

set -euo pipefail

SKILLS_DIR="$(cd "$(dirname "$0")/../../../skills" && pwd)"
SKILL_FILE="${SKILLS_DIR}/task-spec-generator/SKILL.md"
DST_DIR="${HOME}/.hermes/skills/task-spec-generator"

[ -f "$SKILL_FILE" ] || { echo "    ❌ 找不到 SKILL: $SKILL_FILE"; exit 1; }

mkdir -p "$DST_DIR"
cp "$SKILL_FILE" "$DST_DIR/SKILL.md"

echo "    ✅ task-spec-generator"
