"""CLI wrapper for upload confirmation reconciliation."""

from __future__ import annotations

import argparse
import sys

from upload.confirm import ConfirmUploadError, confirm_upload



def _parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        prog="confirm-upload",
        description=__doc__,
    )



def main(argv: list[str] | None = None) -> int:
    _parser().parse_args(argv)
    try:
        confirm_upload(sys.stdin)
    except ConfirmUploadError as exc:
        print(f"confirm-upload: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
