from __future__ import annotations

import sys
from pathlib import Path

from upload.uploader import run_all


def main(argv: list[str] | None = None) -> int:
    argv = argv or []

    if argv:
        print(
            f"upload: bare upload command does not accept arguments: {' '.join(argv)}",
            file=sys.stderr,
        )
        return 2

    run_all(
        root=Path.cwd(),
        output=sys.stdout,
        err=sys.stderr,
    )
    return 0