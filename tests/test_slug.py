from __future__ import annotations

from workbench.lib.slug import is_valid_batch_slug


def test_is_valid_batch_slug() -> None:
    assert is_valid_batch_slug("alpha")
    assert is_valid_batch_slug("alpha-1")
    assert is_valid_batch_slug("omaf.chapter-3")
    assert is_valid_batch_slug("2026.02.26-120001")

    assert not is_valid_batch_slug("")
    assert not is_valid_batch_slug("   ")
