from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TextIO

from upload.ndjson import validate_record


class ManifestHelperError(RuntimeError):
    pass


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("upload: requires at least one manifest file path", file=sys.stderr)
        return 1

    emitted = 0
    failed = 0

    for raw_path in args:
        path = Path(raw_path).expanduser().resolve()

        try:
            emit_one(path=path, output=sys.stdout, err=sys.stderr)
            emitted += 1
        except Exception as exc:
            failed += 1
            print(f"upload: {path}: {exc}", file=sys.stderr)

    print(
        f"upload: emitted {emitted} record(s); failed {failed} manifest(s)",
        file=sys.stderr,
    )
    return 1 if failed else 0


def emit_one(*, path: Path, output: TextIO, err: TextIO) -> None:
    record = load_json_record(path)
    validated = validate_record(record)
    output.write(json.dumps(validated, ensure_ascii=False))
    output.write("\n")
    print(f"upload: emitted 1 record from {path}", file=err)


def load_json_record(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise ManifestHelperError(f"manifest file not found: {path}")

    if path.suffix.lower() != ".json":
        raise ManifestHelperError(f"manifest file must be .json: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ManifestHelperError(f"cannot read JSON file {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ManifestHelperError(f"invalid JSON in {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ManifestHelperError(f"top-level JSON object required: {path}")

    return data


if __name__ == "__main__":
    raise SystemExit(main())