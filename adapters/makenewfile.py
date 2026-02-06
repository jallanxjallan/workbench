#!/home/jeremy/Python3.13Env/bin/python
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, TextIO
from urllib.parse import urlparse

import attr
import fire


_ALNUM_RE = re.compile(r"[A-Za-z0-9]+")
_CANDIDATE_FIELDS = [
    "url",
    "uri",
    "source",
    "source_url",
    "source_uri",
    "origin",
    "filepath",
    "file_path",
    "path",
    "original_path",
]


def _strip_extensions(name: str) -> str:
    if not name:
        return name

    if name.startswith("."):
        parts = [p for p in name.split(".") if p]
        return parts[0] if parts else name.lstrip(".")

    return name.split(".", 1)[0]


def _to_snake_case(text: str) -> str:
    if not text:
        return ""
    lowered = text.lower()
    cleaned = re.sub(r"[^a-z0-9]+", "_", lowered)
    return cleaned.strip("_")


_YAML_SPECIAL_VALUES = {
    "null", "Null", "NULL",
    "true", "True", "TRUE",
    "false", "False", "FALSE",
    "yes", "Yes", "YES",
    "no", "No", "NO",
    "on", "On", "ON",
    "off", "Off", "OFF",
    "~",
}


def _needs_yaml_quotes(value: str) -> bool:
    if value == "":
        return True
    if value.strip() != value:
        return True
    if "\n" in value or "\r" in value or "\t" in value:
        return True
    if value[0] in "-?:!*&@`#{}[],|>%\"'":
        return True
    if ": " in value:
        return True
    if value in _YAML_SPECIAL_VALUES:
        return True
    return False


def _yaml_value(value: str) -> str:
    if value is None:
        return "null"
    if not isinstance(value, str):
        value = str(value)
    if _needs_yaml_quotes(value):
        return json.dumps(value, ensure_ascii=False)
    return value


@attr.define(frozen=True)
class EmitItem:
    record: dict
    line_no: int


