#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TMP_HOME="$(mktemp -d)"
trap 'rm -rf "$TMP_HOME"' EXIT

run_install() {
  local platform="$1"
  HOME="$TMP_HOME" bash "$ROOT_DIR/install.sh" "$platform" >/tmp/aiworkflow-install-${platform}.log
}

assert_file() {
  local file="$1"
  if [ ! -f "$file" ]; then
    echo "missing file: $file" >&2
    exit 1
  fi
}

assert_contains() {
  local file="$1"
  local text="$2"
  if ! grep -Fq "$text" "$file"; then
    echo "expected '$text' in $file" >&2
    exit 1
  fi
}

for platform in claude cursor hermes openclaw; do
  install_dir="$ROOT_DIR/platforms/$platform/install"
  if [ -d "$install_dir" ] && find "$install_dir" -type f -name '*.bash' | grep -q .; then
    echo "platform $platform still has per-skill install scripts" >&2
    exit 1
  fi

  run_install "$platform"
done

for skill_dir in "$ROOT_DIR"/skills/*; do
  [ -d "$skill_dir" ] || continue
  skill="$(basename "$skill_dir")"

  assert_file "$TMP_HOME/.claude/skills/$skill/SKILL.md"
  assert_contains "$TMP_HOME/.claude/skills/$skill/SKILL.md" "name: $skill"

  assert_file "$TMP_HOME/.hermes/skills/$skill/SKILL.md"
  assert_contains "$TMP_HOME/.hermes/skills/$skill/SKILL.md" "name: $skill"

  assert_file "$TMP_HOME/.openclaw/skills/$skill/SKILL.md"
  assert_contains "$TMP_HOME/.openclaw/skills/$skill/SKILL.md" "name: $skill"
  assert_contains "$TMP_HOME/.openclaw/skills/$skill/SKILL.md" "user-invocable: true"
  assert_contains "$TMP_HOME/.openclaw/skills/$skill/SKILL.md" "disable-model-invocation: true"

  assert_file "$TMP_HOME/.cursor/commands/$skill.md"
  assert_contains "$TMP_HOME/.cursor/commands/$skill.md" "# /$skill Command"
done

echo "install smoke test passed"
