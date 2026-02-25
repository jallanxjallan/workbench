from __future__ import annotations

from workbench.ingest._select_records import _BATCH_SENTINEL_LINE_RE, _extract_frontmatter
from workbench.lib.frontmatter import parse_frontmatter, to_json_value


def test_select_records_frontmatter_normalization_matches_lib_helper() -> None:
    text = (
        "--- ASC BATCH: alpha-1 ---\n"
        "---\n"
        "title: Example\n"
        "created: 2024-01-02\n"
        "tags:\n"
        "  - one\n"
        "  - two\n"
        "nested:\n"
        "  enabled: true\n"
        "---\n"
        "\n"
        "Body\n"
    )
    parsed = parse_frontmatter(text, sentinel_pattern=_BATCH_SENTINEL_LINE_RE)
    assert parsed.data is not None
    assert _extract_frontmatter(text) == parsed.data


def test_to_json_value_normalizes_nested_values() -> None:
    value = {"a": 1, 2: ("x", {"y": object()})}
    normalized = to_json_value(value)
    assert normalized["a"] == 1
    assert normalized["2"][0] == "x"
    assert isinstance(normalized["2"][1]["y"], str)
