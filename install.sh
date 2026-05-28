#!/usr/bin/env bash
# AIWorkFlow V2 统一安装入口
# 用法: ./workspace-install.sh [平台名]   不传则安装所有平台

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLATFORMS_DIR="${SCRIPT_DIR}/platforms"
SELECTED="${1:-all}"

V2_SKILLS=("wf-init" "wf-status" "wf-prd-analyzer" "wf-tech-designer" "wf-spec-generator" "wf-code-generator" "wf-test-generator" "wf-git-commit")

if [ "$SELECTED" = "all" ]; then
  echo "📦 安装 AIWorkFlow V2 到所有平台..."
  echo ""
  for platform_dir in "$PLATFORMS_DIR"/*/; do
    [ -d "$platform_dir" ] || continue
    platform="$(basename "$platform_dir")"
    install_script="${platform_dir}install-workspace.sh"
    if [ -f "$install_script" ]; then
      echo "▶ ${platform}:"
      bash "$install_script"
      echo ""
    fi
  done
else
  platform_dir="${PLATFORMS_DIR}/${SELECTED}"
  install_script="${platform_dir}/install-workspace.sh"

  if [ ! -d "$platform_dir" ]; then
    echo "❌ 未知平台: ${SELECTED}"
    echo "可用平台: $(ls "$PLATFORMS_DIR")"
    exit 1
  fi

  if [ ! -f "$install_script" ]; then
    echo "❌ ${SELECTED} 平台尚未配置 V2 安装脚本"
    exit 1
  fi

  echo "▶ ${SELECTED}:"
  bash "$install_script"
fi
