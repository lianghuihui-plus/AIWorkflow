#!/usr/bin/env bash
# openclaw 平台 - 安装所有 AIWorkFlow V2 skills
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="${SCRIPT_DIR}/install"
echo "🔌 安装 AIWorkFlow V2 skills 到 openclaw..."
echo ""
count=0
for script in "$INSTALL_DIR"/*.bash; do
  [ -f "$script" ] || continue
  name="$(basename "$script" .bash)"
  echo "  ▶ ${name}"
  bash "$script"
  count=$((count + 1))
done
echo ""
echo "✅ openclaw V2 skills 已安装 ${count} 条"
