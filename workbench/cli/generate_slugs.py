"""Generate slugs for all slug-sentinel markdown files in Studio."""

from __future__ import annotations

import argparse
import sys

from workbench.config.roots import STUDIO_ROOT
from workbench.slug.writer import SlugGenerationError, generate_slugs


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="generate-slugs",
        description=__doc__,
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Replace slug sentinel '__SLUG__' in matching files.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    try:
        result = generate_slugs(root=STUDIO_ROOT, write=bool(args.write))
    except SlugGenerationError as exc:
        print(f"[generate-slugs] error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"[generate-slugs] error: {exc}", file=sys.stderr)
        return 1

    for assignment in result.assignments:
        print(f"{assignment.slug} {assignment.file}")

    print(
        "[generate-slugs] complete: "
        f"discovered {result.discovered} sentinel file(s), "
        f"skipped {result.skipped} template file(s), "
        f"generated {result.generated} slug(s), "
        f"written {result.written} slug(s), "
        f"failed {result.failed} file(s)"
    )

    if result.errors:
        for detail in result.errors:
            print(f"[generate-slugs] error: {detail}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
