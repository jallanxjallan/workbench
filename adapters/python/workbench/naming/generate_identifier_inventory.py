#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - optional
    yaml = None

EXCLUDED_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "node_modules",
    "dist",
    "build",
    ".venv",
    "venv",
    "v2.egg-info",
    "AutoScribe.egg-info",
    "_depreciated",
    "obsidian",
    "pandoc",
}

TEXT_SUFFIXES = {
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".sh",
    ".zsh",
    ".md",
    ".txt",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".ini",
}

EXCLUDED_FILENAMES = {
    "identifier_inventory.json",
    "rename_plan.json",
    "naming_refactor_report.md",
}

SCRIPT_CASE = {
    ".py": "snake_case",
    ".js": "kebab-case",
    ".ts": "kebab-case",
    ".tsx": "kebab-case",
    ".jsx": "kebab-case",
    ".sh": "kebab-case",
    ".zsh": "kebab-case",
    ".md": "kebab-case",
    ".yaml": "kebab-case",
    ".yml": "kebab-case",
    ".json": "kebab-case",
    ".toml": "kebab-case",
}

UPPER_ENV_RE = re.compile(r"\b[A-Z][A-Z0-9]+(?:_[A-Z0-9]+)+\b")
JS_IDENT_RE = re.compile(
    r"(?P<class>\bclass\s+([A-Za-z_][A-Za-z0-9_]*))|"
    r"(?P<fn>\bfunction\s+([A-Za-z_][A-Za-z0-9_]*))|"
    r"(?P<var>\b(?:const|let|var)\s+([A-Za-z_][A-Za-z0-9_]*))"
)
IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_\-]*$")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def detect_case(value: str) -> str:
    if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)+", value):
        return "kebab-case"
    if re.fullmatch(r"[a-z]+(?:_[a-z0-9]+)+", value):
        return "snake_case"
    if re.fullmatch(r"[a-z]+(?:[A-Z][a-z0-9]*)+", value):
        return "camelCase"
    if re.fullmatch(r"[A-Z][A-Za-z0-9]*", value) and not value.isupper():
        return "PascalCase"
    if re.fullmatch(r"[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+", value):
        return "SCREAMING_SNAKE_CASE"
    if re.fullmatch(r"[a-z0-9]+", value):
        return "lower"
    if re.fullmatch(r"[A-Z0-9]+", value):
        return "UPPER"
    return "mixed"


def split_words(value: str) -> list[str]:
    if not value:
        return []
    parts = re.split(r"[-_\s./:]+", value)
    words: list[str] = []
    for part in parts:
        if not part:
            continue
        tokens = re.findall(r"[A-Z]?[a-z0-9]+|[A-Z]+(?![a-z])", part)
        if not tokens:
            tokens = [part]
        for token in tokens:
            cleaned = re.sub(r"[^A-Za-z0-9]", "", token)
            if cleaned:
                words.append(cleaned.lower())
    return words


def to_case(value: str, target: str) -> str:
    words = split_words(value)
    if not words:
        return value
    if target == "kebab-case":
        return "-".join(words)
    if target == "snake_case":
        return "_".join(words)
    if target == "camelCase":
        head, *tail = words
        return head + "".join(word.capitalize() for word in tail)
    if target == "PascalCase":
        return "".join(word.capitalize() for word in words)
    if target == "SCREAMING_SNAKE_CASE":
        return "_".join(words).upper()
    return value


def add_entry(
    entries: list[dict[str, str]],
    *,
    identifier: str,
    file_path: Path,
    context: str,
    recommended_case: str,
) -> None:
    if not identifier or not IDENT_RE.match(identifier):
        return
    entries.append(
        {
            "identifier": identifier,
            "file_path": str(file_path),
            "context": context,
            "current_case": detect_case(identifier),
            "recommended_case": recommended_case,
        }
    )


def iter_files(repo: Path) -> list[Path]:
    files: list[Path] = []
    for path in repo.rglob("*"):
        if not path.is_file():
            continue
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue
        if path.name in EXCLUDED_FILENAMES:
            continue
        files.append(path)
    return files


