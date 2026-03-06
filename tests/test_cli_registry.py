from workbench.cli.registry import REGISTRY, ROOT_COMMANDS


def test_create_project_command_points_to_create_project_module() -> None:
    entry = ROOT_COMMANDS["create-project"]
    assert entry.module == "workbench.cli.create_project"


def test_scan_sentinel_command_points_to_scan_sentinel_module() -> None:
    entry = ROOT_COMMANDS["scan-sentinel"]
    assert entry.module == "workbench.cli.scan_sentinel"


def test_stream_command_points_to_stream_module() -> None:
    entry = ROOT_COMMANDS["stream"]
    assert entry.module == "workbench.cli.stream"


def test_legacy_ingest_namespace_removed() -> None:
    assert "ingest" not in REGISTRY
