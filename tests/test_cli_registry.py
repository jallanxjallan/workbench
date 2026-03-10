from __future__ import annotations

import pytest

from workbench.cli import discover_commands
import workbench.cli.main as cli_main
import workbench.cli.write_new as write_new_module


def test_discovery_includes_expected_root_commands() -> None:
    commands = discover_commands()

    assert commands["write-new"] == "workbench.cli.write_new"
    assert commands["write-back"] == "workbench.cli.write_back"
    assert commands["write-stream"] == "workbench.cli.write_stream"
    assert commands["stream"] == "workbench.cli.stream"
    assert commands["generate-slugs"] == "workbench.cli.generate_slugs"
    assert commands["compile-registries"] == "workbench.cli.compile_registries"
    assert commands["compile-assets"] == "workbench.cli.compile_assets"
    assert commands["find-duplicates"] == "workbench.cli.find_duplicates"


def test_discovery_excludes_non_command_modules() -> None:
    commands = discover_commands()

    assert "main" not in commands
    assert "slug" not in commands


def test_legacy_commands_not_discovered() -> None:
    commands = discover_commands()

    assert "ingest" not in commands
    assert "create-project" not in commands
    assert "import-project" not in commands
    assert "generate-thumbs" not in commands
    assert "compile-patterns" not in commands


def test_hierarchical_dispatch_supports_write_new(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called: dict[str, list[str] | None] = {}

    def _fake_main(argv: list[str] | None = None) -> int:
        called["argv"] = argv
        return 0

    monkeypatch.setattr(write_new_module, "main", _fake_main)

    rc = cli_main.main(["write", "new", "--help"])

    assert rc == 0
    assert called["argv"] == ["--help"]


def test_help_subcommand_supports_hierarchical_command(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = cli_main.main(["help", "write", "new"])
    out = capsys.readouterr().out

    assert rc == 0
    assert "usage: write-new" in out
