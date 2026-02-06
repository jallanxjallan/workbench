#!/home/jeremy/Python3.13Env/bin/python3.13
from dataclasses import dataclass
from pathlib import Path
import hashlib
import sys
from typing import Any, TextIO

import fire

from asc.core.rg_mapper import map_slugs, RgError
from asc.io.markdown import MarkdownFile
from asc.io.ndjson import iter_ndjson, emit_ndjson

from asc.core.contracts import ensure_contracts_shapes

ensure_contracts_shapes()
from autoscribe_shapes.regex import SLUG_VALUE_RE, SLUG_HAS_ALPHA_RE
from autoscribe_shapes.ndjson import (
    DEFAULT_SNIPPET_SCHEMA_VERSION,
    DECISION_AMBIGUOUS,
    DECISION_UPLOADABLE,
    FIELD_CONTENT,
    FIELD_DECISION,
    FIELD_LAST_HASH,
    FIELD_MTIME,
    FIELD_PATH,
    FIELD_SCHEMA_VERSION,
    FIELD_SCOPE,
    FIELD_SHA256,
    FIELD_SIZE,
    FIELD_SLUG,
    FIELD_TYPE,
    INSTRUCTION_SNIPPET_TYPE,
)




@dataclass(frozen=True)
class CheckSummary:
    total: int


