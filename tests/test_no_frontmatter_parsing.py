from __future__ import annotations

import pathlib


ROOT = pathlib.Path("workbench")
DOCUMENT_MODULE = ROOT / "interop" / "document.py"
CREATE_VAULT_MODULE = ROOT / "cli" / "create_vault.py"


def test_no_legacy_frontmatter_module() -> None:
    assert not (ROOT / "lib" / "frontmatter.py").exists()


def test_no_internal_frontmatter_parsing_outside_document() -> None:
    forbidden = [
        "workbench.frontmatter",
        "parse_frontmatter(",
        "yaml.",
        "safe_load",
        "safe_dump",
    ]
    for path in ROOT.rglob("*.py"):
        if path in {DOCUMENT_MODULE, CREATE_VAULT_MODULE}:
            continue

        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{token} found in {path}"
