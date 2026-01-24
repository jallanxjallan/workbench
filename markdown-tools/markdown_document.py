from typing import Optional, Union, Any, Dict
from pathlib import Path
import attr
from attr import define, field
from attrs.converters import optional
import frontmatter
import re
from datetime import datetime
from utility import to_title


@define()
class Document:
    """
    Wrapper for Markdown + frontmatter files.
    Handles loading, serialization, and introspection of document content and metadata.
    """
    content: Optional[str] = field(
        default=None,
        converter=optional(lambda x: '\n\n'.join(x) if isinstance(x, list) else str(x))
    )
    metadata: Optional[Dict[str, Any]] = field(
        factory=dict,
        converter=optional(lambda x: frontmatter.loads(x).to_dict() if isinstance(x, str) else x)
    )
    filepath: Optional[Path] = field(default=None, converter=optional(Path))

    

    def __str__(self) -> str:
        return self.content or ""

    def __getattr__(self, attr: str) -> Any:
        """
        Allow direct access to metadata keys as attributes (if present).
        """
        return self.metadata.get(attr, None)

    def asdict(self, *atts: str) -> dict:
        """
        Export to dictionary. Optionally filter to specific attributes.
        """
        all_data = attr.asdict(self)
        return {k: v for k, v in all_data.items() if not atts or k in atts}

    @classmethod
    def read_text(cls, text: str) -> "Document":
        """
        Load from raw markdown text (with frontmatter).
        """
        try:
            post = frontmatter.loads(text)
            return cls(content=post.content, metadata=post.metadata)
        except Exception as e:
            raise ValueError(f"Failed to parse markdown: {e}")

    @classmethod
    def read_file(cls, filepath: Union[str, Path]) -> "Document":
        fp = Path(filepath)
        if not fp.exists():
            raise FileNotFoundError(f"{filepath} does not exist.")
        if fp.suffix.lower() not in ('.md', '.markdown'):
            raise ValueError(f"{filepath} is not a markdown document.")
        try:
            post = frontmatter.load(fp)
            return cls(content=post.content, metadata=post.metadata, filepath=fp)
        except Exception as e:
            raise ValueError(f"Failed to load file: {e}")

    @classmethod
    def read_kwargs(cls, **kwargs) -> "Document":
        """
        Construct a document from raw keyword arguments.
        `content`, `metadata`, and `filepath` are special; others go into metadata.
        """
        metadata = kwargs.pop('metadata', {})
        content = kwargs.pop('content', None)
        filepath = kwargs.pop('filepath', None)
        metadata.update({k: str(v) for k, v in kwargs.items()})
        return cls(content=content, metadata=metadata, filepath=filepath)

    def write_file(self, filepath: Optional[Union[str, Path]] = None, overwrite: bool = False) -> Path:
        fp = Path(filepath or self.filepath)
        if not fp:
            raise ValueError("No output path specified.")
        if fp.exists() and not overwrite:
            raise FileExistsError(f"{fp} exists and overwrite not permitted.")
        meta = self.metadata or {
            'name': title_case(fp.stem),
            'status': 'new'
        }
        try:
            post = frontmatter.Post(self.content, **meta)
            frontmatter.dump(post, fp)
            return fp
        except Exception as e:
            raise IOError(f"Failed to write file: {e}")

    def write_text(self) -> str:
        """
        Return markdown+metadata block as a string.
        """
        try:
            post = frontmatter.Post(self.content, **(self.metadata or {}))
            return frontmatter.dumps(post)
        except Exception as e:
            raise IOError(f"Failed to write text: {e}")

    def words(self) -> int:
        return len(re.findall(r'\b\w+\b', self.content or ""))

    def modified(self) -> Optional[int]:
        return int(self.filepath.stat().st_mtime) if self.filepath and self.filepath.exists() else None

    def comments(self) -> list:
        return re.findall(r'<!--(.*?)-->', self.content or "", re.DOTALL)

    def get(self, key: str, default: Any = None) -> Any:
        return self.metadata.get(key, default)

    def has_metadata(self, key: str) -> bool:
        return key in self.metadata
