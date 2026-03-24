"""CLI wrapper for whole-set profile upload."""

from __future__ import annotations

import argparse
import sys

from upload.profiles import UploadProfilesError, upload_profiles



def _parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        prog="upload-profiles",
        description=__doc__,
    )



def main(argv: list[str] | None = None) -> int:
    _parser().parse_args(argv)
    try:
        return upload_profiles()
    except UploadProfilesError as exc:
        print(f"upload-profiles: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
