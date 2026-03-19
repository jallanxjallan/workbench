"""Pure batch tag manifest parsing and validation."""

from __future__ import annotations

from dataclasses import dataclass
import importlib


_YAML_MODULE = importlib.import_module("yaml".upper().lower())


class BatchManifestError(RuntimeError):
    """Raised when a batch tag annotation is invalid."""


@dataclass(frozen=True)
class BatchTagManifest:
    batch: str
    order: tuple[str, ...]
    description: str | None = None

    @property
    def tag_name(self) -> str:
        return f"batch/{self.batch}"


def parse_batch_tag_annotation(annotation: str, *, requested_batch_id: str) -> BatchTagManifest:
    batch_id = str(requested_batch_id).strip()
    if not batch_id:
        raise BatchManifestError("batch id is required")

    raw = str(annotation).strip()
    if raw == "":
        raise BatchManifestError("tag annotation unreadable")

    try:
        payload = _YAML_MODULE.safe_load(raw)
    except Exception as exc:  # noqa: BLE001
        raise BatchManifestError(f"invalid batch tag annotation: {exc}") from exc

    if not isinstance(payload, dict):
        raise BatchManifestError("batch tag annotation must be a mapping")

    raw_batch = payload.get("batch")
    if not isinstance(raw_batch, str) or not raw_batch.strip():
        raise BatchManifestError("batch tag missing required field: batch")
    batch = raw_batch.strip()
    if batch != batch_id:
        raise BatchManifestError(f"batch tag mismatch: expected {batch_id}, found {batch}")

    raw_description = payload.get("description")
    if raw_description is None:
        description = None
    elif not isinstance(raw_description, str) or not raw_description.strip():
        raise BatchManifestError("description must be a non-empty string when present")
    else:
        description = raw_description.strip()

    raw_order = payload.get("order")
    if not isinstance(raw_order, list) or not raw_order:
        raise BatchManifestError("batch tag missing required field: order")

    order: list[str] = []
    seen: set[str] = set()
    for item in raw_order:
        if not isinstance(item, str) or not item.strip():
            raise BatchManifestError("batch tag order entries must be non-empty strings")
        slug = item.strip()
        if slug in seen:
            raise BatchManifestError(f"duplicate batch slug: {slug}")
        seen.add(slug)
        order.append(slug)

    return BatchTagManifest(
        batch=batch,
        order=tuple(order),
        description=description,
    )
