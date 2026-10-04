#!/usr/bin/env bash
# PostToolUse hook: after every Python edit by Claude, format + lint the file and
# check size limits. Problems are sent back to Claude (exit 2) so it fixes them now,
# instead of letting a monolith or duplicate grow.
set -uo pipefail

file=$(python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("tool_input",{}).get("file_path",""))')
[[ "$file" == *.py ]] || exit 0
[[ -f "$file" ]] || exit 0

cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
uv run --quiet ruff format "$file" >/dev/null 2>&1
problems=""
if ! out=$(uv run --quiet ruff check --fix "$file" 2>&1); then
  problems+="ruff:\n$out\n"
fi
if ! out=$(uv run --quiet python tools/check_structure.py "$file" 2>&1); then
  problems+="structure:\n$out\n"
fi
# Duplicates are checked repo-wide but only reported if they involve this file.
rel="${file#"$PWD"/}"
mod="${rel#src/}"; mod="${mod%.py}"; mod="${mod//\//.}"   # pylint reports module names
dup=$(uv run --quiet pylint --disable=all --enable=duplicate-code src 2>/dev/null \
      | awk -v m="==$mod:" '/R0801/{blk=$0; keep=0; next} index($0,m)==1{keep=1} {if(blk!=""){blk=blk"\n"$0}} /^$/{if(keep)print blk; blk=""; keep=0} END{if(keep)print blk}' || true)
if [ -n "$dup" ]; then
  problems+="duplicate code involving $rel (extract a shared function instead):\n$dup\n"
fi
if [ -n "$problems" ]; then
  printf "Fix these in %s before continuing (see AGENTS.md → Architecture & reuse):\n%b" "$rel" "$problems" >&2
  exit 2
fi
exit 0