def _die(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _extract_snippet_fields(
    path: Path,
    *,
    slug: str,
) -> tuple[str, str, str, str | None]:
    doc = MarkdownFile(path).read(
        require_sentinel=False,
        allow_front_matter=True,
    )
    front_matter = doc.front_matter or {}

    # slug is the sole human-authored identifier for markdown instructions.
    fm_slug = front_matter.get("slug")
    if fm_slug and fm_slug != slug:
        raise RuntimeError(
            f"Snippet slug mismatch in {path}: rg={slug!r} slug={fm_slug!r}"
        )

    if not isinstance(slug, str) or slug == "":
        raise RuntimeError(f"Missing slug in {path}")
    if not SLUG_VALUE_RE.fullmatch(slug) or not SLUG_HAS_ALPHA_RE.search(slug):
        raise RuntimeError(f"Invalid slug {slug!r} in {path}")

    scope = (
        front_matter.get("scope")
        or front_matter.get("role")
        or "global"
    )
    if not isinstance(scope, str) or not scope.strip():
        raise RuntimeError(f"Missing or invalid scope in {path}")

    scope = scope.strip()
    if scope == "instruction":
        scope = "global"

    schema_version = _coerce_schema_version(
        front_matter.get("schema_version")
        or front_matter.get("schema"),
        label="schema_version",
        path=path,
    )

    body = doc.body
    if not isinstance(body, str) or not body.strip():
        raise RuntimeError(f"Instruction body is empty in {path}")

    return slug, body, scope, schema_version


def _scan_instruction_candidates(root: Path) -> list[dict[str, Any]]:
    root = root.resolve()

    if not root.is_dir():
        _die("Root path is not a directory")

    try:
        slug_map = map_slugs(root)
    except RgError as exc:
        _die(str(exc))

    records: list[dict[str, Any]] = []

    for slug, path in sorted(slug_map.items()):
        if not path.exists():
            _die(f"File vanished: {path}")
        stat = path.stat()
        records.append(
            {
                FIELD_SLUG: slug,
                FIELD_PATH: str(path),
                FIELD_MTIME: float(stat.st_mtime),
                FIELD_SIZE: int(stat.st_size),
            }
        )

    return records


def check_instructions(
    root: Path | str = ".",
    output: str = "-",
    report: bool = True,
    return_summary: bool = False,
) -> CheckSummary | None:
    """
    Emit instruction candidates as NDJSON (slug/path/mtime/size).
    """
    records = _scan_instruction_candidates(Path(root))
    summary = CheckSummary(total=len(records))

    out_handle = _open_text(output, "w", sys.stdout)
    is_tty = _is_tty(out_handle)
    emit_records = not is_tty
    report = report and is_tty
    try:
        if emit_records:
            emit_ndjson(out_handle, records)
    finally:
        if out_handle is not sys.stdout:
            out_handle.close()

    if report:
        print(f"check_instructions: emitted {summary.total} candidates")
    if return_summary:
        return summary
    return None


@dataclass(frozen=True)
class EmitSummary:
    total: int
    emitted: int
    skipped: int


def emit_instructions(
    input: str = "-",
    output: str = "-",
    default_schema_version: str = DEFAULT_SNIPPET_SCHEMA_VERSION,
    report: bool = True,
    return_summary: bool = False,
) -> EmitSummary | None:
    """
    Read instruction candidates (NDJSON), resolve ambiguity, emit IR NDJSON.
    """
    in_handle = _open_text(input, "r", sys.stdin)
    out_handle = _open_text(output, "w", sys.stdout)
    is_tty = _is_tty(out_handle)
    emit_records = not is_tty
    report = report and is_tty

    total = emitted = skipped = 0

    try:
        for record in iter_ndjson(in_handle):
            total += 1
            candidate = _parse_candidate(record)
            path = Path(candidate[FIELD_PATH])

            if not path.exists():
                _die(f"Instruction file not found: {path}")

            try:
                slug, body, scope, fm_schema = _extract_snippet_fields(
                    path, slug=candidate[FIELD_SLUG]
                )
                schema_version = _select_schema_version(
                    fm_schema,
                    record.get(FIELD_SCHEMA_VERSION),
                    default_schema_version,
                    path=path,
                    report=report,
                )
                prior_hash = _coerce_hash(record.get(FIELD_LAST_HASH), path=path)
            except Exception as exc:
                _die(str(exc))

            sha = sha256_of(path)
            decision = candidate.get(FIELD_DECISION)

            if decision == DECISION_AMBIGUOUS:
                if prior_hash and prior_hash == sha:
                    skipped += 1
                    continue
                if prior_hash is None and report:
                    print(
                        (
                            "emit_instructions: "
                            f"missing last_hash for ambiguous record {slug!r}"
                        ),
                        file=sys.stderr,
                    )

            stat = path.stat()
            output_record = dict(record)
            output_record.update(
                {
                    FIELD_TYPE: INSTRUCTION_SNIPPET_TYPE,
                    FIELD_SLUG: slug,
                    FIELD_PATH: str(path),
                    FIELD_MTIME: float(stat.st_mtime),
                    FIELD_SIZE: int(stat.st_size),
                    FIELD_SHA256: sha,
                    FIELD_SCHEMA_VERSION: schema_version,
                    FIELD_CONTENT: body,
                    FIELD_SCOPE: scope,
                }
            )
            if emit_records:
                emit_ndjson(out_handle, [output_record])
            emitted += 1
    finally:
        if in_handle is not sys.stdin:
            in_handle.close()
        if out_handle is not sys.stdout:
            out_handle.close()

    summary = EmitSummary(total=total, emitted=emitted, skipped=skipped)
    if report:
        print(
            (
                "emit_instructions: "
                f"total={total} emitted={emitted} skipped={skipped}"
            ),
        )
    if return_summary:
        return summary
    return None


def _open_text(path: str, mode: str, default: TextIO) -> TextIO:
    if path == "-":
        return default
    return open(path, mode, encoding="utf-8")


def _is_tty(handle: TextIO) -> bool:
    isatty = getattr(handle, "isatty", None)
    if isatty is None:
        return False
    return bool(isatty())


def _parse_candidate(record: dict[str, Any]) -> dict[str, Any]:
    slug = record.get(FIELD_SLUG)
    path = record.get(FIELD_PATH)
    mtime = record.get(FIELD_MTIME)
    size = record.get(FIELD_SIZE)

    if not isinstance(slug, str) or not slug.strip():
        _die("Candidate slug must be a non-empty string")
    slug = slug.strip()
    if not SLUG_VALUE_RE.fullmatch(slug) or not SLUG_HAS_ALPHA_RE.search(slug):
        _die(f"Invalid slug {slug!r} in candidate record")

    if not isinstance(path, str) or not path.strip():
        _die("Candidate path must be a non-empty string")

    if isinstance(mtime, bool) or not isinstance(mtime, (int, float)):
        _die("Candidate mtime must be a number")
    if isinstance(size, bool) or not isinstance(size, (int, float)):
        _die("Candidate size must be a number")
    size_int = int(size)
    if size_int < 0:
        _die("Candidate size must be non-negative")

    decision = record.get(FIELD_DECISION)
    if decision is not None:
        if not isinstance(decision, str) or not decision.strip():
            _die("Candidate decision must be a non-empty string")
        decision = decision.strip().lower()
        if decision not in {DECISION_UPLOADABLE, DECISION_AMBIGUOUS}:
            _die(f"Unknown candidate decision: {decision}")

    return {
        FIELD_SLUG: slug,
        FIELD_PATH: path,
        FIELD_MTIME: float(mtime),
        FIELD_SIZE: size_int,
        FIELD_DECISION: decision,
    }


def _coerce_schema_version(
    value: Any,
    *,
    label: str,
    path: Path,
) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise RuntimeError(f"{label} must be a string in {path}")
    if isinstance(value, (str, int, float)):
        text = str(value).strip()
        if not text:
            raise RuntimeError(f"{label} must be non-empty in {path}")
        return text
    raise RuntimeError(f"{label} must be a string in {path}")


def _select_schema_version(
    front_matter: str | None,
    record_value: Any,
    default_value: str,
    *,
    path: Path,
    report: bool,
) -> str:
    record_version = _coerce_schema_version(
        record_value,
        label="schema_version",
        path=path,
    )

    if front_matter and record_version and front_matter != record_version:
        if report:
            print(
                (
                    "emit_instructions: "
                    f"schema_version mismatch in {path} "
                    f"(front_matter={front_matter!r}, record={record_version!r})"
                ),
                file=sys.stderr,
            )

    if front_matter:
        return front_matter
    if record_version:
        return record_version

    default_version = _coerce_schema_version(
        default_value,
        label="schema_version",
        path=path,
    )
    if default_version is None:
        _die("default_schema_version must be non-empty")
    return default_version


def _coerce_hash(value: Any, *, path: Path) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"last_hash must be a non-empty string in {path}")
    return value.strip()


def main() -> None:
    fire.Fire(
        {
            "check_instructions": check_instructions,
            "emit_instructions": emit_instructions,
        }
    )


if __name__ == "__main__":
    main()


__all__ = [
    "check_instructions",
    "emit_instructions",
    "CheckSummary",
    "EmitSummary",
]
