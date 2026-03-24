# identity/mnemonic.py
from __future__ import annotations

import re


_MNEMONIC_RE = re.compile(r"^[a-z0-9]{1,5}$")


class IdentityError(ValueError):
    pass


def normalize_mnemonic(value: str) -> str:
    return str(value).strip().lower()


def validate_mnemonic(value: str) -> str:
    normalized = normalize_mnemonic(value)
    if not _MNEMONIC_RE.fullmatch(normalized):
        raise IdentityError(
            "Mnemonic must be 1-5 characters of lowercase letters and digits."
        )
    return normalized


def create_mnemonic(name: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "", str(name).strip().lower())
    if not normalized:
        raise IdentityError("Cannot derive mnemonic from empty name.")
    return validate_mnemonic(normalized[:5])