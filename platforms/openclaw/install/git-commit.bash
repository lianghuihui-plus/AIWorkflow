#!/usr/bin/env bash
# 安装 git-commit 到 OpenClaw workspace skills
# 从 skills/git-commit/SKILL.md 读取，添加 OpenClaw frontmatter 后写入

set -euo pipefail

SKILLS_DIR="$(cd "$(dirname "$0")/../../../skills" && pwd)"
SKILL_FILE="${SKILLS_DIR}/git-commit/SKILL.md"
DST_DIR="${HOME}/.openclaw/skills/git-commit"

[ -f "$SKILL_FILE" ] || { echo "    ❌ 找不到 SKILL: $SKILL_FILE"; exit 1; }

name=$(awk '/^---$/{n++; next} n==1 && /^name:/{sub(/^name: */,""); print; exit}' "$SKILL_FILE")
desc=$(awk '/^---$/{n++; next} n==1 && /^description:/{sub(/^description: *"?/,""); sub(/"?"/,""); print; exit}' "$SKILL_FILE")
body=$(awk 'BEGIN{n=0} /^---$/{n++; next} n>=2{print}' "$SKILL_FILE")

mkdir -p "$DST_DIR"

cat > "$DST_DIR/SKILL.md" << SKILLEOF
---
name: $name
description: $desc
user-invocable: true
disable-model-invocation: true
---

$body
SKILLEOF

echo "    ✅ /$name"
