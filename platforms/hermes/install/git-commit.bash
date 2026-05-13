#!/usr/bin/env bash
# 安装 git-commit 到 Hermes skills
# 从 skills/git-commit/SKILL.md 直接复制，不做修改

set -euo pipefail

SKILLS_DIR="$(cd "$(dirname "$0")/../../../skills" && pwd)"
SKILL_FILE="${SKILLS_DIR}/git-commit/SKILL.md"
DST_DIR="${HOME}/.hermes/skills/git-commit"

[ -f "$SKILL_FILE" ] || { echo "    ❌ 找不到 SKILL: $SKILL_FILE"; exit 1; }

mkdir -p "$DST_DIR"
cp "$SKILL_FILE" "$DST_DIR/SKILL.md"

echo "    ✅ git-commit"
