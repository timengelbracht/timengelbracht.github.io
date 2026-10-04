#!/usr/bin/env python3
"""Structure guard: keep files and functions small so code stays modular.

Limits come from [tool.structure] in pyproject.toml. Used by pre-commit, CI and
the Claude Code edit hook. Exit 1 if any limit is exceeded.

    python tools/check_structure.py                 # check src/ scripts/ tests/
    python tools/check_structure.py path/to/file.py # check specific files
"""

from __future__ import annotations

import ast
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULTS = {"max_file_lines": 400, "max_function_lines": 60, "paths": ["src", "scripts", "tests"]}


def load_cfg() -> dict:
    """Read [tool.structure] limits from pyproject.toml."""
    cfg = dict(DEFAULTS)
    pp = ROOT / "pyproject.toml"
    if pp.exists():
        cfg |= tomllib.loads(pp.read_text()).get("tool", {}).get("structure", {})
    return cfg


def check_file(path: Path, cfg: dict) -> list[str]:
    """Return limit violations for one file."""
    text = path.read_text(encoding="utf-8")
    rel = path.resolve().relative_to(ROOT) if path.resolve().is_relative_to(ROOT) else path
    problems = []
    n = len([ln for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")])
    if n > cfg["max_file_lines"]:
        problems.append(
            f"{rel}: {n} code lines > {cfg['max_file_lines']} — split it into focused modules "
            f"(see docs/ARCHITECTURE.md for where things belong)"
        )
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return problems
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            length = (node.end_lineno or node.lineno) - node.lineno + 1
            if length > cfg["max_function_lines"]:
                problems.append(
                    f"{rel}:{node.lineno}: function `{node.name}` is {length} lines > "
                    f"{cfg['max_function_lines']} — extract helpers"
                )
    return problems


def main(argv: list[str]) -> int:
    """Check the given files/dirs (default: configured paths)."""
    cfg = load_cfg()
    targets = [Path(a) for a in argv] or [ROOT / p for p in cfg["paths"]]
    files = []
    for t in targets:
        if t.is_dir():
            files += sorted(t.rglob("*.py"))
        elif t.suffix == ".py" and t.exists():
            files.append(t)
    problems = [p for f in files for p in check_file(f, cfg)]
    for p in problems:
        print(p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
