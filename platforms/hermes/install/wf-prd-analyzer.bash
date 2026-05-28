#!/usr/bin/env bash
set -euo pipefail
SKILLS_DIR="$(cd "$(dirname "$0")/../../../skills" && pwd)"
SKILL_FILE="${SKILLS_DIR}/wf-prd-analyzer/SKILL.md"
DST_DIR="${HOME}/.hermes/skills/wf-prd-analyzer"
[ -f "$SKILL_FILE" ] || { echo "    ❌ 找不到 SKILL: $SKILL_FILE"; exit 1; }
mkdir -p "$DST_DIR"
cp "$SKILL_FILE" "$DST_DIR/SKILL.md"
echo "    ✅ wf-prd-analyzer"
