# identity/suffix.py
from __future__ import annotations

import secrets
import string


DEFAULT_SUFFIX_LENGTH = 8
_SUFFIX_ALPHABET = string.ascii_lowercase


class IdentityError(ValueError):
    pass


def generate_slug_suffix(length: int = DEFAULT_SUFFIX_LENGTH) -> str:
    if length <= 0:
        raise IdentityError("Suffix length must be positive.")
    return "".join(secrets.choice(_SUFFIX_ALPHABET) for _ in range(length))


def validate_slug_suffix(value: str, length: int = DEFAULT_SUFFIX_LENGTH) -> str:
    normalized = str(value).strip()
    if len(normalized) != length:
        raise IdentityError(f"Suffix must be exactly {length} characters.")
    if any(char not in _SUFFIX_ALPHABET for char in normalized):
        raise IdentityError("Suffix must contain lowercase letters only.")
    return normalized