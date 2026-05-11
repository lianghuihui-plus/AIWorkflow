#!/usr/bin/env bash
# 安装 dev-profile 到 OpenClaw skills
# 从 skills/dev-profile/SKILL.md 直接复制，不做修改

set -euo pipefail

SKILLS_DIR="$(cd "$(dirname "$0")/../../../skills" && pwd)"
SKILL_FILE="${SKILLS_DIR}/dev-profile/SKILL.md"
DST_DIR="${HOME}/.openclaw/skills/dev-profile"

[ -f "$SKILL_FILE" ] || { echo "    ❌ 找不到 SKILL: $SKILL_FILE"; exit 1; }

mkdir -p "$DST_DIR"
cp "$SKILL_FILE" "$DST_DIR/SKILL.md"

echo "    ✅ dev-profile"
