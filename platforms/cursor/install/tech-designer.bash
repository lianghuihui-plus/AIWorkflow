#!/usr/bin/env bash
# 注册 tech-designer 命令到 Cursor 全局命令目录
# 从 skills/tech-designer/SKILL.md 即时生成 .md 命令文件

set -euo pipefail

SKILLS_DIR="$(cd "$(dirname "$0")/../../../skills" && pwd)"
SKILL_FILE="${SKILLS_DIR}/tech-designer/SKILL.md"
GLOBAL_COMMANDS="${HOME}/.cursor/commands"

if [ ! -f "$SKILL_FILE" ]; then
  echo "    ❌ 找不到 SKILL: $SKILL_FILE"
  exit 1
fi

mkdir -p "$GLOBAL_COMMANDS"

# 提取 name
skill_name=$(awk '/^---$/{n++; next} n==1 && /^name:/{sub(/^name: */,""); print; exit}' "$SKILL_FILE")

# 提取 description
description=$(awk '/^---$/{n++; next} n==1 && /^description:/{sub(/^description: *"?/,""); sub(/"?$/,""); print; exit}' "$SKILL_FILE")

# 提取 body（跳过 frontmatter）
body=$(awk 'BEGIN{n=0} /^---$/{n++; next} n>=2{print}' "$SKILL_FILE")

# 即时生成 .md 命令文件
cat > "${GLOBAL_COMMANDS}/${skill_name}.md" << EOF
# /${skill_name} Command

${description}

${body}
EOF

echo "    ✅ /${skill_name}"
