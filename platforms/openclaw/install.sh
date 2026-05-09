#!/usr/bin/env bash
# OpenClaw 平台 - 安装所有 AIWorkFlow skills
# 用法: ./install.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="${SCRIPT_DIR}/install"

echo "🔌 安装 AIWorkFlow skills 到 OpenClaw..."
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
echo "✅ OpenClaw skills 已安装 ${count} 条"
echo "   新开一个会话即可使用 /command 调用"
