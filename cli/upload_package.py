"""CLI wrapper for package upload compilation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from upload.package import UploadPackageError, upload_package



def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="upload-package",
        description=__doc__,
    )
    parser.add_argument("package_file", help="Path to the package manifest")
    return parser



def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        return upload_package(Path(args.package_file))
    except UploadPackageError as exc:
        print(f"upload-package: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
