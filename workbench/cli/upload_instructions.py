"""Emit canonical NDJSON instruction records for ASC upsert."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import TextIO

from workbench.config.roots import CONTROL_ROOT, STUDIO_ROOT
from workbench.ingest.records import RecordContractError, dump_record, make_record
from workbench.scan.rg import RipgrepError, rg_search
from workbench.scan.rg_collect_unique_slugs import rg_collect_unique_slugs

TYPE_PATTERN = r"^type:\s*(instruction|package)\s*$"
_MARKDOWN_EXTENSIONS = ["md", "markdown"]
_VAULT_REGISTRY_FILENAME = "_vault_registry.json"


class UploadInstructionsError(RuntimeError):
    """Raised when instruction discovery or emission fails."""


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="upload-instructions",
        description=__doc__,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate discovery and emit NDJSON without side effects.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit discovery counts as JSON instead of NDJSON records.",
    )
    return parser


def _iter_active_studio_vault_roots(studio_root: Path) -> tuple[Path, ...]:
    root = Path(studio_root).expanduser().resolve()
    if not root.exists():
        return ()
    if not root.is_dir():
        raise UploadInstructionsError(f"studio root is not a directory: {root}")

    vaults: list[Path] = []
    for candidate in sorted(path for path in root.iterdir() if path.is_dir()):
        if candidate.name.startswith("."):
            continue
        if (candidate / _VAULT_REGISTRY_FILENAME).is_file():
            vaults.append(candidate.resolve())
    return tuple(vaults)


def _instruction_roots() -> tuple[Path, ...]:
    roots = [Path(CONTROL_ROOT).expanduser().resolve(), *_iter_active_studio_vault_roots(STUDIO_ROOT)]
    unique_roots: list[Path] = []
    for root in roots:
        if root not in unique_roots:
            unique_roots.append(root)
    return tuple(unique_roots)


def rg_collect_typed_paths(*, roots: tuple[Path, ...]) -> set[Path]:
    paths: set[Path] = set()
    for root in roots:
        for record in rg_search(
            pattern=TYPE_PATTERN,
            root=root,
            extensions=_MARKDOWN_EXTENSIONS,
        ):
            path = record.get("path")
            if isinstance(path, Path):
                paths.add(path.resolve())
    return paths


def extract_body(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            return parts[2].lstrip("\n")
    return text


def compute_hash(content: str) -> str:
    return "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()


def _prepare_records(*, roots: tuple[Path, ...]) -> tuple[list[dict[str, object]], int, int]:
    try:
        slug_map = rg_collect_unique_slugs(roots=roots)
        typed_paths = rg_collect_typed_paths(roots=roots)
    except (RipgrepError, RuntimeError) as exc:
        raise UploadInstructionsError(str(exc)) from exc

    filtered = {slug: path for slug, path in slug_map.items() if path.resolve() in typed_paths}

    records: list[dict[str, object]] = []
    for slug, path in sorted(filtered.items()):
        content = extract_body(path)
        records.append(
            make_record(
                content=content,
                input_record={
                    "slug": slug,
                    "content_hash": compute_hash(content),
                },
            )
        )
    return records, len(slug_map), len(filtered)


def _emit_ndjson(records: list[dict[str, object]], *, stdout: TextIO) -> None:
    for record in records:
        stdout.write(dump_record(record))


def run(
    *,
    dry_run: bool = False,
    json_out: bool = False,
    stdout: TextIO = sys.stdout,
) -> int:
    del dry_run
    roots = _instruction_roots()
    records, discovered, emitted = _prepare_records(roots=roots)
    vaults = max(0, len(roots) - 1)

    if json_out:
        stdout.write(
            json.dumps(
                {
                    "vaults": vaults,
                    "discovered": discovered,
                    "emitted": emitted,
                },
                ensure_ascii=False,
                separators=(",", ":"),
            )
            + "\n"
        )
        return 0

    _emit_ndjson(records, stdout=stdout)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        return run(dry_run=args.dry_run, json_out=args.json)
    except (OSError, RecordContractError, UploadInstructionsError) as exc:
        print(f"[upload-instructions] error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
