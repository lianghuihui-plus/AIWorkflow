#!/usr/bin/env bash
# 安装 wf-spec-generator 到 OpenClaw workspace skills
set -euo pipefail
SKILLS_DIR="$(cd "$(dirname "$0")/../../../skills" && pwd)"
SKILL_FILE="${SKILLS_DIR}/wf-spec-generator/SKILL.md"
DST_DIR="${HOME}/.openclaw/skills/wf-spec-generator"
[ -f "$SKILL_FILE" ] || { echo "    ❌ 找不到 SKILL: $SKILL_FILE"; exit 1; }
name=$(awk '/^---$/{n++; next} n==1 && /^name:/{sub(/^name: */,""); print; exit}' "$SKILL_FILE")
desc=$(awk '/^---$/{n++; next} n==1 && /^description:/{sub(/^description: *"?/,""); sub(/"?$/,""); print; exit}' "$SKILL_FILE")
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
