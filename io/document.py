from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, Literal, Mapping

import yaml

from runtime.text import strip_utf8_bom

RenderMode = Literal["full", "content", "frontmatter"]


def _to_json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _to_json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_json_value(item) for item in value]
    return str(value)


@dataclass(frozen=True)
class DocumentParseResult:
    has_frontmatter: bool
    body: str
    metadata: dict[str, Any] | None
    error: str | None


@dataclass
class Document:
    """
    Canonical in-memory Markdown + frontmatter abstraction.
    """

    content: str | None = None
    metadata: dict[str, Any] | None = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.content, list):
            self.content = "\n\n".join(str(item) for item in self.content)
        elif self.content is None:
            self.content = ""
        elif not isinstance(self.content, str):
            self.content = str(self.content)

        if self.metadata is None:
            self.metadata = {}
        elif isinstance(self.metadata, str):
            parsed = self.inspect_text(self.metadata)
            if parsed.error:
                raise ValueError(f"Failed to parse metadata: {parsed.error}")
            self.metadata = parsed.metadata or {}
        elif isinstance(self.metadata, Mapping):
            self.metadata = _to_json_value(dict(self.metadata))
        else:
            raise ValueError("metadata must be a mapping object")

    def __str__(self) -> str:
        return self.content

    @staticmethod
    def parse_metadata_block(raw_metadata: str) -> dict[str, Any]:
        try:
            parsed = yaml.safe_load(raw_metadata)
        except Exception as exc:
            raise ValueError(str(exc)) from exc

        if parsed is None:
            return {}
        if not isinstance(parsed, dict):
            raise ValueError("frontmatter must be a mapping object")

        return _to_json_value(parsed)

    @classmethod
    def inspect_text(cls, text: str) -> DocumentParseResult:
        normalized = strip_utf8_bom(text)
        lines = normalized.splitlines(keepends=True)

        if not lines:
            return DocumentParseResult(False, "", None, None)

        idx = 0
        while idx < len(lines) and lines[idx].strip() == "":
            idx += 1

        if idx >= len(lines) or lines[idx].strip() != "---":
            return DocumentParseResult(False, normalized, None, None)

        end = idx + 1
        while end < len(lines) and lines[end].strip() != "---":
            end += 1

        if end >= len(lines):
            return DocumentParseResult(True, normalized, None, "unterminated frontmatter")

        raw_metadata = "".join(lines[idx + 1:end])
        prefix = "".join(lines[:idx])
        suffix = "".join(lines[end + 1:])

        if suffix.startswith("\n"):
            suffix = suffix[1:]

        body = prefix + suffix

        try:
            metadata = cls.parse_metadata_block(raw_metadata)
        except ValueError as exc:
            return DocumentParseResult(
                True,
                body,
                None,
                f"invalid YAML frontmatter: {exc}",
            )

        return DocumentParseResult(True, body, metadata, None)

    @classmethod
    def read_text(cls, text: str) -> Document:
        parsed = cls.inspect_text(text)
        if parsed.error:
            raise ValueError(f"Failed to parse markdown: {parsed.error}")
        return cls(
            content=parsed.body,
            metadata=parsed.metadata or {},
        )

    def render(self, mode: RenderMode = "full") -> str:
        if mode == "content":
            return self.content or ""

        metadata = self.metadata or {}
        frontmatter = ""
        if metadata:
            try:
                serialized_metadata = yaml.safe_dump(
                    metadata,
                    sort_keys=False,
                    allow_unicode=True,
                    default_flow_style=False,
                )
            except Exception as exc:
                raise IOError(f"Failed to serialize YAML: {exc}") from exc
            frontmatter = f"---\n{serialized_metadata}---\n"

        if mode == "frontmatter":
            return frontmatter

        if mode != "full":
            raise ValueError(f"invalid render mode: {mode}")

        if frontmatter:
            return f"{frontmatter}\n{self.content}"
        return self.content or ""

    def write_text(self, mode: RenderMode = "full") -> str:
        return self.render(mode=mode)

    @property
    def word_count(self) -> int:
        return len(re.findall(r"\b\w+\b", self.content))

    @property
    def words(self) -> int:
        return self.word_count

    def comments(self) -> list[str]:
        return re.findall(r"<!--(.*?)-->", self.content, re.DOTALL)

    def get(self, key: str, default: Any = None) -> Any:
        return (self.metadata or {}).get(key, default)

    def has_metadata(self, key: str) -> bool:
        return key in (self.metadata or {})