#!/usr/bin/env bash
# One command to see the site with fresh papers: sets up .venv, syncs, builds, opens the browser.
set -euo pipefail
cd "$(dirname "$0")"
[ -x .venv/bin/sitegen ] || { python3 -m venv .venv && .venv/bin/pip install -q --upgrade pip && .venv/bin/pip install -q -e ".[dev]"; }
exec .venv/bin/sitegen preview "$@"
