"""Legacy compatibility helpers for slug generation internals."""

from workbench.lib.identity import slug
from workbench.slug.generator import (
    find_vault_root,
    generate_slug_for_file,
    load_vault_mnemonic,
)

__all__ = [
    "find_vault_root",
    "generate_slug_for_file",
    "load_vault_mnemonic",
    "slug",
]
