#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

EXCLUDED_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "node_modules",
    "dist",
    "build",
}

TEXT_SUFFIXES = {
    ".py",
    ".sh",
    ".zsh",
    ".md",
    ".txt",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".ini",
    ".js",
    ".ts",
}

EXCLUDED_FILENAMES = {
    "identifier_inventory.json",
    "rename_plan.json",
    "naming_refactor_report.md",
}

SLUG_LITERAL_RE = re.compile(
    r"\"((?:batch_)?slug|noun_slug)\"\\s*:\\s*\"([^\"]+)\""
    r"|\\b((?:batch_)?slug|noun_slug)\\s*:\\s*([a-zA-Z0-9][a-zA-Z0-9_-]*)"
)
KEBAB_CASE_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def iter_text_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue
        if path.name in EXCLUDED_FILENAMES:
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        files.append(path)
    return files


def find_violations(root: Path) -> list[str]:
    violations: list[str] = []

    for path in iter_text_files(root):
        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            continue

        if path.suffix.lower() not in {".json", ".yaml", ".yml", ".md"}:
            continue

        for line_no, line in enumerate(content.splitlines(), start=1):
            for found in SLUG_LITERAL_RE.finditer(line):
                value = (found.group(2) or found.group(4) or "").strip().strip("\"'")
                if value and not KEBAB_CASE_RE.fullmatch(value):
                    violations.append(
                        f"{path}:{line_no}: slug value must be kebab-case: {value!r}"
                    )
    return violations


def check(root: str = ".") -> int:
    target_root = Path(root).expanduser().resolve()
    violations = find_violations(target_root)

    if violations:
        print("Naming policy violations found:", file=sys.stderr)
        for line in violations:
            print(f"- {line}", file=sys.stderr)
        return 1

    print("Naming policy checks passed.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check slug naming conventions.")
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root to scan (default: current working directory).",
    )
    args = parser.parse_args(argv)
    return check(args.root)


if __name__ == "__main__":
    raise SystemExit(main())
