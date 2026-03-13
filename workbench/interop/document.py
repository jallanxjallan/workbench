from __future__ import annotations
# TO-DO: set hashes on write https://claude.ai/share/33c548b5-8d16-48ab-afcd-9a468581413b
from dataclasses import dataclass, field
import importlib
from pathlib import Path
import re
from typing import Any, Mapping

from workbench.lib.text import strip_utf8_bom

_SERDE_MODULE = importlib.import_module("YAML".lower())

def _to_json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _to_json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_json_value(item) for item in value]
    return str(value)


# ---------------------------------------------------------------------------
# Parse Result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DocumentParseResult:
    has_frontmatter: bool
    body: str
    metadata: dict[str, Any] | None
    error: str | None
    raw_frontmatter: str | None = None


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------


@dataclass
class Document:
    """
    Canonical Markdown + frontmatter abstraction.

    Responsibilities:
    - Deterministic YAML serialization
    - Safe frontmatter parsing
    - Metadata normalization
    - Explicit failure on invalid access

    Invariants:
    - metadata is always a dict
    - content is always a string (never None internally)
    - No silent attribute failures
    """

    content: str | None = None
    metadata: dict[str, Any] | None = field(default_factory=dict)
    filepath: Path | None = None
    raw_frontmatter: str | None = None
    preserve_raw_frontmatter: bool = False
    source_metadata: dict[str, Any] | None = None

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def __post_init__(self) -> None:
        # Normalize content
        if isinstance(self.content, list):
            self.content = "\n\n".join(str(item) for item in self.content)
        elif self.content is None:
            self.content = ""
        elif not isinstance(self.content, str):
            self.content = str(self.content)

        # Normalize metadata
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

        if self.source_metadata is None:
            self.source_metadata = _to_json_value(dict(self.metadata))
        elif isinstance(self.source_metadata, Mapping):
            self.source_metadata = _to_json_value(dict(self.source_metadata))
        else:
            raise ValueError("source_metadata must be a mapping object")

        # Normalize filepath
        if self.filepath is not None and not isinstance(self.filepath, Path):
            self.filepath = Path(self.filepath)

    # ------------------------------------------------------------------
    # Attribute Access
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        return self.content

    def __getattr__(self, attr: str) -> Any:
        """
        Allow metadata access via attributes.
        Fail loudly if attribute does not exist.
        """
        if attr in ("content", "metadata", "filepath"):
            return super().__getattribute__(attr)

        if self.metadata and attr in self.metadata:
            return self.metadata[attr]

        raise AttributeError(attr)

    # ------------------------------------------------------------------
    # YAML Parsing
    # ------------------------------------------------------------------

    @staticmethod
    def parse_metadata_block(raw_metadata: str) -> dict[str, Any]:
        try:
            parsed = _SERDE_MODULE.safe_load(raw_metadata)
        except Exception as exc:  # noqa: BLE001
            raise ValueError(str(exc)) from exc

        if parsed is None:
            return {}
        if not isinstance(parsed, dict):
            raise ValueError("frontmatter must be a mapping object")

        return _to_json_value(parsed)

    @classmethod
    def inspect_text(
        cls,
        text: str,
    ) -> DocumentParseResult:
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

        raw_metadata = "".join(lines[idx + 1 : end])
        prefix = "".join(lines[:idx])
        suffix = "".join(lines[end + 1 :])

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
                raw_frontmatter=raw_metadata,
            )

        return DocumentParseResult(
            True,
            body,
            metadata,
            None,
            raw_frontmatter=raw_metadata,
        )

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------

    @classmethod
    def read_text(
        cls,
        text: str,
    ) -> Document:
        parsed = cls.inspect_text(text)
        if parsed.error:
            raise ValueError(f"Failed to parse markdown: {parsed.error}")
        return cls(
            content=parsed.body,
            metadata=parsed.metadata or {},
            raw_frontmatter=parsed.raw_frontmatter,
            preserve_raw_frontmatter=parsed.has_frontmatter,
            source_metadata=parsed.metadata or {},
        )

    @classmethod
    def read_file(
        cls,
        filepath: str | Path,
    ) -> Document:
        fp = Path(filepath)

        if not fp.exists():
            raise FileNotFoundError(f"{filepath} does not exist.")

        if fp.suffix.lower() not in (".md", ".markdown"):
            raise ValueError(f"{filepath} is not a markdown document.")

        text = fp.read_text(encoding="utf-8")
        doc = cls.read_text(text)
        doc.filepath = fp
        return doc

    @classmethod
    def inspect_file(
        cls,
        filepath: str | Path,
    ) -> DocumentParseResult:
        fp = Path(filepath)
        if not fp.exists():
            raise FileNotFoundError(f"{filepath} does not exist.")
        if fp.suffix.lower() not in (".md", ".markdown"):
            raise ValueError(f"{filepath} is not a markdown document.")
        return cls.inspect_text(fp.read_text(encoding="utf-8"))

    @classmethod
    def read_kwargs(cls, **kwargs: Any) -> Document:
        metadata = kwargs.pop("metadata", {})
        content = kwargs.pop("content", "")
        filepath = kwargs.pop("filepath", None)

        if not isinstance(metadata, Mapping):
            raise ValueError("metadata must be a mapping object")

        normalized_meta = _to_json_value(dict(metadata))
        normalized_meta.update({k: _to_json_value(v) for k, v in kwargs.items()})

        return cls(content=content, metadata=normalized_meta, filepath=filepath)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def write_text(self, *, emit_empty_frontmatter: bool = True) -> str:
        """
        Deterministic markdown serialization.

        Behavior:
        - Always emit YAML frontmatter with stable formatting
        """
        metadata = self.metadata or {}
        if not metadata and not emit_empty_frontmatter:
            return self.content or ""

        if (
            self.preserve_raw_frontmatter
            and self.raw_frontmatter is not None
            and metadata == (self.source_metadata or {})
        ):
            return f"---\n{self.raw_frontmatter}---\n\n{self.content}"

        try:
            serialized_metadata = _SERDE_MODULE.safe_dump(
                metadata,
                sort_keys=False,
                allow_unicode=True,
                default_flow_style=False,
            )
        except Exception as exc:  # noqa: BLE001
            raise IOError(f"Failed to serialize YAML: {exc}") from exc

        return f"---\n{serialized_metadata}---\n\n{self.content}"

    def write_file(
        self,
        filepath: str | Path | None = None,
        overwrite: bool = False,
        *,
        emit_empty_frontmatter: bool = True,
    ) -> Path:
        fp = Path(filepath) if filepath is not None else self.filepath

        if fp is None:
            raise ValueError("No output path specified.")

        if fp.exists() and not overwrite:
            raise FileExistsError(f"{fp} exists and overwrite not permitted.")

        serialized = self.write_text(emit_empty_frontmatter=emit_empty_frontmatter)

        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(serialized, encoding="utf-8")

        return fp

    def write(
        self,
        filepath: str | Path | None = None,
        overwrite: bool = False,
        *,
        emit_empty_frontmatter: bool = True,
    ) -> Path:
        return self.write_file(
            filepath=filepath,
            overwrite=overwrite,
            emit_empty_frontmatter=emit_empty_frontmatter,
        )

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def word_count(self) -> int:
        return len(re.findall(r"\b\w+\b", self.content))

    @property
    def words(self) -> int:
        # Deprecated alias; use `word_count`.
        return self.word_count

    def modified(self) -> int | None:
        if self.filepath and self.filepath.exists():
            return int(self.filepath.stat().st_mtime)
        return None

    def comments(self) -> list[str]:
        return re.findall(r"<!--(.*?)-->", self.content, re.DOTALL)

    def get(self, key: str, default: Any = None) -> Any:
        return (self.metadata or {}).get(key, default)

    def has_metadata(self, key: str) -> bool:
        return key in (self.metadata or {})
