"""Write streamed NDJSON records into current-vault notes from one template."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import TextIO

from workbench.write.common import WriteError, has_piped_stdin
from workbench.write.writenew import write_new_records_with_template

VAULT_REGISTRY_FILENAME = "_vault_registry.json"


def parser() -> argparse.ArgumentParser:
    command_parser = argparse.ArgumentParser(
        prog="writenew",
        description="Write NDJSON records into current vault files using one template.",
    )
    command_parser.add_argument(
        "--folder",
        default="contents",
        help="Target folder under the current vault (default: contents).",
    )
    command_parser.add_argument(
        "--template",
        default="passage",
        help="Template name under _common/templates (default: passage).",
    )
    return command_parser


def _resolve_current_vault(cwd: Path) -> Path:
    vault_root = cwd.expanduser().resolve()
    marker = vault_root / VAULT_REGISTRY_FILENAME
    if not marker.is_file():
        raise WriteError(
            f"current directory is not a vault (missing {VAULT_REGISTRY_FILENAME}): "
            f"{vault_root}"
        )
    return vault_root


def _vault_display_name(vault_root: Path) -> str:
    marker = vault_root / VAULT_REGISTRY_FILENAME
    fallback = vault_root.name
    try:
        payload = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback
    if not isinstance(payload, dict):
        return fallback

    for key in ("name", "vault"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return fallback


def _resolve_folder(vault_root: Path, folder: str) -> Path:
    folder_raw = str(folder).strip()
    if not folder_raw:
        raise WriteError("folder must be a non-empty string")

    folder_relative = Path(folder_raw)
    if folder_relative.is_absolute():
        raise WriteError(f"folder must be vault-relative: {folder_raw}")

    target = (vault_root / folder_relative).resolve()
    try:
        target.relative_to(vault_root)
    except ValueError as exc:
        raise WriteError(f"folder escapes vault root: {folder_raw}") from exc

    target.mkdir(parents=True, exist_ok=True)
    if not target.is_dir():
        raise WriteError(f"target folder is not a directory: {target}")
    return target


def _resolve_template(vault_root: Path, template: str) -> tuple[str, str]:
    template_raw = str(template).strip()
    if not template_raw:
        raise WriteError("template must be a non-empty string")

    template_name = template_raw[:-3] if template_raw.endswith(".md") else template_raw
    if "/" in template_name or "\\" in template_name:
        raise WriteError(
            f"invalid template '{template_raw}': expected template name only"
        )
    if template_name.startswith("_"):
        raise WriteError(
            f"template names starting with '_' are not selectable: {template_name}"
        )

    templates_root = (vault_root / "_common" / "templates").resolve()
    if not templates_root.is_dir():
        raise WriteError(f"template directory is missing: {templates_root}")

    template_path = (templates_root / f"{template_name}.md").resolve()
    try:
        template_path.relative_to(templates_root)
    except ValueError as exc:
        raise WriteError(f"template path escapes template root: {template_path}") from exc
    if not template_path.is_file():
        raise WriteError(f"template not found: {template_path}")

    return template_name, str(template_path)


def _read_confirmation(prompt: str, *, tty_reader: TextIO | None = None) -> str:
    if tty_reader is not None:
        print(prompt)
        line = tty_reader.readline()
        return line.strip().lower() if line else ""

    print(prompt)
    try:
        with Path("/dev/tty").open("r", encoding="utf-8") as handle:
            line = handle.readline()
    except OSError as exc:
        raise WriteError("confirmation requires an interactive TTY") from exc
    return line.strip().lower() if line else ""


def run(
    *,
    folder: str,
    template: str,
    input_stream,
    cwd: Path | None = None,
    tty_reader: TextIO | None = None,
) -> bool:
    vault_root = _resolve_current_vault(cwd or Path.cwd())
    folder_path = _resolve_folder(vault_root, folder)
    template_name, template_path = _resolve_template(vault_root, template)
    display = _vault_display_name(vault_root)
    prompt = (
        f"ingesting into {display} folder {folder_path.relative_to(vault_root)} "
        f"apply template {template_name} y/n"
    )

    if _read_confirmation(prompt, tty_reader=tty_reader) != "y":
        return False

    write_new_records_with_template(
        template_path=template_path,
        target_path=str(folder_path),
        debug_routing=False,
        input_stream=input_stream,
    )
    return True


def main(argv: list[str] | None = None) -> int:
    command_parser = parser()
    args = command_parser.parse_args(argv)
    if not has_piped_stdin(sys.stdin):
        command_parser.print_usage(sys.stderr)
        print("ERROR: expected NDJSON input from stdin (pipe or < file)", file=sys.stderr)
        return 1

    try:
        completed = run(
            folder=args.folder,
            template=args.template,
            input_stream=sys.stdin,
        )
        return 0 if completed else 0
    except WriteError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

