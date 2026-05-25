#!/usr/bin/env bash
# 安装 workflow-session 到 OpenClaw workspace skills
# 从 skills/workflow-session/SKILL.md 读取，添加 OpenClaw frontmatter 后写入

set -euo pipefail

SKILLS_DIR="$(cd "$(dirname "$0")/../../../skills" && pwd)"
SKILL_FILE="${SKILLS_DIR}/workflow-session/SKILL.md"
DST_DIR="${HOME}/.openclaw/skills/workflow-session"

[ -f "$SKILL_FILE" ] || { echo "    ❌ 找不到 SKILL: $SKILL_FILE"; exit 1; }

AGENT_FILE="${SKILLS_DIR}/workflow-session/AGENT.md"
[ -f "$AGENT_FILE" ] || { echo "    ❌ 找不到 AGENT: $AGENT_FILE"; exit 1; }

# 提取原 frontmatter 字段
name=$(awk '/^---$/{n++; next} n==1 && /^name:/{sub(/^name: */,""); print; exit}' "$SKILL_FILE")
desc=$(awk '/^---$/{n++; next} n==1 && /^description:/{sub(/^description: *"?/,""); sub(/"?$/,""); print; exit}' "$SKILL_FILE")
body=$(awk 'BEGIN{n=0} /^---$/{n++; next} n>=2{print}' "$SKILL_FILE")

mkdir -p "$DST_DIR"
cp "$AGENT_FILE" "$DST_DIR/AGENT.md"

cat > "$DST_DIR/SKILL.md" << SKILLEOF
---
name: $name
description: $desc
user-invocable: true
---

$body
SKILLEOF

echo "    ✅ /$name"
