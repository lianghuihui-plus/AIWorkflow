#!/usr/bin/env bash
# Claude Code 平台 - 安装所有 AIWorkFlow skills
# 用法: ./install.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="${SCRIPT_DIR}/install"

echo "🔌 安装 AIWorkFlow skills 到 Claude Code..."
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
echo "✅ Claude Code skills 已安装 ${count} 条"
echo "   在 Claude Code 中输入自然语言即可自动匹配调用 skill"