@attr.define
class MakefileAdapter:
    out_dir: Path = attr.field(converter=Path)
    dry_run: bool = False

    def run(self, *, in_path: str | None = None, source: TextIO | None = None) -> None:
        if source is not None:
            self._process(source)
            return

        if in_path and in_path != "-":
            with open(in_path, "r", encoding="utf-8") as fh:
                self._process(fh)
            return

        self._process(sys.stdin)

    def _process(self, stream: TextIO) -> None:
        for item in self.parse_ndjson(stream):
            record = item.record
            content = record.get("content")

            if not isinstance(content, str):
                _log_item_error(
                    reason="missing or invalid content",
                    inferred_name="",
                    source_label="unknown",
                    call_ulid=_get_call_ulid(record),
                )
                continue

            source_blob = record.get("source_blob")
            source_label = self.infer_source_label(source_blob, record)
            source_type = self._infer_source_type(source_label)

            filename = self.sanitize_filename(
                self.infer_filename(
                    source_label,
                    content,
                    fallback_id=_get_call_ulid(record),
                )
            )

            emitted_at = self._iso_now()
            frontmatter = self.build_frontmatter(
                source_label=source_label,
                emitted_at=emitted_at,
                call_id=_get_call_ulid(record),
                batch_id=record.get("batch_id"),
                source_type=source_type,
            )

            written = self.write_markdown(
                out_dir=self.out_dir,
                filename=filename,
                frontmatter=frontmatter,
                content=content,
                dry_run=self.dry_run,
            )

            if written is None:
                _log_item_error(
                    reason="file exists; not overwriting",
                    inferred_name=filename,
                    source_label=source_label,
                    call_ulid=_get_call_ulid(record),
                )
            elif self.dry_run:
                _log_item_error(
                    reason="dry-run: not written",
                    inferred_name=filename,
                    source_label=source_label,
                    call_ulid=_get_call_ulid(record),
                )

    def parse_ndjson(self, stream: TextIO) -> Iterator[EmitItem]:
        """
        Parse NDJSON from a stream.

        Malformed lines are logged and skipped.
        """
        for line_no, line in enumerate(stream, 1):
            raw = line.strip()
            if not raw:
                continue

            try:
                obj = json.loads(raw)
            except json.JSONDecodeError as exc:
                _log_item_error(
                    reason=f"invalid JSON: {exc}",
                    inferred_name="",
                    source_label="unknown",
                    call_ulid="unknown",
                )
                continue

            if not isinstance(obj, dict):
                _log_item_error(
                    reason=f"expected JSON object, got {type(obj).__name__}",
                    inferred_name="",
                    source_label="unknown",
                    call_ulid="unknown",
                )
                continue

            yield EmitItem(record=obj, line_no=line_no)

    def infer_source_label(self, source_blob: object | None, record: dict) -> str:
        """
        Infer a source label from source_blob or record fields.
        """
        candidates: list[str] = []

        def _collect_from_mapping(mapping: dict) -> None:
            for field in _CANDIDATE_FIELDS:
                value = mapping.get(field)
                if isinstance(value, str) and value.strip():
                    candidates.append(value.strip())
                elif isinstance(value, dict):
                    if isinstance(value.get("url"), str):
                        candidates.append(value["url"].strip())
                    if isinstance(value.get("uri"), str):
                        candidates.append(value["uri"].strip())
                    if isinstance(value.get("path"), str):
                        candidates.append(value["path"].strip())

            metadata = mapping.get("metadata")
            if isinstance(metadata, dict):
                for field in ("source", "url"):
                    value = metadata.get(field)
                    if isinstance(value, str) and value.strip():
                        candidates.append(value.strip())

            origin = mapping.get("origin")
            if isinstance(origin, dict):
                for field in ("url", "uri", "path"):
                    value = origin.get(field)
                    if isinstance(value, str) and value.strip():
                        candidates.append(value.strip())

        if isinstance(source_blob, str):
            raw = source_blob.strip()
            if raw:
                parsed = None
                if raw.startswith("{") and raw.endswith("}"):
                    try:
                        parsed = json.loads(raw)
                    except Exception:
                        parsed = None
                if isinstance(parsed, dict):
                    _collect_from_mapping(parsed)
                else:
                    candidates.append(raw)
        elif isinstance(source_blob, dict):
            _collect_from_mapping(source_blob)

        if isinstance(record, dict):
            _collect_from_mapping(record)

        return candidates[0] if candidates else "unknown"

    def infer_filename(
        self,
        source_label: str,
        content: str,
        fallback_id: str,
    ) -> str:
        """
        Infer a safe filename using ordered heuristics.
        """
        filename = self._filename_from_source(source_label)
        if filename:
            return filename

        slug = self._slug_from_text(source_label)
        if slug:
            return f"{slug}.md"

        line = self._first_non_empty_line(content)
        if line:
            slug = self._slug_from_text(line)
            if slug:
                return f"{slug}.md"

        return f"{self.sanitize_filename(fallback_id)}.md"

    def sanitize_filename(self, name: str) -> str:
        """
        Ensure the filename is filesystem-safe and flat.
        """
        if not name:
            return "unknown.md"

        base = _strip_extensions(name)
        base = _to_snake_case(base)
        base = base or "unknown"
        return f"{base}.md"

    def build_frontmatter(
        self,
        *,
        source_label: str,
        emitted_at: str,
        call_id: str | None = None,
        batch_id: str | None = None,
        source_type: str | None = None,
    ) -> str:
        lines: list[str] = ["---"]
        lines.append(f"source: {_yaml_value(source_label)}")
        lines.append(f"emitted_at: {_yaml_value(emitted_at)}")
        if call_id:
            lines.append(f"call_id: {_yaml_value(call_id)}")
        if batch_id:
            lines.append(f"batch_id: {_yaml_value(batch_id)}")
        if source_type:
            lines.append(f"source_type: {_yaml_value(source_type)}")
        lines.append("---")
        return "\n".join(lines) + "\n"

    def write_markdown(
        self,
        *,
        out_dir: Path,
        filename: str,
        frontmatter: str,
        content: str,
        dry_run: bool = False,
    ) -> Path | None:
        target = out_dir / filename

        if target.exists():
            return None

        if dry_run:
            return target

        out_dir.mkdir(parents=True, exist_ok=True)
        target.write_text(frontmatter + content, encoding="utf-8")
        return target

    def _filename_from_source(self, source_label: str) -> str | None:
        if not source_label or source_label == "unknown":
            return None

        parsed = urlparse(source_label)
        if parsed.scheme and parsed.netloc:
            name = Path(parsed.path).name
            if name:
                return self.sanitize_filename(name)

        name = Path(source_label).name
        if name and name != source_label:
            return self.sanitize_filename(name)
        return None

    def _slug_from_text(self, text: str) -> str | None:
        if not text:
            return None
        tokens = _ALNUM_RE.findall(text.lower())
        if not tokens:
            return None
        slug = "_".join(tokens[:12])
        return slug[:80] if slug else None

    def _first_non_empty_line(self, content: str) -> str | None:
        for line in content.splitlines():
            if line.strip():
                return line.strip()
        return None

    def _infer_source_type(self, source_label: str) -> str:
        if not source_label or source_label == "unknown":
            return "unknown"
        parsed = urlparse(source_label)
        if parsed.scheme in {"http", "https"}:
            return "url"
        if "/" in source_label or "\\" in source_label:
            return "file"
        return "unknown"

    def _iso_now(self) -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _get_call_ulid(record: dict) -> str:
    value = record.get("call_ulid") or record.get("call_id")
    return value if isinstance(value, str) and value else "unknown"


def _log_item_error(
    *,
    reason: str,
    inferred_name: str,
    source_label: str,
    call_ulid: str,
) -> None:
    print(
        (
            "makefile: "
            f"reason={reason} "
            f"filename={inferred_name or 'unknown'} "
            f"source={source_label or 'unknown'} "
            f"call_ulid={call_ulid or 'unknown'}"
        ),
        file=sys.stderr,
    )


def main(
    in_path: str | None = None,
    out_dir: str = ".",
    dry_run: bool = False,
) -> None:
    adapter = MakefileAdapter(out_dir=Path(out_dir), dry_run=dry_run)
    adapter.run(in_path=in_path)


if __name__ == "__main__":
    fire.Fire(main)


__all__ = [
    "EmitItem",
    "MakefileAdapter",
    "main",
]
