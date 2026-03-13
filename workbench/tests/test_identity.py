from __future__ import annotations

from workbench.slug.identity import slug


def test_examples() -> None:
    assert slug("HHPLawFirm").startswith("hlf-")
    assert slug("OneManAirForce").startswith("omaf-")
    assert slug("HarvardLawFirm").startswith("hlf-")
