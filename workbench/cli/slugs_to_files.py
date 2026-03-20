"""Resolve canonical NDJSON slug records into markdown file-content records."""

from __future__ import annotations

import argparse
import sys
from typing import Any

from workbench.ingest.records import RecordContractError, dump_record, iter_records, make_record
from workbench.resolver import ResolverError, resolve_slugs
from workbench.write.common import has_piped_stdin


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="slugs-to-files",
        description=__doc__,
    )
    return parser


def stream_slug_files(*, stdin: object = sys.stdin, stdout: object = sys.stdout) -> int:
    try:
        records = list(iter_records(stdin))
        slugs: list[str] = []
        input_records: list[dict[str, Any]] = []
        for record in records:
            input_record = dict(record["input_record"])
            slug = input_record.get("slug")
            if not isinstance(slug, str) or not slug.strip():
                raise RecordContractError("input_record.slug must be a non-empty string")
            slugs.append(slug.strip())
            input_records.append(input_record)

        paths = resolve_slugs(slugs)
        payloads: list[str] = []
        for input_record, path in zip(input_records, paths, strict=True):
            content = path.read_text(encoding="utf-8")
            payloads.append(dump_record(make_record(content=content, input_record=input_record)))

        for payload in payloads:
            stdout.write(payload)
        return 0
    except (ResolverError, RecordContractError) as exc:
        print(f"[slugs-to-files] error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"[slugs-to-files] error: {exc}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    _parser().parse_args(argv)
    if not has_piped_stdin(sys.stdin):
        _parser().print_usage(sys.stderr)
        print("ERROR: expected canonical NDJSON input from stdin", file=sys.stderr)
        return 1
    return stream_slug_files()


if __name__ == "__main__":
    raise SystemExit(main())
