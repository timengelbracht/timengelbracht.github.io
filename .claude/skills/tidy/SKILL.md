---
name: tidy
description: Find and fix structural rot — oversized files and functions, duplicated code, dead code, stale ARCHITECTURE.md. Use when Tim says "tidy", "clean up the code", "refactor", before a paper release, or every couple of weeks on an active repo.
---

# Tidy

1. Run and collect:
   - `uv run python tools/check_structure.py`
   - `uv run pylint --disable=all --enable=duplicate-code src`
   - `uv run ruff check . --select C90,PLR0912,PLR0915`
   - `uv run ruff check . --select F401,F841` (unused imports/variables)
   - modules not listed in `docs/ARCHITECTURE.md`;
     files named `*_v2`, `*_new`, `*_old`, `*_final`, `utils2`.
2. Report a prioritised list (max 10 items): what, where, proposed fix.
3. After Tim picks items, refactor **one item at a time**, behaviour-preserving:
   tests green before and after each step; no new features mixed in.
4. Update `docs/ARCHITECTURE.md`, then summarise what moved where.
