from __future__ import annotations

from workbench.lib.slug import is_valid_batch_slug


def test_is_valid_batch_slug() -> None:
    assert is_valid_batch_slug("alpha")
    assert is_valid_batch_slug("alpha-1")
    assert is_valid_batch_slug("a1-b2-c3")

    assert not is_valid_batch_slug("")
    assert not is_valid_batch_slug(" alpha")
    assert not is_valid_batch_slug("alpha ")
    assert not is_valid_batch_slug("Alpha")
    assert not is_valid_batch_slug("alpha_beta")
    assert not is_valid_batch_slug("alpha--beta")
