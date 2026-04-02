"""CLI wrapper for whole-set profile upload."""

from __future__ import annotations

import argparse
import sys

import upload.profiles as source


def _parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        prog="upload-profiles",
        description=__doc__,
    )


def main(argv: list[str] | None = None) -> int:
    _parser().parse_args(argv)
    try:
        return int(source.main())
    except source.UploadProfilesSimpleError as exc:
        print(f"upload-profiles: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())