def scan_python(path: Path, entries: list[dict[str, str]]) -> None:
    try:
        source = path.read_text(encoding="utf-8")
    except Exception:
        return

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            add_entry(
                entries,
                identifier=node.name,
                file_path=path,
                context="python_function",
                recommended_case="snake_case",
            )
        elif isinstance(node, ast.ClassDef):
            add_entry(
                entries,
                identifier=node.name,
                file_path=path,
                context="python_class",
                recommended_case="PascalCase",
            )
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    recommended = (
                        "SCREAMING_SNAKE_CASE"
                        if target.id.isupper()
                        else "snake_case"
                    )
                    add_entry(
                        entries,
                        identifier=target.id,
                        file_path=path,
                        context="python_constant" if target.id.isupper() else "python_variable",
                        recommended_case=recommended,
                    )
        elif isinstance(node, ast.AnnAssign):
            target = node.target
            if isinstance(target, ast.Name):
                recommended = "SCREAMING_SNAKE_CASE" if target.id.isupper() else "snake_case"
                add_entry(
                    entries,
                    identifier=target.id,
                    file_path=path,
                    context="python_constant" if target.id.isupper() else "python_variable",
                    recommended_case=recommended,
                )


def scan_js(path: Path, entries: list[dict[str, str]]) -> None:
    try:
        source = path.read_text(encoding="utf-8")
    except Exception:
        return

    for match in JS_IDENT_RE.finditer(source):
        text = match.group(0)
        name = text.split()[-1]
        if "class" in text:
            ctx, rec = "js_class", "PascalCase"
        elif "function" in text:
            ctx, rec = "js_function", "camelCase"
        else:
            ctx = "js_variable"
            rec = "SCREAMING_SNAKE_CASE" if name.isupper() else "camelCase"
        add_entry(entries, identifier=name, file_path=path, context=ctx, recommended_case=rec)


def walk_mapping(value: Any, *, path: Path, entries: list[dict[str, str]], context: str) -> None:
    if isinstance(value, dict):
        for key, sub in value.items():
            if isinstance(key, str):
                add_entry(
                    entries,
                    identifier=key,
                    file_path=path,
                    context=context,
                    recommended_case="snake_case",
                )
                if "slug" in key and isinstance(sub, str):
                    add_entry(
                        entries,
                        identifier=sub,
                        file_path=path,
                        context="slug_value",
                        recommended_case="kebab-case",
                    )
            walk_mapping(sub, path=path, entries=entries, context=context)
    elif isinstance(value, list):
        for item in value:
            walk_mapping(item, path=path, entries=entries, context=context)


def scan_structured(path: Path, entries: list[dict[str, str]]) -> None:
    suffix = path.suffix.lower()
    try:
        raw = path.read_text(encoding="utf-8")
    except Exception:
        return

    if suffix == ".json":
        try:
            payload = json.loads(raw)
        except Exception:
            return
        walk_mapping(payload, path=path, entries=entries, context="json_key")
        return

    if suffix in {".yaml", ".yml"} and yaml is not None:
        try:
            payload = yaml.safe_load(raw)
        except Exception:
            return
        walk_mapping(payload, path=path, entries=entries, context="yaml_key")


def scan_env_vars(path: Path, entries: list[dict[str, str]]) -> None:
    try:
        raw = path.read_text(encoding="utf-8")
    except Exception:
        return
    for env in set(UPPER_ENV_RE.findall(raw)):
        add_entry(
            entries,
            identifier=env,
            file_path=path,
            context="env_var",
            recommended_case="SCREAMING_SNAKE_CASE",
        )


def scan_redis_segments(path: Path, entries: list[dict[str, str]]) -> None:
    try:
        raw = path.read_text(encoding="utf-8")
    except Exception:
        return

    for line in raw.splitlines():
        if "format_redis_key" not in line and "RedisKey" not in line:
            continue
        for literal in re.findall(r"['\"]([a-zA-Z0-9:_-]+)['\"]", line):
            for segment in literal.split(":"):
                if not segment:
                    continue
                if "slug" in segment:
                    rec = "kebab-case"
                else:
                    rec = "snake_case"
                add_entry(
                    entries,
                    identifier=segment,
                    file_path=path,
                    context="redis_key_segment",
                    recommended_case=rec,
                )


def scan_cli_commands(repo: Path, entries: list[dict[str, str]]) -> None:
    pyproject = repo / "dev" / "packaging" / "pyproject.toml"
    if pyproject.exists():
        try:
            raw = pyproject.read_text(encoding="utf-8")
        except Exception:
            raw = ""
        in_scripts = False
        for line in raw.splitlines():
            stripped = line.strip()
            if stripped == "[project.scripts]":
                in_scripts = True
                continue
            if in_scripts and stripped.startswith("["):
                in_scripts = False
            if in_scripts and "=" in stripped and not stripped.startswith("#"):
                name = stripped.split("=", 1)[0].strip()
                add_entry(
                    entries,
                    identifier=name,
                    file_path=pyproject,
                    context="cli_command",
                    recommended_case="kebab-case",
                )

    commands_dir = repo / "commands"
    if commands_dir.is_dir():
        for path in commands_dir.iterdir():
            if path.is_file() and path.name:
                add_entry(
                    entries,
                    identifier=path.name,
                    file_path=path,
                    context="cli_command",
                    recommended_case="kebab-case",
                )


