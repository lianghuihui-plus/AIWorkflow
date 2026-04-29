#!/usr/bin/env bash
# Cursor 平台 - 安装所有命令
# 用法: ./install.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="${SCRIPT_DIR}/install"

count=0
for script in "$INSTALL_DIR"/*.bash; do
  [ -f "$script" ] || continue
  name="$(basename "$script" .bash)"
  echo "  ▶ ${name}"
  bash "$script"
  count=$((count + 1))
done

echo ""
echo "✅ Cursor 命令已安装 ${count} 条"
