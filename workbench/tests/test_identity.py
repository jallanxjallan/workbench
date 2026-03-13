from __future__ import annotations

from workbench.interop.identity import normalize_semantic_base


def test_examples() -> None:
    assert normalize_semantic_base("HHPLawFirm.md") == "hhplawfirm"
    assert normalize_semantic_base("One Man Air Force") == "one-man-air-force"
    assert normalize_semantic_base("HarvardLawFirm") == "harvardlawfirm"