def scan_repo(repo: Path, entries: list[dict[str, str]]) -> None:
    files = iter_files(repo)
    for path in files:
        stem = path.stem
        suffix = path.suffix.lower()
        rec = SCRIPT_CASE.get(suffix)
        if rec and stem not in {"__init__", "README", "LICENSE", "Makefile"}:
            add_entry(
                entries,
                identifier=stem,
                file_path=path,
                context="filename",
                recommended_case=rec,
            )

        if suffix == ".py":
            scan_python(path, entries)
        elif suffix in {".js", ".ts", ".tsx", ".jsx"}:
            scan_js(path, entries)

        if suffix in {".json", ".yaml", ".yml"}:
            scan_structured(path, entries)

        if suffix in TEXT_SUFFIXES:
            scan_env_vars(path, entries)
            scan_redis_segments(path, entries)

    scan_cli_commands(repo, entries)


def build_rename_plan(entries: list[dict[str, str]]) -> list[dict[str, Any]]:
    by_identifier: dict[tuple[str, str], set[str]] = defaultdict(set)
    contexts: dict[tuple[str, str], set[str]] = defaultdict(set)
    for entry in entries:
        key = (entry["identifier"], entry["recommended_case"])
        by_identifier[key].add(entry["file_path"])
        contexts[key].add(entry["context"])

    plan: list[dict[str, Any]] = []
    for entry in entries:
        old = entry["identifier"]
        target_case = entry["recommended_case"]
        if entry["current_case"] == target_case:
            continue
        if target_case == "SCREAMING_SNAKE_CASE" and old.isupper():
            continue
        new = to_case(old, target_case)
        if new == old:
            continue
        key = (old, target_case)
        locations = sorted(by_identifier[key])

        update_rules = [
            "update references/imports",
            "update tests and fixtures",
            "update docs and examples",
            "verify lint/test suite",
        ]

        plan.append(
            {
                "old": old,
                "new": new,
                "locations": locations,
                "contexts": sorted(contexts[key]),
                "updateRules": update_rules,
            }
        )

    deduped: dict[tuple[str, str], dict[str, Any]] = {}
    for item in plan:
        deduped[(item["old"], item["new"])] = item
    return sorted(deduped.values(), key=lambda item: (item["old"], item["new"]))


def generate(
    repos: list[str],
    inventory_out: str,
    rename_plan_out: str,
) -> tuple[Path, Path, int, int]:
    entries: list[dict[str, str]] = []
    for repo_raw in repos:
        repo = Path(repo_raw).expanduser().resolve()
        if not repo.exists() or not repo.is_dir():
            raise SystemExit(f"Repo not found: {repo}")
        scan_repo(repo, entries)

    entries_sorted = sorted(
        entries,
        key=lambda row: (
            row["identifier"],
            row["context"],
            row["file_path"],
            row["recommended_case"],
        ),
    )
    plan = build_rename_plan(entries_sorted)

    inv_path = Path(inventory_out).expanduser().resolve()
    plan_path = Path(rename_plan_out).expanduser().resolve()
    inv_path.write_text(json.dumps(entries_sorted, indent=2) + "\n", encoding="utf-8")
    plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    return inv_path, plan_path, len(entries_sorted), len(plan)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate identifier inventory and rename plan")
    parser.add_argument("--repos", nargs="+", required=True, help="Repo roots to scan")
    parser.add_argument("--inventory-out", required=True, help="Output JSON path for inventory")
    parser.add_argument("--rename-plan-out", required=True, help="Output JSON path for rename plan")
    args = parser.parse_args()

    inv_path, plan_path, inventory_count, plan_count = generate(
        repos=args.repos,
        inventory_out=args.inventory_out,
        rename_plan_out=args.rename_plan_out,
    )

    print(f"Inventory entries: {inventory_count}")
    print(f"Rename plan entries: {plan_count}")
    print(f"Inventory path: {inv_path}")
    print(f"Rename plan path: {plan_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
