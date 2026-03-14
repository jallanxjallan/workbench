from __future__ import annotations

import pytest

from workbench.interop.identity import create_mnemonic, normalize_semantic_base


def test_examples() -> None:
    assert normalize_semantic_base("HHPLawFirm.md") == "hhplawfirm"
    assert normalize_semantic_base("One Man Air Force") == "one-man-air-force"
    assert normalize_semantic_base("HarvardLawFirm") == "harvardlawfirm"


def test_create_mnemonic_compacts_and_caps_length() -> None:
    assert create_mnemonic("Batavia Triptych") == "batav"
    assert create_mnemonic("One Man Air Force") == "onema"
    assert create_mnemonic("omaf") == "omaf"


def test_create_mnemonic_rejects_empty_result() -> None:
    with pytest.raises(ValueError, match="Unable to derive mnemonic"):
        create_mnemonic("!!!")
