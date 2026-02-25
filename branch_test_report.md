# Branch Test Report

## Context

- Branch: `refactor/strip-cli-flags`
- Commit: `aaf0a0b`
- Run time (UTC): `2026-02-25 00:34:45 UTC`

## Command Executed

```bash
pytest -vv
```

## Environment

- Platform: `linux`
- Python: `3.13.12`
- pytest: `9.0.2`
- Plugins: `anyio-4.10.0`, `typeguard-4.4.4`
- Root dir: `/home/jeremy/Workbench`
- Config: `pyproject.toml`

## Summary

- Collected: `33`
- Passed: `33`
- Failed: `0`
- Skipped: `0`
- Errors: `0`
- Duration: `0.16s`

## Detailed Results

1. `tests/test_converter_primitives.py::test_markdown_to_record_primitive_matches_batch_converter` — PASSED
2. `tests/test_converter_primitives.py::test_record_to_markdown_primitive_single_record` — PASSED
3. `tests/test_converter_primitives.py::test_markdown_to_record_stream_entrypoint_is_functional` — PASSED
4. `tests/test_converter_primitives.py::test_record_to_markdown_requires_string_content` — PASSED
5. `tests/test_converter_primitives.py::test_markdown_to_record_rejects_multi_document_markdown` — PASSED
6. `tests/test_emit_adapter_guardrails.py::test_assemble_adapter_uses_record_to_markdown_for_single_record` — PASSED
7. `tests/test_emit_adapter_guardrails.py::test_export_adapter_uses_record_to_markdown_for_single_record` — PASSED
8. `tests/test_emit_adapter_guardrails.py::test_assemble_and_export_ndjson_adapters_match_output_for_single_record` — PASSED
9. `tests/test_emit_adapter_guardrails.py::test_assemble_and_export_ndjson_adapters_reject_multi_record_input` — PASSED
10. `tests/test_emit_adapter_guardrails.py::test_assemble_and_export_ndjson_adapters_match_error_behavior` — PASSED
11. `tests/test_framing_batch.py::test_single_record_round_trip` — PASSED
12. `tests/test_framing_batch.py::test_empty_input_parses_to_empty_list` — PASSED
13. `tests/test_framing_batch.py::test_multi_document_input_is_rejected` — PASSED
14. `tests/test_framing_batch.py::test_invalid_yaml_failure_still_surfaces` — PASSED
15. `tests/test_framing_batch.py::test_emit_markdown_batch_rejects_more_than_one_document` — PASSED
16. `tests/test_framing_batch.py::test_invalid_json_failure` — PASSED
17. `tests/test_framing_batch.py::test_deterministic_output_check` — PASSED
18. `tests/test_framing_batch.py::test_ndjson_multi_record_conversion_still_works` — PASSED
19. `tests/test_framing_batch.py::test_markdown_to_ndjson_and_back_single_document` — PASSED
20. `tests/test_framing_batch.py::test_ndjson_to_markdown_rejects_multiple_records` — PASSED
21. `tests/test_framing_batch.py::test_no_legacy_split_markdown_batch_symbol` — PASSED
22. `tests/test_frontmatter_normalization.py::test_select_records_frontmatter_normalization_matches_lib_helper` — PASSED
23. `tests/test_frontmatter_normalization.py::test_to_json_value_normalizes_nested_values` — PASSED
24. `tests/test_interop.py::test_single_document_round_trip` — PASSED
25. `tests/test_interop.py::test_multiple_documents_round_trip` — PASSED
26. `tests/test_interop.py::test_invalid_ndjson_raises_stream_error` — PASSED
27. `tests/test_interop.py::test_schema_violation_raises_stream_error` — PASSED
28. `tests/test_slug.py::test_is_valid_batch_slug` — PASSED
29. `tests/test_write_commands.py::test_writenew_creates_file` — PASSED
30. `tests/test_write_commands.py::test_writenew_rejects_multi_document_markdown` — PASSED
31. `tests/test_write_commands.py::test_writeback_overwrites_existing` — PASSED
32. `tests/test_write_commands.py::test_writestream_passthrough` — PASSED
33. `tests/test_write_commands.py::test_writestream_rejects_multi_document_markdown` — PASSED
