from workbench.cli.registry import REGISTRY, ROOT_COMMANDS


def test_scan_sentinel_command_points_to_scan_sentinel_module() -> None:
    entry = ROOT_COMMANDS["scan-sentinel"]
    assert entry.module == "workbench.cli.scan_sentinel"


def test_stream_command_points_to_stream_module() -> None:
    entry = ROOT_COMMANDS["stream"]
    assert entry.module == "workbench.cli.stream"


def test_generate_slugs_command_points_to_generate_slugs_module() -> None:
    entry = ROOT_COMMANDS["generate-slugs"]
    assert entry.module == "workbench.cli.generate_slugs"


def test_generate_thumbs_command_points_to_generate_thumbs_module() -> None:
    entry = ROOT_COMMANDS["generate-thumbs"]
    assert entry.module == "workbench.cli.generate_thumbs"


def test_compile_registries_command_points_to_compile_registries_module() -> None:
    entry = ROOT_COMMANDS["compile-registries"]
    assert entry.module == "workbench.cli.compile_registries"


def test_compile_assets_command_points_to_compile_assets_module() -> None:
    entry = ROOT_COMMANDS["compile-assets"]
    assert entry.module == "workbench.cli.compile_assets"


def test_find_duplicates_command_points_to_find_duplicates_module() -> None:
    entry = ROOT_COMMANDS["find-duplicates"]
    assert entry.module == "workbench.cli.find_duplicates"


def test_legacy_ingest_namespace_removed() -> None:
    assert "ingest" not in REGISTRY


def test_legacy_slug_namespace_removed() -> None:
    assert "slug" not in REGISTRY


def test_create_project_command_removed() -> None:
    assert "create-project" not in ROOT_COMMANDS


def test_import_project_command_removed() -> None:
    assert "import-project" not in ROOT_COMMANDS
