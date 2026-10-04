#!/usr/bin/env bash
# One command to see the site with fresh papers: syncs, builds and opens the browser.
set -euo pipefail
cd "$(dirname "$0")"
exec uv run sitegen preview "$@"
