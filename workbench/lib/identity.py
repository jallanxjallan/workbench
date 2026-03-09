"""
Workbench identity utilities.

Provides deterministic short slugs derived from names.
Used by create-vault, generate-slug, and other identity consumers.
"""

from __future__ import annotations

import hashlib
import re

_CAMEL_TOKEN_RE = re.compile(r"[A-Z]+(?=[A-Z][a-z]|$)|[A-Z]?[a-z]+|[0-9]+")


def canonicalize(name: str) -> str:
    """
    Normalize a name for hashing.
    Removes punctuation and normalizes case.
    """
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def acronym(name: str) -> str:
    """
    Extract acronym from CamelCase words.

    Examples
    --------
    HHPLawFirm -> hlf
    OneManAirForce -> omaf
    """
    camel_tokens = _CAMEL_TOKEN_RE.findall(name)
    if camel_tokens:
        return "".join(token[0].lower() for token in camel_tokens if token)

    words = re.findall(r"[A-Za-z0-9]+", name)
    return "".join(w[0].lower() for w in words)


def short_hash(text: str, length: int = 3) -> str:
    """
    Deterministic short hash suffix.
    """
    h = hashlib.blake2s(text.encode(), digest_size=4).hexdigest()
    return h[:length]


def slug(name: str, hash_len: int = 3) -> str:
    """
    Generate deterministic slug.

    Format:
        <acronym>-<hash>

    Example
        HHPLawFirm -> hlf-7c2
    """
    base = acronym(name)
    canon = canonicalize(name)
    suffix = short_hash(canon, hash_len)
    return f"{base}-{suffix}"
