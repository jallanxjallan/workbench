"""Load compiled regex pattern specs from Workbench runtime artifacts."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from workbench.config.roots import WORKBENCH_ROOT

_SUPPORTED_ENGINES = {"default", "pcre2"}
DEFAULT_COMPILED_REGEX_ROOT = WORKBENCH_ROOT / "_compiled" / "regex"
_regex_cache: dict[str, dict] = {}


class RegexRegistryError(RuntimeError):
    """Raised when a compiled regex spec cannot be loaded."""


@dataclass(frozen=True)
class RegexPattern:
    name: str
    pattern: str
    engine: str
    ignore_case: bool

    @property
    def pcre2(self) -> bool:
        return self.engine == "pcre2"


def load_regex(
    name: str,
    *,
    compiled_root: Path = DEFAULT_COMPILED_REGEX_ROOT,
) -> RegexPattern:
    pattern_name = str(name).strip()
    if not pattern_name:
        raise RegexRegistryError("regex name must be non-empty")

    root_path = Path(compiled_root).expanduser().resolve()
    cache_key = pattern_name
    if root_path != DEFAULT_COMPILED_REGEX_ROOT:
        cache_key = f"{root_path.as_posix()}::{pattern_name}"

    payload = _regex_cache.get(cache_key)
    if payload is None:
        path = root_path / f"{pattern_name}.json"
        if not path.is_file():
            raise RegexRegistryError(f"compiled regex not found: {path}")
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RegexRegistryError(f"invalid compiled regex JSON: {path}") from exc
        if not isinstance(loaded, dict):
            raise RegexRegistryError(f"compiled regex root must be a mapping: {path}")
        payload = loaded
        _regex_cache[cache_key] = payload

    loaded_name = payload.get("name")
    pattern = payload.get("pattern")
    engine = payload.get("engine")
    ignore_case = payload.get("ignore_case")

    if not isinstance(loaded_name, str) or not loaded_name.strip():
        raise RegexRegistryError(f"compiled regex missing 'name': {cache_key}")
    if loaded_name != pattern_name:
        raise RegexRegistryError(
            f"compiled regex name mismatch: expected {pattern_name}, found {loaded_name}"
        )
    if not isinstance(pattern, str) or not pattern:
        raise RegexRegistryError(f"compiled regex missing 'pattern': {cache_key}")
    if not isinstance(engine, str) or engine not in _SUPPORTED_ENGINES:
        raise RegexRegistryError(
            f"compiled regex has invalid 'engine' in {cache_key}: {engine}"
        )
    if not isinstance(ignore_case, bool):
        raise RegexRegistryError(f"compiled regex has invalid 'ignore_case': {cache_key}")

    return RegexPattern(
        name=loaded_name,
        pattern=pattern,
        engine=engine,
        ignore_case=ignore_case,
    )


__all__ = [
    "DEFAULT_COMPILED_REGEX_ROOT",
    "RegexPattern",
    "RegexRegistryError",
    "load_regex",
]
