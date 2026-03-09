"""Legacy compatibility helpers for slug generation internals."""

from workbench.lib.identity import slug
from workbench.slug.writer import (
    find_vault_root,
    generate_slug_for_file,
    vault_namespace,
)

__all__ = [
    "find_vault_root",
    "generate_slug_for_file",
    "vault_namespace",
    "slug",
]
