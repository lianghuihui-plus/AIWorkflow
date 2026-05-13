#!/usr/bin/env bash
set -euo pipefail
SKILLS_DIR="$(cd "$(dirname "$0")/../../../skills" && pwd)"
SKILL_FILE="${SKILLS_DIR}/workflow-status/SKILL.md"
GLOBAL_COMMANDS="${HOME}/.cursor/commands"
if [ ! -f "$SKILL_FILE" ]; then echo "    ❌ 找不到 SKILL: $SKILL_FILE"; exit 1; fi
mkdir -p "$GLOBAL_COMMANDS"
skill_name=$(awk '/^---$/{n++; next} n==1 && /^name:/{sub(/^name: */,""); print; exit}' "$SKILL_FILE")
description=$(awk '/^---$/{n++; next} n==1 && /^description:/{sub(/^description: *"?/,""); sub(/"?"/,""); print; exit}' "$SKILL_FILE")
body=$(awk 'BEGIN{n=0} /^---$/{n++; next} n>=2{print}' "$SKILL_FILE")
cat > "${GLOBAL_COMMANDS}/${skill_name}.md" << EOFF
# /${skill_name} Command

${description}

${body}
EOFF
echo "    ✅ /${skill_name}"
