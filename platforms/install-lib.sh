#!/usr/bin/env bash
# AIWorkFlow 平台安装公共库
# 用法: source platforms/install-lib.sh; aiwf_install_platform "<平台名>"
set -euo pipefail

aiwf_skill_name() {
  awk '/^---$/{n++; next} n==1 && /^name:/{sub(/^name: */,""); print; exit}' "$1"
}

aiwf_skill_description() {
  awk '/^---$/{n++; next} n==1 && /^description:/{sub(/^description: *"?/,""); sub(/"?$/,""); print; exit}' "$1"
}

aiwf_skill_body() {
  awk 'BEGIN{n=0} /^---$/{n++; next} n>=2{print}' "$1"
}

aiwf_install_copy_skill() {
  local platform="$1"
  local skill_file="$2"
  local name="$3"
  local dst_dir="${HOME}/.${platform}/skills/${name}"

  mkdir -p "$dst_dir"
  cp "$skill_file" "$dst_dir/SKILL.md"
}

aiwf_install_cursor_skill() {
  local skill_file="$1"
  local name="$2"
  local description
  local commands_dir="${HOME}/.cursor/commands"

  description="$(aiwf_skill_description "$skill_file")"
  mkdir -p "$commands_dir"
  {
    printf '# /%s Command\n\n' "$name"
    printf '%s\n\n' "$description"
    aiwf_skill_body "$skill_file"
  } > "${commands_dir}/${name}.md"
}

aiwf_install_openclaw_skill() {
  local skill_file="$1"
  local name="$2"
  local description
  local dst_dir="${HOME}/.openclaw/skills/${name}"

  description="$(aiwf_skill_description "$skill_file")"
  mkdir -p "$dst_dir"
  {
    printf -- '---\n'
    printf 'name: %s\n' "$name"
    printf 'description: %s\n' "$description"
    printf 'user-invocable: true\n'
    printf 'disable-model-invocation: true\n'
    printf -- '---\n'
    aiwf_skill_body "$skill_file"
  } > "$dst_dir/SKILL.md"
}

aiwf_install_skill() {
  local platform="$1"
  local skill_file="$2"
  local name="$3"

  case "$platform" in
    claude|hermes)
      aiwf_install_copy_skill "$platform" "$skill_file" "$name"
      ;;
    cursor)
      aiwf_install_cursor_skill "$skill_file" "$name"
      ;;
    openclaw)
      aiwf_install_openclaw_skill "$skill_file" "$name"
      ;;
    *)
      echo "❌ 未支持的平台: ${platform}" >&2
      return 1
      ;;
  esac
}

aiwf_install_platform() {
  local platform="$1"
  local lib_dir
  local root_dir
  local skills_dir

  lib_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  root_dir="$(cd "${lib_dir}/.." && pwd)"
  skills_dir="${root_dir}/skills"

  if [ ! -d "$skills_dir" ]; then
    echo "❌ skills 目录不存在: ${skills_dir}"
    return 1
  fi

  echo "🔌 安装 AIWorkFlow skills 到 ${platform}..."
  echo ""

  local count=0
  local skill_dir skill_file name
  for skill_dir in "$skills_dir"/*; do
    [ -d "$skill_dir" ] || continue
    skill_file="${skill_dir}/SKILL.md"
    [ -f "$skill_file" ] || continue
    name="$(aiwf_skill_name "$skill_file")"
    if [ -z "$name" ]; then
      echo "    ❌ 缺少 skill name: ${skill_file}" >&2
      return 1
    fi
    echo "  ▶ ${name}"
    aiwf_install_skill "$platform" "$skill_file" "$name"
    echo "    ✅ ${name}"
    count=$((count + 1))
  done

  echo ""
  echo "✅ ${platform} skills 已安装 ${count} 条"
}
