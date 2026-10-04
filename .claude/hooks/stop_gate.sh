#!/usr/bin/env bash
# Stop hook: before Claude ends a turn in which Python changed, run the repo-wide
# structure checks. On failure, exit 2 sends the problems back and Claude keeps
# working. Only blocks once per stop (stop_hook_active) to avoid loops.
set -uo pipefail
input=$(cat)
active=$(printf '%s' "$input" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("stop_hook_active", False))' 2>/dev/null)
[ "$active" = "True" ] && exit 0
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
# Only when Python files changed (staged, unstaged or untracked).
changed=$( { git diff --name-only HEAD 2>/dev/null; git ls-files --others --exclude-standard; } | grep -E '\.py$' || true)
[ -z "$changed" ] && exit 0

out=""
r=$(uv run --quiet python tools/check_structure.py 2>&1) || out+="structure:\n$r\n"
r=$(uv run --quiet lint-imports --no-cache 2>&1) || out+="import boundaries (higher layers may import lower, never the reverse):\n$(printf '%s' "$r" | sed -n '/^Broken contracts/,$p;/^Missing layer/p;/error/Ip' | head -25)\n"
r=$(uv run --quiet pylint --disable=all --enable=duplicate-code src 2>&1) || out+="duplicate code:\n$(printf '%s' "$r" | head -30)\n"
if [ -n "$out" ]; then
  printf "Before finishing, fix these (AGENTS.md → Architecture & reuse). Refactor, don't silence:\n%b" "$out" >&2
  exit 2
fi
exit 0
