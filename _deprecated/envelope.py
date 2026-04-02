from __future__ import annotations


def wrap_uploaded_record(
    *,
    entity_type: str,
    slug: str,
    payload: dict[str, object],
) -> dict[str, object]:
    return {
        "type": entity_type,
        "slug": slug,
        "payload": payload,
    }
