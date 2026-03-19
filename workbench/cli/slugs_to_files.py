"""Resolve canonical NDJSON slug records into markdown file-content records."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from workbench.batch.repository import BatchRepositoryError, resolve_repo_slug_file
from workbench.ingest.records import RecordContractError, dump_record, iter_records, make_record
from workbench.write.common import has_piped_stdin


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="slugs-to-files",
        description=__doc__,
    )
    parser.add_argument(
        "--repo",
        default=".",
        help="Repository path used for slug resolution (default: current directory).",
    )
    return parser


def stream_slug_files(*, repo: Path | str = ".", stdin: object = sys.stdin, stdout: object = sys.stdout) -> int:
    try:
        for record in iter_records(stdin):
            input_record = dict(record["input_record"])
            slug = input_record.get("slug")
            if not isinstance(slug, str) or not slug.strip():
                raise RecordContractError("input_record.slug must be a non-empty string")

            path = resolve_repo_slug_file(slug.strip(), repo=repo)
            content = path.read_text(encoding="utf-8")
            stdout.write(dump_record(make_record(content=content, input_record=input_record)))
        return 0
    except (BatchRepositoryError, RecordContractError) as exc:
        print(f"[slugs-to-files] error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"[slugs-to-files] error: {exc}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if not has_piped_stdin(sys.stdin):
        _parser().print_usage(sys.stderr)
        print("ERROR: expected canonical NDJSON input from stdin", file=sys.stderr)
        return 1
    return stream_slug_files(repo=Path(args.repo))


if __name__ == "__main__":
    raise SystemExit(main())
